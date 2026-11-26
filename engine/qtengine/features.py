"""Minute-aligned day panel + intraday features used by the strategies.

All features at (day t, minute m) use only information available at the close of
minute m of day t (no look-ahead). Rolling statistics over past days use days < t.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import RTH_MINUTES, minutes_from_open, sessions


@dataclass
class DayPanel:
    dates: list[pd.Timestamp]
    open: np.ndarray    # [D, 390]
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray

    @property
    def n_days(self) -> int:
        return len(self.dates)

    @property
    def day_open(self) -> np.ndarray:
        return self.open[:, 0]

    @property
    def day_close(self) -> np.ndarray:
        return self.close[:, -1]

    @property
    def prev_close(self) -> np.ndarray:
        pc = np.empty(self.n_days)
        pc[0] = self.open[0, 0]
        pc[1:] = self.close[:-1, -1]
        return pc


def build_panel(df: pd.DataFrame, min_bars: int = 380) -> DayPanel:
    """Align each full RTH session onto a 390-minute grid (forward-filling gaps)."""
    dates, arrs = [], {k: [] for k in ("open", "high", "low", "close", "volume")}
    for day, g in sessions(df, min_bars=min_bars):
        mins = minutes_from_open(g.index)
        grid = pd.DataFrame(index=np.arange(RTH_MINUTES))
        gg = g.copy()
        gg.index = mins
        gg = gg[~gg.index.duplicated()].reindex(grid.index)
        gg["close"] = gg["close"].ffill().bfill()
        for c in ("open", "high", "low"):
            gg[c] = gg[c].fillna(gg["close"])
        gg["volume"] = gg["volume"].fillna(0.0)
        dates.append(day)
        for k in arrs:
            arrs[k].append(gg[k].to_numpy(dtype=float))
    if not dates:
        raise ValueError("No complete RTH sessions found")
    return DayPanel(dates, *(np.vstack(arrs[k]) for k in ("open", "high", "low", "close", "volume")))


def session_vwap(p: DayPanel) -> tuple[np.ndarray, np.ndarray]:
    """Cumulative session VWAP and volume-weighted std of typical price around it."""
    tp = (p.high + p.low + p.close) / 3.0
    v = np.maximum(p.volume, 1e-9)
    cv = np.cumsum(v, axis=1)
    vwap = np.cumsum(tp * v, axis=1) / cv
    var = np.cumsum(v * tp ** 2, axis=1) / cv - vwap ** 2
    return vwap, np.sqrt(np.maximum(var, 0.0))


def noise_sigma(p: DayPanel, lookback: int = 14) -> np.ndarray:
    """sigma[t, m] = mean over the previous ``lookback`` days of |close[m]/open - 1|.

    This is the 'noise area' width from Zarattini, Aziz & Barbon (2024). Rows with
    insufficient history are NaN.
    """
    move = np.abs(p.close / p.day_open[:, None] - 1.0)
    sig = np.full_like(move, np.nan)
    csum = np.cumsum(np.vstack([np.zeros((1, move.shape[1])), move]), axis=0)
    for t in range(lookback, p.n_days):
        sig[t] = (csum[t] - csum[t - lookback]) / lookback
    return sig


def noise_bands(p: DayPanel, lookback: int = 14, mult: float = 1.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Upper/lower noise-area boundaries, gap-adjusted with the prior RTH close."""
    sig = noise_sigma(p, lookback)
    o, pc = p.day_open[:, None], p.prev_close[:, None]
    upper = np.maximum(o, pc) * (1 + mult * sig)
    lower = np.minimum(o, pc) * (1 - mult * sig)
    return upper, lower, sig


def daily_realized_vol(p: DayPanel, lookback: int = 14) -> np.ndarray:
    """Rolling std of close-to-close RTH log returns over the previous ``lookback`` days
    (value at t uses days t-lookback..t-1)."""
    r = np.diff(np.log(p.day_close), prepend=np.log(p.day_open[0]))
    out = np.full(p.n_days, np.nan)
    for t in range(lookback + 1, p.n_days):
        out[t] = r[t - lookback:t].std(ddof=1)
    return out


def vol_regime(p: DayPanel, fast: int = 14, slow: int = 60) -> np.ndarray:
    """+1 high-vol regime (fast RV > rolling median of fast RV over ``slow`` days), -1 low-vol, 0 unknown."""
    rv = daily_realized_vol(p, fast)
    out = np.zeros(p.n_days, dtype=int)
    for t in range(p.n_days):
        hist = rv[max(0, t - slow):t]
        hist = hist[~np.isnan(hist)]
        if len(hist) >= slow // 2 and not np.isnan(rv[t]):
            out[t] = 1 if rv[t] > np.median(hist) else -1
    return out


def day_type(p: DayPanel) -> np.ndarray:
    """Ex-post label for journaling/analytics only: 'trend' if |C-O| >= 0.6 * range else 'range'."""
    rng = p.high.max(axis=1) - p.low.min(axis=1)
    body = np.abs(p.day_close - p.day_open)
    return np.where(body >= 0.6 * np.maximum(rng, 1e-9), "trend", "range")
