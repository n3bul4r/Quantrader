"""Performance statistics, including the multiple-testing-aware Probabilistic and
Deflated Sharpe Ratios (Bailey & Lopez de Prado 2012, 2014)."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats

EULER_GAMMA = 0.5772156649015329


def max_consecutive(mask: np.ndarray) -> int:
    best = cur = 0
    for v in mask:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


def trade_stats(pnl: np.ndarray, r: np.ndarray | None = None) -> dict:
    pnl = np.asarray(pnl, dtype=float)
    n = len(pnl)
    if n == 0:
        return {"n": 0}
    wins, losses = pnl[pnl > 0], pnl[pnl <= 0]
    gross_win, gross_loss = wins.sum(), -losses.sum()
    sd = pnl.std(ddof=1) if n > 1 else float("nan")
    out = {
        "n": n,
        "win_rate": len(wins) / n,
        "avg_win": wins.mean() if len(wins) else 0.0,
        "avg_loss": losses.mean() if len(losses) else 0.0,
        "payoff_ratio": (wins.mean() / -losses.mean()) if len(wins) and len(losses) and losses.mean() < 0 else float("nan"),
        "expectancy": pnl.mean(),
        "profit_factor": gross_win / gross_loss if gross_loss > 0 else float("inf"),
        "total": pnl.sum(),
        "std": sd,
        "t_stat": pnl.mean() / (sd / math.sqrt(n)) if n > 1 and sd > 0 else float("nan"),
        "largest_win": pnl.max(),
        "largest_loss": pnl.min(),
        "max_consec_losses": max_consecutive(pnl <= 0),
    }
    if r is not None and len(r):
        r = np.asarray(r, dtype=float)
        out.update({
            "expectancy_r": r.mean(),
            "avg_win_r": r[r > 0].mean() if (r > 0).any() else 0.0,
            "avg_loss_r": r[r <= 0].mean() if (r <= 0).any() else 0.0,
            "std_r": r.std(ddof=1) if len(r) > 1 else float("nan"),
        })
    return out


def drawdown(equity: np.ndarray) -> np.ndarray:
    eq = np.asarray(equity, dtype=float)
    return eq - np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]


def max_drawdown_duration(equity: np.ndarray) -> int:
    dd = drawdown(equity)
    return max_consecutive(dd < 0)


def daily_stats(daily: pd.Series | np.ndarray) -> dict:
    d = np.asarray(daily, dtype=float)
    n = len(d)
    if n < 2:
        return {"days": n}
    eq = np.cumsum(d)
    sd = d.std(ddof=1)
    downside = d[d < 0]
    total = d.sum()
    pos_total = d[d > 0].sum()
    sr_d = d.mean() / sd if sd > 0 else float("nan")
    return {
        "days": n,
        "mean_daily": d.mean(),
        "std_daily": sd,
        "sharpe_annual": sr_d * math.sqrt(252) if sd > 0 else float("nan"),
        "sortino_annual": d.mean() / downside.std(ddof=1) * math.sqrt(252) if len(downside) > 1 else float("nan"),
        "max_drawdown": drawdown(eq).min(),
        "max_dd_duration_days": max_drawdown_duration(eq),
        "pct_positive_days": (d > 0).mean(),
        "pct_flat_days": (d == 0).mean(),
        "best_day": d.max(),
        "worst_day": d.min(),
        # prop-firm consistency metric: best day share of total net profit
        "best_day_share": d.max() / total if total > 0 else float("nan"),
        "best_day_share_of_gross_wins": d.max() / pos_total if pos_total > 0 else float("nan"),
        "skew": float(stats.skew(d)),
        "kurtosis": float(stats.kurtosis(d, fisher=False)),
        "psr_vs_0": probabilistic_sharpe(sr_d, n, stats.skew(d), stats.kurtosis(d, fisher=False)),
    }


def probabilistic_sharpe(sr: float, n: int, skew: float, kurt: float, sr_star: float = 0.0) -> float:
    """P(true SR > sr_star) given an observed per-period SR over n observations.
    kurt is raw (non-excess) kurtosis."""
    if not np.isfinite(sr) or n < 2:
        return float("nan")
    denom = 1 - skew * sr + (kurt - 1) / 4 * sr ** 2
    if denom <= 0:
        return float("nan")
    return float(stats.norm.cdf((sr - sr_star) * math.sqrt(n - 1) / math.sqrt(denom)))


def expected_max_sharpe(n_trials: int, var_sr: float) -> float:
    """Expected maximum per-period SR among n_trials unskilled strategies (False Strategy Theorem)."""
    if n_trials <= 1:
        return 0.0
    z1 = stats.norm.ppf(1 - 1 / n_trials)
    z2 = stats.norm.ppf(1 - 1 / (n_trials * math.e))
    return math.sqrt(var_sr) * ((1 - EULER_GAMMA) * z1 + EULER_GAMMA * z2)


def deflated_sharpe(sr: float, n: int, skew: float, kurt: float, n_trials: int, var_sr: float) -> float:
    """DSR: PSR against the SR you would expect from the best of n_trials pure-noise backtests."""
    return probabilistic_sharpe(sr, n, skew, kurt, expected_max_sharpe(n_trials, var_sr))


def min_track_record_length(sr: float, skew: float, kurt: float, sr_star: float = 0.0, alpha: float = 0.05) -> float:
    """Observations needed for SR to be significantly > sr_star at confidence 1-alpha."""
    if sr <= sr_star:
        return float("inf")
    z = stats.norm.ppf(1 - alpha)
    return 1 + (1 - skew * sr + (kurt - 1) / 4 * sr ** 2) * (z / (sr - sr_star)) ** 2


def breakdown(trades: pd.DataFrame, by: str, pnl_col: str = "pnl", r_col: str = "r_net") -> pd.DataFrame:
    rows = []
    for key, g in trades.groupby(by, observed=True):
        s = trade_stats(g[pnl_col].to_numpy(), g[r_col].to_numpy() if r_col in g else None)
        rows.append({by: key, "n": s["n"], "win_rate": s["win_rate"], "expectancy": s["expectancy"],
                     "expectancy_r": s.get("expectancy_r", np.nan), "profit_factor": s["profit_factor"],
                     "total": s["total"]})
    return pd.DataFrame(rows)
