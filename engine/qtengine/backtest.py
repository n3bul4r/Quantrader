"""Backtest runner: strategies -> trades (points) -> sized $ P&L with all-in costs."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from .features import DayPanel, build_panel
from .instruments import Instrument, get_instrument
from .metrics import daily_stats, trade_stats
from .strategies.base import FeatureCache, Strategy, Trade


@dataclass
class Sizing:
    """mode='contracts': fixed contracts per trade.
    mode='risk': contracts = floor(risk_dollars / (stop_pts * point_value)), one contract
    allowed if a single contract risks <= round_up_tolerance * risk_dollars, else skip."""
    mode: str = "contracts"
    contracts: int = 1
    risk_dollars: float = 200.0
    max_contracts: int = 50
    round_up_tolerance: float = 1.25

    def size(self, risk_pts: float, ins: Instrument) -> int:
        if self.mode == "contracts":
            return self.contracts
        per = risk_pts * ins.point_value
        if per <= 0:
            return 0
        n = math.floor(self.risk_dollars / per)
        if n == 0 and per <= self.round_up_tolerance * self.risk_dollars:
            n = 1
        return min(n, self.max_contracts)


@dataclass
class BacktestResult:
    symbol: str
    trades: pd.DataFrame
    daily: pd.Series
    summary: dict
    params: dict = field(default_factory=dict)

    @property
    def equity(self) -> pd.Series:
        return self.daily.cumsum()

    def to_dict(self) -> dict:
        t = self.trades.copy()
        for c in ("date",):
            if c in t:
                t[c] = t[c].astype(str)
        return {
            "symbol": self.symbol,
            "summary": _clean(self.summary),
            "params": self.params,
            "equity": [{"date": str(d.date()), "pnl": float(v), "equity": float(e)}
                       for d, v, e in zip(self.daily.index, self.daily.values, self.equity.values)],
            "trades": _clean(t.to_dict(orient="records")),
        }


def _clean(obj):
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return None if not math.isfinite(f) else f
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return obj


def trades_frame(trades: list[Trade], ins: Instrument, sizing: Sizing, cost_rt: float | None = None) -> pd.DataFrame:
    cost = ins.cost_rt() if cost_rt is None else cost_rt
    rows = []
    for tr in sorted(trades, key=lambda x: (x.date, x.entry_min)):
        n = sizing.size(tr.risk_pts, ins)
        if n <= 0:
            continue
        gross = tr.pnl_pts * ins.point_value * n
        c = cost * n
        risk_d = tr.risk_pts * ins.point_value * n
        rows.append({
            "date": tr.date, "strategy": tr.strategy, "side": tr.side,
            "entry_min": tr.entry_min, "exit_min": tr.exit_min,
            "entry_time": _hhmm(tr.entry_min), "exit_time": _hhmm(tr.exit_min),
            "entry": tr.entry, "exit": tr.exit, "stop": tr.stop_init, "risk_pts": tr.risk_pts,
            "contracts": n, "pnl_pts": tr.pnl_pts, "gross": gross, "cost": c, "pnl": gross - c,
            "risk_dollars": risk_d, "r_gross": tr.r_gross, "r_net": (gross - c) / risk_d if risk_d else 0.0,
            "mae_r": tr.mae_pts / tr.risk_pts if tr.risk_pts else 0.0,
            "mfe_r": tr.mfe_pts / tr.risk_pts if tr.risk_pts else 0.0,
            "exit_reason": tr.exit_reason, **{f"m_{k}": v for k, v in tr.meta.items()},
        })
    return pd.DataFrame(rows)


def _hhmm(minute: int) -> str:
    h, m = divmod(9 * 60 + 30 + int(minute) + 1, 60)  # bar close time
    return f"{h:02d}:{m:02d}"


def run_backtest(
    data: pd.DataFrame | DayPanel,
    strategies: list[Strategy],
    symbol: str = "MES",
    sizing: Sizing | None = None,
    cost_rt: float | None = None,
) -> BacktestResult:
    panel = data if isinstance(data, DayPanel) else build_panel(data)
    ins = get_instrument(symbol)
    sizing = sizing or Sizing()
    fc = FeatureCache(panel)
    trades: list[Trade] = []
    for s in strategies:
        trades.extend(s.generate(fc))
    tf = trades_frame(trades, ins, sizing, cost_rt)
    idx = pd.DatetimeIndex(panel.dates)
    daily = pd.Series(0.0, index=idx)
    if len(tf):
        daily = daily.add(tf.groupby("date")["pnl"].sum(), fill_value=0.0)
    # drop warm-up days before any strategy could trade (noise lookback)
    first_valid = 15
    daily = daily.iloc[first_valid:]
    summary = {
        "trades": trade_stats(tf["pnl"].to_numpy(), tf["r_net"].to_numpy()) if len(tf) else {"n": 0},
        "daily": daily_stats(daily),
        "cost_per_contract_rt": ins.cost_rt() if cost_rt is None else cost_rt,
        "by_strategy": {k: trade_stats(g["pnl"].to_numpy(), g["r_net"].to_numpy()) for k, g in tf.groupby("strategy")} if len(tf) else {},
    }
    params = {s.name: s.params() for s in strategies}
    params["sizing"] = asdict(sizing)
    return BacktestResult(symbol, tf, daily, summary, params)
