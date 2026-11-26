"""Strategy interface and shared intraday position-management helpers.

Strategies emit trades in *price points* with an explicit initial stop, so the
risk layer can size every trade in R (risk units) independently of the signal.
Fills: decisions are taken on the close of minute bar i and filled at that close;
slippage is charged separately by the cost model (instruments.Instrument).
Stops: checked on every subsequent bar's high/low; a gap through the stop fills at
the bar open (worse than the stop). If target and stop are both inside one bar the
stop is assumed to fill first (conservative).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import cached_property

import numpy as np
import pandas as pd

from ..features import DayPanel, noise_bands, session_vwap, vol_regime


@dataclass
class Trade:
    strategy: str
    date: pd.Timestamp
    side: int            # +1 long, -1 short
    entry_min: int       # minutes from 09:30 (decision bar index)
    exit_min: int
    entry: float
    exit: float
    stop_init: float
    exit_reason: str     # stop | time | target | reverse | eod
    mae_pts: float = 0.0
    mfe_pts: float = 0.0
    meta: dict = field(default_factory=dict)

    @property
    def risk_pts(self) -> float:
        return abs(self.entry - self.stop_init)

    @property
    def pnl_pts(self) -> float:
        return self.side * (self.exit - self.entry)

    @property
    def r_gross(self) -> float:
        return self.pnl_pts / self.risk_pts if self.risk_pts > 0 else 0.0


class FeatureCache:
    """Computes panel features once and shares them between strategies."""

    def __init__(self, panel: DayPanel, lookback: int = 14):
        self.panel = panel
        self.lookback = lookback

    @cached_property
    def bands(self):
        return noise_bands(self.panel, self.lookback)

    @cached_property
    def vwap(self):
        return session_vwap(self.panel)

    @cached_property
    def regime(self):
        return vol_regime(self.panel)


class Strategy(ABC):
    name: str = "base"

    @abstractmethod
    def generate(self, fc: FeatureCache) -> list[Trade]:
        ...

    def params(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


@dataclass
class OpenPosition:
    side: int
    entry_min: int
    entry: float
    stop: float
    stop_init: float
    target: float | None = None
    mae: float = 0.0
    mfe: float = 0.0
    meta: dict = field(default_factory=dict)

    def update_excursions(self, hi: float, lo: float) -> None:
        if self.side > 0:
            self.mfe = max(self.mfe, hi - self.entry)
            self.mae = max(self.mae, self.entry - lo)
        else:
            self.mfe = max(self.mfe, self.entry - lo)
            self.mae = max(self.mae, hi - self.entry)

    def stop_fill(self, o: float, hi: float, lo: float) -> float | None:
        """Return fill price if the stop is hit on this bar, else None."""
        if self.side > 0 and lo <= self.stop:
            return min(self.stop, o)
        if self.side < 0 and hi >= self.stop:
            return max(self.stop, o)
        return None

    def target_fill(self, o: float, hi: float, lo: float) -> float | None:
        if self.target is None:
            return None
        if self.side > 0 and hi >= self.target:
            return max(self.target, o)
        if self.side < 0 and lo <= self.target:
            return min(self.target, o)
        return None

    def close(self, strategy: str, date, exit_min: int, price: float, reason: str) -> Trade:
        return Trade(strategy, date, self.side, self.entry_min, exit_min, self.entry, price,
                     self.stop_init, reason, self.mae, self.mfe, dict(self.meta))


def valid_day(arr: np.ndarray, t: int) -> bool:
    return not np.isnan(arr[t]).any()
