"""Validation gate: walk-forward selection, sign-flip permutation test, bootstrap CIs,
and a deflated-Sharpe check that accounts for how many configurations were tried."""
from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from .backtest import Sizing, trades_frame
from .features import DayPanel
from .instruments import get_instrument
from .metrics import deflated_sharpe, trade_stats
from .strategies.base import FeatureCache, Strategy


def bootstrap_ci(x: np.ndarray, stat=np.mean, n_boot: int = 5000, alpha: float = 0.05, seed: int = 0) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    if len(x) < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    s = np.apply_along_axis(stat, 1, x[idx])
    return float(np.quantile(s, alpha / 2)), float(np.quantile(s, 1 - alpha / 2))


def sign_flip_pvalue(gross_pnl: np.ndarray, cost: np.ndarray | float, n_perm: int = 10000, seed: int = 0) -> float:
    """H0: direction choice has no skill. Randomly flip each trade's gross P&L sign,
    subtract costs, compare mean net P&L to the observed one. Valid for symmetric
    long/short strategies; one-sided p-value."""
    g = np.asarray(gross_pnl, dtype=float)
    c = np.broadcast_to(np.asarray(cost, dtype=float), g.shape)
    obs = (g - c).mean()
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1.0, 1.0], size=(n_perm, len(g)))
    null = (signs * g - c).mean(axis=1)
    return float((np.sum(null >= obs) + 1) / (n_perm + 1))


@dataclass
class WalkForwardResult:
    oos_trades: pd.DataFrame
    folds: list[dict]
    n_configs: int
    summary: dict


def walk_forward(
    panel: DayPanel,
    strategy_cls: type[Strategy],
    grid: dict[str, list],
    symbol: str = "MES",
    train_days: int = 250,
    test_days: int = 63,
    objective: str = "expectancy_r",
    min_trades: int = 30,
) -> WalkForwardResult:
    """Anchored-free rolling walk-forward. Features are causal, so every configuration is
    simulated once over the full panel and trades are then split by date per fold."""
    ins = get_instrument(symbol)
    fc = FeatureCache(panel)
    keys = list(grid)
    configs = [dict(zip(keys, vals)) for vals in itertools.product(*(grid[k] for k in keys))]
    frames = []
    for cfg in configs:
        tf = trades_frame(strategy_cls(**cfg).generate(fc), ins, Sizing())
        frames.append(tf)
    dates = pd.DatetimeIndex(panel.dates)
    folds, oos = [], []
    start = 15
    while start + train_days + test_days <= len(dates):
        tr0, tr1 = dates[start], dates[start + train_days - 1]
        te0, te1 = dates[start + train_days], dates[start + train_days + test_days - 1]
        best, best_score = None, -np.inf
        for ci, tf in enumerate(frames):
            if not len(tf):
                continue
            tr = tf[(tf.date >= tr0) & (tf.date <= tr1)]
            if len(tr) < min_trades:
                continue
            score = trade_stats(tr.pnl.to_numpy(), tr.r_net.to_numpy()).get(objective, -np.inf)
            if score > best_score:
                best, best_score = ci, score
        if best is not None:
            te = frames[best]
            te = te[(te.date >= te0) & (te.date <= te1)].copy()
            te["fold"] = len(folds)
            oos.append(te)
            folds.append({"train": (str(tr0.date()), str(tr1.date())), "test": (str(te0.date()), str(te1.date())),
                          "config": configs[best], "train_score": float(best_score), "test_trades": len(te)})
        start += test_days
    oos_df = pd.concat(oos) if oos else pd.DataFrame()
    summary = {"n_configs": len(configs)}
    if len(oos_df):
        ts = trade_stats(oos_df.pnl.to_numpy(), oos_df.r_net.to_numpy())
        r = oos_df.r_net.to_numpy()
        sr = r.mean() / r.std(ddof=1)
        # variance of per-trade SR across configs (full sample) for the DSR benchmark
        srs = [f.r_net.mean() / f.r_net.std(ddof=1) for f in frames if len(f) > 10 and f.r_net.std() > 0]
        var_sr = float(np.var(srs, ddof=1)) if len(srs) > 1 else 0.0
        summary.update({
            "oos": ts,
            "oos_expectancy_r_ci95": bootstrap_ci(r),
            "sign_flip_p": sign_flip_pvalue(oos_df.gross.to_numpy(), oos_df.cost.to_numpy()),
            "dsr": deflated_sharpe(sr, len(r), stats.skew(r), stats.kurtosis(r, fisher=False), len(configs), var_sr),
        })
    return WalkForwardResult(oos_df, folds, len(configs), summary)


GATE = {
    "min_oos_trades": 200,
    "min_expectancy_r_lower_ci": 0.0,
    "max_sign_flip_p": 0.05,
    "min_dsr": 0.95,
}


def passes_gate(summary: dict, gate: dict = GATE) -> tuple[bool, list[str]]:
    """The promotion gate a strategy must clear before it touches an evaluation account."""
    reasons = []
    oos = summary.get("oos", {})
    if oos.get("n", 0) < gate["min_oos_trades"]:
        reasons.append(f"only {oos.get('n', 0)} OOS trades (< {gate['min_oos_trades']})")
    lo = summary.get("oos_expectancy_r_ci95", (np.nan, np.nan))[0]
    if not (lo > gate["min_expectancy_r_lower_ci"]):
        reasons.append(f"95% CI lower bound of expectancy {lo:.3f}R not > 0")
    if not (summary.get("sign_flip_p", 1.0) <= gate["max_sign_flip_p"]):
        reasons.append(f"sign-flip p={summary.get('sign_flip_p', 1.0):.3f} > {gate['max_sign_flip_p']}")
    if not (summary.get("dsr", 0.0) >= gate["min_dsr"]):
        reasons.append(f"deflated Sharpe {summary.get('dsr', 0.0):.2f} < {gate['min_dsr']}")
    return (not reasons), reasons
