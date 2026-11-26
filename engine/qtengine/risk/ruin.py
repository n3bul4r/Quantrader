"""Risk of ruin: closed-form diffusion results + model-free Monte Carlo.

Diffusion approximations treat cumulative P&L as Brownian motion with drift mu and
volatility sigma per unit time (per trade or per day — be consistent).

* Fixed barriers (static drawdown):   P(hit +T before -D)
* No target:                           P(ever hit -D) = exp(-2 mu D / sigma^2)
* Trailing drawdown of size D (Lehoczky 1977 / Taylor 1975): the high-water-mark gain
  at the moment the trailing stop is first hit is Exponential with mean
        m = (sigma^2 / (2 mu)) * (exp(2 mu D / sigma^2) - 1)         (m = D when mu = 0)
  so P(high-water mark rises by L before the trailing stop is hit) = exp(-L / m).
  For prop firms whose trailing MLL locks once the HWM is D above start, the chance of
  ever reaching the lock is exp(-D / m)  -> 36.8% for a zero-edge trader.
* Lundberg/Cramer: for i.i.d. trade P&L X with E[X] > 0, the adjustment coefficient
  lambda solves E[exp(-lambda X)] = 1 and P(ruin from buffer D) <= exp(-lambda D).
"""
from __future__ import annotations

import math

import numpy as np
from scipy.optimize import brentq


def bm_prob_target_before_ruin(mu: float, sigma: float, target: float, ruin: float) -> float:
    """P(cumulative P&L reaches +target before -ruin) for BM(mu, sigma)."""
    if sigma <= 0:
        return 1.0 if mu > 0 else 0.0
    a = 2 * mu / sigma ** 2
    if abs(a) < 1e-12:
        return ruin / (ruin + target)
    # P = (e^{aD} - 1) / (e^{aD} - e^{-aT}) ; computed stably
    num = math.expm1(a * ruin)
    den = num - math.expm1(-a * target)
    return float(num / den)


def bm_prob_ruin_infinite(mu: float, sigma: float, ruin: float) -> float:
    if mu <= 0:
        return 1.0
    return float(math.exp(-2 * mu * ruin / sigma ** 2))


def trailing_hwm_mean(mu: float, sigma: float, dd: float) -> float:
    """Mean high-water-mark gain at the first time a trailing drawdown of ``dd`` occurs."""
    a = 2 * mu / sigma ** 2
    if abs(a) < 1e-12:
        return dd
    return float(math.expm1(a * dd) / a)


def prob_reach_lock_before_trailing_breach(mu: float, sigma: float, dd: float, lock_gain: float) -> float:
    m = trailing_hwm_mean(mu, sigma, dd)
    if m <= 0:
        return 0.0
    return float(math.exp(-lock_gain / m))


def expected_time_to_trailing_breach(mu: float, sigma: float, dd: float) -> float:
    """E[time until a drawdown of size dd first occurs] for BM (Taylor 1975)."""
    a = 2 * mu / sigma ** 2
    if abs(a) < 1e-12:
        return dd ** 2 / sigma ** 2
    return float((math.exp(a * dd) - 1 - a * dd) / (a * mu))


def lundberg_coefficient(pnl: np.ndarray) -> float:
    """Adjustment coefficient lambda > 0 with mean(exp(-lambda X)) = 1. Returns 0 if E[X] <= 0."""
    x = np.asarray(pnl, dtype=float)
    if x.mean() <= 0 or (x < 0).sum() == 0:
        return 0.0 if x.mean() <= 0 else float("inf")
    f = lambda lam: np.mean(np.exp(-lam * x)) - 1.0
    hi = 1.0 / max(np.abs(x).max(), 1e-9)
    while f(hi) < 0:
        hi *= 2
        if hi > 1e6:
            return float("inf")
    return float(brentq(f, 1e-12, hi))


def lundberg_ruin_bound(pnl: np.ndarray, buffer: float) -> float:
    lam = lundberg_coefficient(pnl)
    if lam == 0.0:
        return 1.0
    return float(math.exp(-lam * buffer))


def monte_carlo_ruin(
    pnl_samples: np.ndarray,
    ruin: float,
    target: float | None = None,
    horizon: int = 500,
    n_paths: int = 20000,
    trailing: bool = False,
    lock_gain: float | None = None,
    seed: int = 0,
) -> dict:
    """Bootstrap i.i.d. P&L draws (per trade or per day). Ruin barrier is -ruin below start
    (static) or below the running high-water mark (trailing, optionally locking once the
    HWM gain reaches lock_gain — e.g. Topstep/Apex MLL that stops at the start balance)."""
    rng = np.random.default_rng(seed)
    x = np.asarray(pnl_samples, dtype=float)
    draws = x[rng.integers(0, len(x), size=(n_paths, horizon))]
    eq = np.cumsum(draws, axis=1)
    if trailing:
        hwm = np.maximum.accumulate(np.maximum(eq, 0.0), axis=1)
        floor = hwm - ruin
        if lock_gain is not None:
            floor = np.minimum(floor, lock_gain - ruin)
    else:
        floor = np.full_like(eq, -ruin)
    ruined = eq <= floor
    t_ruin = np.where(ruined.any(axis=1), ruined.argmax(axis=1), horizon)
    if target is not None:
        hit = eq >= target
        t_hit = np.where(hit.any(axis=1), hit.argmax(axis=1), horizon)
        success = t_hit < t_ruin
        return {
            "p_target_first": float(success.mean()),
            "p_ruin_first": float((t_ruin < t_hit).mean()),
            "p_neither": float(((t_ruin == horizon) & (t_hit == horizon)).mean()),
            "median_steps_to_target": float(np.median(t_hit[success])) if success.any() else float("nan"),
        }
    return {"p_ruin": float((t_ruin < horizon).mean()),
            "median_steps_to_ruin": float(np.median(t_ruin[t_ruin < horizon])) if (t_ruin < horizon).any() else float("nan")}
