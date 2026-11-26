"""Empirical day-replay trade model for multi-market, multi-account simulations.

Instead of drawing trades i.i.d., every simulated day replays one *historical* day: all
trades that the validated strategies took on that day, in every market. Each account slot
trades its own subset of markets, but all slots on a path see the same historical day, so
the cross-market and cross-account correlations are the real ones. Days are drawn with a
stationary block bootstrap (mean block length 20 days) so volatility clustering — the thing
that actually kills trailing-drawdown accounts — is preserved.

Costs are folded into R (r_net = r_gross − cost / stop$), so `cost_per_contract` is 0.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..instruments import get_instrument


@dataclass
class MarketTradeLog:
    """Trades of one market on a common day calendar (day = index into the calendar)."""
    market: str
    trades: pd.DataFrame   # columns: day, entry_min, r_gross, mae_r, mfe_r, risk_pts

    def with_costs(self) -> pd.DataFrame:
        ins = get_instrument(self.market)
        t = self.trades.copy()
        t["stop_dollars"] = t["risk_pts"] * ins.point_value
        t["r_net"] = t["r_gross"] - ins.cost_rt() / t["stop_dollars"]
        t["mae_r"] = t["mae_r"] + ins.cost_rt() / t["stop_dollars"]
        return t


class SlotDayModel:
    def __init__(self, logs: dict[str, MarketTradeLog], n_days: int, slot_markets: list[list[str]], n_paths: int,
                 block: int = 20, kmax: int = 8, name: str = "empirical_days", seed: int = 0):
        self.name, self.n_paths, self.block, self.n_days = name, n_paths, block, n_days
        self.slot_markets = slot_markets
        self.S = len(slot_markets)
        self.cost_per_contract = 0.0
        prepared = {m: lg.with_costs() for m, lg in logs.items()}
        self.T, self.C = [], []
        for mk in slot_markets:
            t = pd.concat([prepared[m] for m in mk if m in prepared], ignore_index=True).sort_values(["day", "entry_min"])
            T = np.zeros((n_days, kmax, 4))
            T[:, :, 3] = 1.0
            C = np.zeros(n_days, dtype=int)
            for d, g in t.groupby("day"):
                g = g.head(kmax)
                k = len(g)
                T[int(d), :k] = g[["r_net", "mae_r", "mfe_r", "stop_dollars"]].to_numpy()
                C[int(d)] = k
            self.T.append(T)
            self.C.append(C)
        self.trades_per_day = float(np.mean([c.mean() for c in self.C]))
        self.max_trades_per_day = kmax
        self._rng = np.random.default_rng(seed)
        self._day = self._rng.integers(0, n_days, n_paths)
        self._k = 0

    def _advance(self):
        jump = self._rng.random(self.n_paths) < 1.0 / self.block
        self._day = np.where(jump, self._rng.integers(0, self.n_days, self.n_paths), (self._day + 1) % self.n_days)

    def n_trades(self, rng, n):
        assert n == self.S * self.n_paths, "SlotDayModel is laid out slot-major: n = slots * paths"
        self._advance()
        self._k = 0
        return np.concatenate([C[self._day] for C in self.C])

    def sample(self, rng, n):
        k = self._k
        self._k += 1
        rows = np.concatenate([T[self._day, k] for T in self.T])
        r, mae, mfe, stop = rows[:, 0], rows[:, 1], rows[:, 2], rows[:, 3]
        return r, np.maximum(mae, 0.0), np.maximum(mfe, 0.0), np.maximum(stop, 1e-6)

    def summary(self) -> dict:
        allr = np.concatenate([T[:, :, 0][np.arange(T.shape[1])[None, :] < C[:, None]] for T, C in zip(self.T, self.C)])
        return {"name": self.name, "slots": self.slot_markets, "trades_per_day": self.trades_per_day,
                "expected_net_r": float(allr.mean()) if len(allr) else 0.0, "n_trades": int(len(allr)),
                "win_rate": float((allr > 0).mean()) if len(allr) else 0.0, "block": self.block}


def slot_assignment(markets: list[str], n_slots: int, mode: str = "all") -> list[list[str]]:
    """How the validated markets are spread over account slots.

    all            every account trades every market (maximum edge per account, accounts highly correlated)
    leave_one_out  account k trades all markets except market k (keeps most of the edge, partial decorrelation)
    pairs          one equity index + one commodity per account (strong decorrelation, thin edge per account)"""
    markets = sorted(markets)
    if mode == "all" or len(markets) == 1:
        return [list(markets) for _ in range(n_slots)]
    if mode == "leave_one_out":
        if n_slots == 1:
            return [list(markets)]
        return [[m for j, m in enumerate(markets) if j != (k % len(markets))] for k in range(n_slots)]
    eq = [m for m in markets if m in ("MES", "MNQ", "ES", "NQ")]
    other = [m for m in markets if m not in eq]
    pairs = [[e, o] for e in eq for o in other] or [[m] for m in markets]
    return [pairs[i % len(pairs)] for i in range(n_slots)]
