"""Position sizing for prop-firm accounts.

Core idea: size off the *drawdown buffer* (equity - max-loss level), not the nominal
account size. A '$50K' account with a $2,000 trailing MLL is economically a $2,000
account with free leverage; every sizing decision is a fraction of that buffer.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ..instruments import Instrument


def contracts_for_risk(risk_dollars: float, stop_points: float, ins: Instrument,
                       include_costs: bool = True, round_up_tolerance: float = 1.25,
                       max_contracts: int = 50) -> int:
    per = stop_points * ins.point_value + (ins.cost_rt() if include_costs else 0.0)
    if per <= 0 or risk_dollars <= 0:
        return 0
    n = math.floor(risk_dollars / per)
    if n == 0 and per <= round_up_tolerance * risk_dollars:
        n = 1
    return min(n, max_contracts)


def vol_target_contracts(target_daily_vol_dollars: float, price: float, daily_vol_pct: float,
                         ins: Instrument, max_contracts: int = 50) -> int:
    """Zarattini-style volatility targeting expressed in $: contracts such that one
    day's expected P&L std ~= target. daily_vol_pct is e.g. 0.011 for 1.1%."""
    per = price * daily_vol_pct * ins.point_value
    return max(0, min(max_contracts, math.floor(target_daily_vol_dollars / per))) if per > 0 else 0


def kelly_fraction_r(r_multiples: np.ndarray) -> float:
    """Growth-optimal fraction of capital to risk per trade, for outcomes in R.
    Solves max E[log(1 + f R)] numerically (exact, not the mu/sigma^2 approximation)."""
    r = np.asarray(r_multiples, dtype=float)
    if r.mean() <= 0:
        return 0.0
    lo, hi = 0.0, 0.999 / max(-r.min(), 1e-9)
    g = lambda f: np.mean(r / (1 + f * r))  # derivative of E log
    if g(hi) > 0:
        return hi
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if g(mid) > 0 else (lo, mid)
    return (lo + hi) / 2


@dataclass
class BufferSizer:
    """risk$ per trade = clip(fraction * buffer, min_risk, max_risk), additionally
    capped so that a full stop-out (plus slippage allowance) cannot breach the daily
    loss limit, and halved while the buffer is below ``defensive_below`` of its
    starting value."""
    fraction: float = 0.10
    min_risk: float = 75.0
    max_risk: float = 600.0
    dll_safety: float = 0.8       # never risk more than 80% of the remaining daily allowance
    defensive_below: float = 0.5
    defensive_factor: float = 0.5
    initial_buffer: float = 2000.0

    def risk_dollars(self, buffer: float, daily_remaining: float | None = None) -> float:
        if buffer <= 0:
            return 0.0
        r = self.fraction * buffer
        if buffer < self.defensive_below * self.initial_buffer:
            r *= self.defensive_factor
        r = min(max(r, self.min_risk), self.max_risk, buffer * 0.5)
        if daily_remaining is not None:
            r = min(r, self.dll_safety * max(daily_remaining, 0.0))
        return max(r, 0.0)


@dataclass
class ScalingTier:
    min_buffer: float      # buffer ($) needed to be in this tier
    risk_dollars: float    # risk per trade in this tier


@dataclass
class ScalingPolicy:
    """Step-up only when BOTH capital and evidence allow it; step down on capital alone.

    * Up: buffer >= next tier threshold AND the lower 90% confidence bound of the
      rolling expectancy (last ``window`` trades, in R) is > 0 AND live expectancy
      is not significantly below the backtest expectancy (drift check).
    * Down: buffer < current tier threshold * (1 - hysteresis) -> drop immediately.
    """
    tiers: list[ScalingTier] = field(default_factory=lambda: [
        ScalingTier(0, 100), ScalingTier(2500, 150), ScalingTier(3500, 200),
        ScalingTier(5000, 300), ScalingTier(8000, 450),
    ])
    window: int = 60
    hysteresis: float = 0.15
    backtest_expectancy_r: float = 0.05

    def evaluate(self, current_tier: int, buffer: float, recent_r: np.ndarray) -> tuple[int, str]:
        tiers = self.tiers
        # step down
        while current_tier > 0 and buffer < tiers[current_tier].min_buffer * (1 - self.hysteresis):
            current_tier -= 1
            return current_tier, f"step down: buffer ${buffer:,.0f} below tier threshold"
        if current_tier + 1 >= len(tiers) or buffer < tiers[current_tier + 1].min_buffer:
            return current_tier, "hold: capital"
        r = np.asarray(recent_r, dtype=float)[-self.window:]
        if len(r) < self.window:
            return current_tier, f"hold: need {self.window} trades of evidence ({len(r)})"
        se = r.std(ddof=1) / math.sqrt(len(r))
        lcb = r.mean() - 1.2816 * se
        if lcb <= 0:
            return current_tier, f"hold: rolling expectancy LCB90 {lcb:.3f}R <= 0"
        if r.mean() < self.backtest_expectancy_r - 2 * se:
            return current_tier, "hold: live expectancy significantly below backtest (drift)"
        return current_tier + 1, "step up"
