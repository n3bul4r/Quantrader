"""S1 — Noise-Area Intraday Momentum (core strategy).

Futures adaptation of Zarattini, Aziz & Barbon (2024), "Beat the Market: An Effective
Intraday Momentum Strategy for S&P500 ETF (SPY)", itself grounded in the market
intraday-momentum literature (Gao, Han, Li & Zhou, JFE 2018; Baltussen, Da, Lammers &
Martens, JFE 2021 — 60+ futures, mechanism: short-gamma hedging flows).

Rules (all times ET, RTH only, 1-minute bars):
    O_t          RTH open (09:30), C_{t-1} prior RTH close
    sigma_{t,m}  mean_{i=1..14} |Close_{t-i,m} / O_{t-i} - 1|     (noise width at minute m)
    U_{t,m}      max(O_t, C_{t-1}) * (1 + k * sigma_{t,m})
    L_{t,m}      min(O_t, C_{t-1}) * (1 - k * sigma_{t,m})
    Decision times: every 30 min from 10:00 to 15:30 (m = 30, 60, ..., 360)
    Long  if Close_m > U_m ; Short if Close_m < L_m   (flip allowed, max N entries/day)
    Stop  long: max(U_m, VWAP_m), ratcheted, re-evaluated at each decision time;
          short: min(L_m, VWAP_m). Initial stop floored at >= f * sigma * O_t from entry.
    Exit  stop, or market-on-close at 15:59 bar close. Never holds overnight.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .base import FeatureCache, OpenPosition, Strategy, Trade


@dataclass
class NoiseAreaMomentum(Strategy):
    band_mult: float = 1.0
    first_decision: int = 30       # 10:00
    decision_every: int = 30
    last_entry: int = 360          # 15:30
    exit_min: int = 389            # 15:59 bar close ~ 16:00
    min_stop_sigma: float = 0.5    # initial stop floor, in units of sigma * open
    max_entries: int = 3
    allow_flip: bool = True
    name: str = "S1_noise_momentum"

    def generate(self, fc: FeatureCache) -> list[Trade]:
        p = fc.panel
        upper, lower, sig = fc.bands
        if self.band_mult != 1.0:
            o, pc = p.day_open[:, None], p.prev_close[:, None]
            upper = np.maximum(o, pc) * (1 + self.band_mult * sig)
            lower = np.minimum(o, pc) * (1 - self.band_mult * sig)
        vwap, _ = fc.vwap
        trades: list[Trade] = []
        decisions = set(range(self.first_decision, self.last_entry + 1, self.decision_every))
        for t in range(p.n_days):
            if np.isnan(sig[t]).any():
                continue
            date = p.dates[t]
            O, H, L_, C = p.open[t], p.high[t], p.low[t], p.close[t]
            U, Lo, V = upper[t], lower[t], vwap[t]
            pos: OpenPosition | None = None
            entries = 0
            for i in range(p.close.shape[1]):
                if pos is not None and i > pos.entry_min:
                    pos.update_excursions(H[i], L_[i])
                    fill = pos.stop_fill(O[i], H[i], L_[i])
                    if fill is not None:
                        trades.append(pos.close(self.name, date, i, fill, "stop"))
                        pos = None
                    elif i >= self.exit_min:
                        trades.append(pos.close(self.name, date, i, C[i], "time"))
                        pos = None
                        break
                if i in decisions:
                    if pos is not None:  # re-evaluate trailing stop at decision times
                        trail = max(U[i], V[i]) if pos.side > 0 else min(Lo[i], V[i])
                        if pos.side * (C[i] - trail) < 0:
                            # closed back through the trailing level -> exit at market
                            trades.append(pos.close(self.name, date, i, C[i], "trail"))
                            pos = None
                        elif pos.side > 0:
                            pos.stop = max(pos.stop, trail)
                        else:
                            pos.stop = min(pos.stop, trail)
                    if entries >= self.max_entries:
                        continue
                    want = 1 if C[i] > U[i] else (-1 if C[i] < Lo[i] else 0)
                    if want == 0 or (pos is not None and pos.side == want):
                        continue
                    if pos is not None:
                        if not self.allow_flip:
                            continue
                        trades.append(pos.close(self.name, date, i, C[i], "reverse"))
                        pos = None
                    floor = self.min_stop_sigma * sig[t, i] * O[0]
                    if want > 0:
                        stop = min(max(U[i], V[i]), C[i] - floor)
                    else:
                        stop = max(min(Lo[i], V[i]), C[i] + floor)
                    pos = OpenPosition(want, i, C[i], stop, stop,
                                       meta={"sigma": float(sig[t, i]), "decision_min": i})
                    entries += 1
            if pos is not None:  # safety: flatten at last bar
                trades.append(pos.close(self.name, date, len(C) - 1, C[-1], "eod"))
        return trades
