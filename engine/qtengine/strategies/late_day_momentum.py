"""S2 — Late-Session Momentum (satellite strategy).

Based on Gao, Han, Li & Zhou (JFE 2018): the return from the prior close to 15:30 ET
predicts the last half-hour return; Baltussen et al. (JFE 2021) show it across 60+
futures and tie its strength to dealer short-gamma hedging (stronger on high-vol days).

Rules:
    r_ROD     = Close_{t,15:30} / C_{t-1} - 1
    z         = r_ROD / std(r_ROD over previous 60 sessions)
    Enter at the 15:30 bar close in sign(r_ROD) iff |z| >= z_min
             (optionally only in the high realized-vol regime: proxy for short gamma)
    Stop      entry -/+ stop_mult * std(last-30-min price move over previous 60 sessions)
    Exit      15:59 bar close.

Honest note: the per-trade gross edge is a few basis points. On micros, all-in costs
(~$3.9/RT on MES incl. 2 ticks slippage) consume most of it — this is a satellite to
be enabled only if forward results beat costs (see docs/SYSTEM_DESIGN.md).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .base import FeatureCache, OpenPosition, Strategy, Trade


@dataclass
class LateDayMomentum(Strategy):
    signal_min: int = 360      # 15:30 bar
    exit_min: int = 389
    lookback: int = 60
    z_min: float = 0.75
    stop_mult: float = 1.5
    high_vol_only: bool = True
    name: str = "S2_late_momentum"

    def generate(self, fc: FeatureCache) -> list[Trade]:
        p = fc.panel
        pc = p.prev_close
        r_rod = p.close[:, self.signal_min] / pc - 1.0
        last_move = p.close[:, self.exit_min] - p.close[:, self.signal_min]
        regime = fc.regime
        trades: list[Trade] = []
        for t in range(self.lookback + 1, p.n_days):
            hist = r_rod[t - self.lookback:t]
            sd = hist.std(ddof=1)
            if not np.isfinite(sd) or sd <= 0:
                continue
            z = r_rod[t] / sd
            if abs(z) < self.z_min:
                continue
            if self.high_vol_only and regime[t] != 1:
                continue
            side = 1 if z > 0 else -1
            sd_last = last_move[t - self.lookback:t].std(ddof=1)
            entry = p.close[t, self.signal_min]
            stop = entry - side * self.stop_mult * sd_last
            pos = OpenPosition(side, self.signal_min, entry, stop, stop, meta={"z": float(z)})
            closed = None
            for i in range(self.signal_min + 1, self.exit_min + 1):
                pos.update_excursions(p.high[t, i], p.low[t, i])
                fill = pos.stop_fill(p.open[t, i], p.high[t, i], p.low[t, i])
                if fill is not None:
                    closed = pos.close(self.name, p.dates[t], i, fill, "stop")
                    break
            if closed is None:
                closed = pos.close(self.name, p.dates[t], self.exit_min, p.close[t, self.exit_min], "time")
            trades.append(closed)
        return trades
