"""Overfitting diagnostics for large searches.

* CSCV / PBO — Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest
  Overfitting" (J. Computational Finance, 2017). Split the time axis into S blocks; for
  many combinations of S/2 blocks pick the best configuration in-sample and look at its
  rank out-of-sample. PBO = share of splits where the IS winner lands in the bottom half
  OOS. PBO ≈ 0.5+ means the "best" configuration is noise.
* Deflated Sharpe ratio (metrics.deflated_sharpe) — the IS winner's Sharpe must beat the
  Sharpe expected from the best of N unskilled trials.
"""
from __future__ import annotations

import itertools
import math

import numpy as np
from scipy import stats


def cscv_pbo(R: np.ndarray, S: int = 16, max_combos: int = 2000, seed: int = 0) -> dict:
    """R: [T, N] per-period returns of N configurations. Returns PBO, the logit distribution,
    and the IS->OOS performance degradation slope."""
    T, N = R.shape
    if N < 2 or T < S * 5:
        return {"pbo": float("nan"), "n_splits": 0}
    T2 = (T // S) * S
    blocks = R[:T2].reshape(S, T2 // S, N)
    bsum = blocks.sum(axis=1)                 # [S, N]
    bsq = (blocks ** 2).sum(axis=1)
    bn = T2 // S
    combos = list(itertools.combinations(range(S), S // 2))
    rng = np.random.default_rng(seed)
    if len(combos) > max_combos:
        combos = [combos[i] for i in rng.choice(len(combos), max_combos, replace=False)]
    logits, is_best, oos_of_best = [], [], []
    all_idx = np.arange(S)
    for c in combos:
        ins = np.array(c)
        oos = np.setdiff1d(all_idx, ins)

        def sharpe(idx):
            s = bsum[idx].sum(0)
            q = bsq[idx].sum(0)
            k = bn * len(idx)
            mu = s / k
            var = np.maximum(q / k - mu ** 2, 1e-18)
            return mu / np.sqrt(var)
        sr_is, sr_oos = sharpe(ins), sharpe(oos)
        best = int(np.argmax(sr_is))
        rank = stats.rankdata(sr_oos)[best] / (N + 1)
        logits.append(math.log(rank / (1 - rank)))
        is_best.append(sr_is[best])
        oos_of_best.append(sr_oos[best])
    logits = np.array(logits)
    slope = float(np.polyfit(is_best, oos_of_best, 1)[0]) if len(is_best) > 2 else float("nan")
    return {
        "pbo": float((logits <= 0).mean()),
        "n_splits": len(combos),
        "logit_median": float(np.median(logits)),
        "is_best_sr_mean": float(np.mean(is_best)),
        "oos_of_best_sr_mean": float(np.mean(oos_of_best)),
        "degradation_slope": slope,
        "logits_hist": np.histogram(np.clip(logits, -4, 4), bins=16, range=(-4, 4))[0].tolist(),
    }
