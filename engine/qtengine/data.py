"""Bar data loading, RTH session handling and a synthetic generator (tests/demo only).

Conventions
-----------
* DataFrame index: tz-aware ``DatetimeIndex`` in America/New_York, timestamp = bar START.
* Columns: open, high, low, close, volume.
* RTH = 09:30-16:00 ET -> 390 one-minute bars per full session.

Real data: export 1-minute OHLCV from Databento (GLBX.MDP3, continuous front month,
volume-roll), Rithmic, or Tradovate to CSV/Parquet and use :func:`load_bars`.
Synthetic data NEVER proves an edge — it exists so the pipeline can be tested.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

NY = "America/New_York"
RTH_START = "09:30"
RTH_END = "15:59"  # last 1-min bar start
RTH_MINUTES = 390


def load_bars(path: str | Path, tz_in: str = "UTC") -> pd.DataFrame:
    """Load OHLCV from CSV or Parquet. Expects a timestamp column (ts/timestamp/datetime/ts_event)."""
    path = Path(path)
    df = pd.read_parquet(path) if path.suffix in {".parquet", ".pq"} else pd.read_csv(path)
    ts_col = next((c for c in ("ts", "timestamp", "datetime", "ts_event", "time", "date") if c in df.columns), None)
    if ts_col is None:
        raise ValueError("No timestamp column found")
    idx = pd.to_datetime(df[ts_col], utc=False)
    if idx.dt.tz is None:
        idx = idx.dt.tz_localize(tz_in)
    df = df.drop(columns=[ts_col])
    df.index = pd.DatetimeIndex(idx).tz_convert(NY)
    df.columns = [c.lower() for c in df.columns]
    missing = {"open", "high", "low", "close"} - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    if "volume" not in df.columns:
        df["volume"] = 1.0
    return df.sort_index()[["open", "high", "low", "close", "volume"]]


def rth(df: pd.DataFrame) -> pd.DataFrame:
    """Restrict to regular trading hours."""
    return df.between_time(RTH_START, RTH_END)


def sessions(df: pd.DataFrame, min_bars: int = 300) -> list[tuple[pd.Timestamp, pd.DataFrame]]:
    """Split RTH bars into per-day sessions, dropping half days / broken sessions (< min_bars)."""
    out = []
    r = rth(df)
    for day, g in r.groupby(r.index.date):
        if len(g) >= min_bars:
            out.append((pd.Timestamp(day), g))
    return out


def minutes_from_open(index: pd.DatetimeIndex) -> np.ndarray:
    return ((index.hour - 9) * 60 + index.minute - 30).to_numpy()


def synthetic_bars(
    n_days: int = 500,
    start_price: float = 6800.0,
    daily_vol: float = 0.011,
    momentum: float = 0.0,
    seed: int = 0,
    start: str = "2023-01-02",
    tick: float = 0.25,
) -> pd.DataFrame:
    """Generate 1-minute RTH bars with U-shaped intraday volatility, stochastic daily
    volatility regimes, overnight gaps and an optional intraday-momentum component.

    ``momentum`` (kappa) adds drift proportional to tanh(standardised return-from-open):
    0.0 -> martingale (no edge for any strategy, by construction);
    ~0.05-0.15 -> trend persistence similar in spirit to documented intraday momentum.
    """
    rng = np.random.default_rng(seed)
    days = pd.bdate_range(start=start, periods=n_days)
    m = np.arange(RTH_MINUTES)
    w = 1.0 + 1.5 * np.exp(-m / 30.0) + 0.8 * np.exp(-(RTH_MINUTES - 1 - m) / 30.0)
    w = w / np.sqrt((w ** 2).sum())  # sum of squared minute weights = 1
    vol_shape = (w / w.mean())
    cum_w = np.sqrt(np.cumsum(w ** 2))

    log_regime = 0.0
    price = start_price
    frames = []
    for d in days:
        log_regime = 0.9 * log_regime + rng.normal(0, 0.25)
        sig_d = daily_vol * np.exp(log_regime - 0.5 * 0.25 ** 2 / (1 - 0.81))
        price *= np.exp(rng.normal(0, 0.35 * sig_d))  # overnight gap
        sig_m = 0.9 * sig_d * w
        rets = np.empty(RTH_MINUTES)
        cum = 0.0
        eps = rng.standard_t(df=5, size=RTH_MINUTES) / np.sqrt(5 / 3)
        for i in range(RTH_MINUTES):
            elapsed = cum_w[i] * 0.9 * sig_d
            drift = momentum * np.tanh(cum / elapsed) if i > 0 else 0.0
            rets[i] = sig_m[i] * (eps[i] + drift)
            cum += rets[i]
        closes = price * np.exp(np.cumsum(rets))
        opens = np.concatenate([[price], closes[:-1]])
        wick = np.abs(rng.normal(0, 0.35, size=(2, RTH_MINUTES))) * sig_m * closes
        highs = np.maximum(opens, closes) + wick[0]
        lows = np.minimum(opens, closes) - wick[1]
        vol = (1000 * vol_shape * np.exp(rng.normal(0, 0.3, RTH_MINUTES))).round()
        idx = pd.date_range(d + pd.Timedelta(hours=9, minutes=30), periods=RTH_MINUTES, freq="1min", tz=NY)
        f = pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": vol}, index=idx)
        frames.append(f)
        price = closes[-1]
    df = pd.concat(frames)
    for c in ("open", "high", "low", "close"):
        df[c] = (df[c] / tick).round() * tick
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)
    return df
