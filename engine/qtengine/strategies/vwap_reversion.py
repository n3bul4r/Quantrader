"""S3 — Regime-gated VWAP reversion (RESEARCH CANDIDATE — no capital until validated).

Hypothesis: on calm days (low realized-vol regime — a proxy for dealers being long
gamma, which dampens intraday volatility per Adams et al. on 0DTE flows) and while price
stays *inside* the noise area (i.e. S1 has no signal), excursions from session VWAP
mean-revert. It is designed to be active exactly when S1 is idle, giving a
complementary (negatively-correlated-in-regime) return stream.

Evidence status: weak. No peer-reviewed ES/NQ study validates VWAP-band fades after
costs; independent reproductions of VWAP strategies decay out-of-sample. Treat the
planning edge as ZERO until it passes the validation gate (walk-forward + DSR > 0.95).

Rules:
    Window          10:00-15:00 ET, max 2 entries/day, 15-minute cooldown after exit
    Regime          vol_regime == -1 (14d RV below its 60d median)
    Inside noise    L_m < Close_m < U_m
    Band            VWAP_m -/+ k * sd_m  (sd_m = volume-weighted std of typical price)
    Long            Close_m <= VWAP_m - k*sd_m ; target VWAP (dynamic) ; stop entry - s*sd_m
    Short           mirror
    Time stop       60 minutes; hard exit 15:59.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .base import FeatureCache, OpenPosition, Strategy, Trade


@dataclass
class VwapReversion(Strategy):
    start_min: int = 30
    last_entry: int = 330
    exit_min: int = 389
    band_k: float = 2.0
    stop_k: float = 1.0
    time_stop: int = 60
    cooldown: int = 15
    max_entries: int = 2
    min_sd_sigma: float = 0.25   # sd_m must be >= this * sigma * open (avoid micro-R trades)
    low_vol_only: bool = True
    name: str = "S3_vwap_reversion"

    def generate(self, fc: FeatureCache) -> list[Trade]:
        p = fc.panel
        upper, lower, sig = fc.bands
        vwap, vsd = fc.vwap
        regime = fc.regime
        trades: list[Trade] = []
        for t in range(p.n_days):
            if np.isnan(sig[t]).any():
                continue
            if self.low_vol_only and regime[t] != -1:
                continue
            O, H, L_, C = p.open[t], p.high[t], p.low[t], p.close[t]
            pos: OpenPosition | None = None
            entries, last_exit = 0, -10_000
            for i in range(self.start_min, self.exit_min + 1):
                if pos is not None:
                    pos.update_excursions(H[i], L_[i])
                    pos.target = vwap[t, i - 1]  # resting limit at last known VWAP
                    fill = pos.stop_fill(O[i], H[i], L_[i])
                    reason = "stop"
                    if fill is None:
                        fill, reason = pos.target_fill(O[i], H[i], L_[i]), "target"
                    if fill is None and (i - pos.entry_min >= self.time_stop or i >= self.exit_min):
                        fill, reason = C[i], "time"
                    if fill is not None:
                        trades.append(pos.close(self.name, p.dates[t], i, fill, reason))
                        pos, last_exit = None, i
                    continue
                if entries >= self.max_entries or i > self.last_entry or i - last_exit < self.cooldown:
                    continue
                sd = vsd[t, i]
                if sd < self.min_sd_sigma * sig[t, i] * O[0]:
                    continue
                if not (lower[t, i] < C[i] < upper[t, i]):
                    continue
                dev = C[i] - vwap[t, i]
                if dev <= -self.band_k * sd:
                    side = 1
                elif dev >= self.band_k * sd:
                    side = -1
                else:
                    continue
                stop = C[i] - side * self.stop_k * sd
                pos = OpenPosition(side, i, C[i], stop, stop, target=vwap[t, i], meta={"dev_sd": float(dev / sd)})
                entries += 1
        return trades
