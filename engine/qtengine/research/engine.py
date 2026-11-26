"""Massive strategy search under Topstep constraints.

Pipeline
    1. Build features once per market (VWAP, noise width for every lookback, vol regime).
    2. Enumerate / randomly sample thousands of configurations across strategy families.
    3. Run each through a JIT kernel → trades → daily net R series (costs included).
    4. Score every configuration, then judge the *search itself*:
         - walk-forward: re-select the best config on a rolling train window, trade it on
           the next test window → the honest out-of-sample curve of "what the search finds"
         - CSCV probability of backtest overfitting (PBO)
         - deflated Sharpe of the in-sample winner given N trials
    5. Feed the walk-forward OOS trades into the Topstep lifecycle simulator: the final
       objective is net $ under the real account rules, not Sharpe.
"""
from __future__ import annotations

import itertools
import math
import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from ..features import DayPanel, noise_sigma, session_vwap, vol_regime
from ..instruments import get_instrument
from ..metrics import deflated_sharpe, probabilistic_sharpe
from . import kernels as K
from .overfit import cscv_pbo

# ----------------------------------------------------------------------------- search space
DEFAULT_SPACE: dict[str, dict[str, list]] = {
    "NAM": {  # noise-area momentum (+ high-win-rate target variants)
        "lookback": [7, 14, 21],
        "band_mult": [0.6, 0.8, 1.0, 1.2, 1.5],
        "first_dec": [15, 30, 60],
        "dec_every": [15, 30, 60],
        "last_entry": [240, 330, 360],
        "exit_min": [330, 389],
        "stop_floor": [0.3, 0.5, 1.0],
        "trail_mode": [0, 1, 2, 3],
        "target_r": [0.0, 0.5, 1.0, 2.0, 3.0],
        "max_entries": [1, 3],
        "regime_filter": [0, 1, -1],
        "direction": [0, 1],
    },
    "ORB": {
        "or_len": [5, 15, 30, 60],
        "last_entry": [120, 240, 360],
        "exit_min": [240, 389],
        "stop_frac": [0.25, 0.5, 1.0],
        "target_r": [0.0, 0.5, 1.0, 2.0, 4.0],
        "max_entries": [1, 2],
        "regime_filter": [0, 1, -1],
        "direction": [0, 1],
    },
    "VWR": {  # VWAP reversion: the classic 'high win rate' family
        "lookback": [14],
        "start_min": [15, 30, 60],
        "last_entry": [240, 330],
        "band_k": [1.0, 1.5, 2.0, 2.5],
        "stop_k": [0.5, 1.0, 2.0],
        "target_mode": [0, 1],
        "time_stop": [15, 30, 60, 120],
        "max_entries": [1, 3],
        "regime_filter": [0, 1, -1],
        "inside_noise": [0, 1],
    },
    "LDM": {
        "signal_min": [330, 360],
        "exit_min": [389],
        "lookback": [20, 60],
        "z_min": [0.0, 0.5, 1.0, 1.5],
        "stop_mult": [1.0, 2.0, 4.0],
        "regime_filter": [0, 1, -1],
    },
}


def grid(space: dict[str, list]) -> list[dict]:
    keys = list(space)
    return [dict(zip(keys, v)) for v in itertools.product(*(space[k] for k in keys))]


def sample_configs(space: dict[str, dict[str, list]], n_per_family: int | None, seed: int = 0) -> list[tuple[str, dict]]:
    rng = np.random.default_rng(seed)
    out = []
    for fam, sp in space.items():
        g = grid(sp)
        if n_per_family is not None and len(g) > n_per_family:
            g = [g[i] for i in rng.choice(len(g), n_per_family, replace=False)]
        out += [(fam, c) for c in g]
    return out


# ----------------------------------------------------------------------------- features + runner
@dataclass
class MarketFeatures:
    symbol: str
    panel: DayPanel
    vwap: np.ndarray
    vsd: np.ndarray
    regime: np.ndarray
    sig: dict = field(default_factory=dict)
    point_value: float = 5.0
    cost_rt: float = 3.9
    tick: float = 0.25

    @classmethod
    def build(cls, panel: DayPanel, symbol: str, lookbacks=(7, 14, 21), cost_rt: float | None = None):
        ins = get_instrument(symbol)
        v, sd = session_vwap(panel)
        f = cls(symbol, panel, v, sd, vol_regime(panel).astype(np.int64), {},
                ins.point_value, ins.cost_rt() if cost_rt is None else cost_rt, ins.tick_size)
        for lb in lookbacks:
            f.sig[lb] = noise_sigma(panel, lb)
        return f


def _fit_session(p: dict, M: int) -> dict:
    """Clamp minute-based parameters to the market's session length (equity = 390, crude = 330, gold = 310)."""
    q = dict(p)
    for k in ("exit_min",):
        if k in q:
            q[k] = min(q[k], M - 1)
    for k in ("last_entry", "signal_min"):
        if k in q:
            q[k] = min(q[k], M - 30)          # equity: 360 = 15:30 ET, unchanged
    for k in ("first_dec", "or_len", "start_min"):
        if k in q:
            q[k] = min(q[k], M - 61)
    return q


def run_config(mf: MarketFeatures, fam: str, p: dict) -> np.ndarray:
    P = mf.panel
    D = P.n_days
    p = _fit_session(p, P.close.shape[1])
    out = np.zeros((D * 4 + 8, K.NCOL))
    if fam == "NAM":
        n = K.noise_momentum(P.open, P.high, P.low, P.close, mf.vwap, mf.sig[p["lookback"]], P.day_open, P.prev_close,
                             mf.regime, p["band_mult"], p["first_dec"], p["dec_every"], p["last_entry"], p["exit_min"],
                             p["stop_floor"], p["trail_mode"], p["target_r"], p["max_entries"], p["regime_filter"],
                             p["direction"], out)
    elif fam == "ORB":
        n = K.opening_range(P.open, P.high, P.low, P.close, P.day_open, mf.regime, p["or_len"], p["last_entry"],
                            p["exit_min"], p["stop_frac"], p["target_r"], p["max_entries"], p["regime_filter"],
                            p["direction"], 4 * mf.tick, out)
    elif fam == "VWR":
        n = K.vwap_reversion(P.open, P.high, P.low, P.close, mf.vwap, mf.vsd, mf.sig[p["lookback"]], P.day_open,
                             P.prev_close, mf.regime, p["start_min"], p["last_entry"], P.close.shape[1] - 1, p["band_k"], p["stop_k"],
                             p["target_mode"], p["time_stop"], p["max_entries"], p["regime_filter"], p["inside_noise"], out)
    elif fam == "LDM":
        n = K.late_momentum(P.open, P.high, P.low, P.close, P.prev_close, mf.regime, p["signal_min"], p["exit_min"],
                            p["lookback"], p["z_min"], p["stop_mult"], p["regime_filter"], out)
    else:
        raise KeyError(fam)
    return out[:n]


def trades_to_r(tr: np.ndarray, mf: MarketFeatures, min_risk_ticks: float = 4) -> tuple[np.ndarray, np.ndarray]:
    """Net R per trade (1R = initial stop distance, costs charged in R) and validity mask."""
    risk = np.abs(tr[:, 4] - tr[:, 6])
    ok = risk >= min_risk_ticks * mf.tick
    r = np.where(ok, tr[:, 1] * (tr[:, 5] - tr[:, 4]) / np.maximum(risk, 1e-9) - mf.cost_rt / (np.maximum(risk, 1e-9) * mf.point_value), 0.0)
    return r, ok


def daily_r(tr: np.ndarray, r: np.ndarray, ok: np.ndarray, D: int) -> np.ndarray:
    d = np.zeros(D)
    np.add.at(d, tr[ok, 0].astype(np.int64), r[ok])
    return d


@dataclass
class SearchResult:
    configs: list[tuple[str, dict]]
    R: np.ndarray                 # [D, N] daily net R per config
    scores: pd.DataFrame
    wf: dict
    pbo: dict
    dsr_best: float
    elapsed_s: float
    symbol: str
    dates: list

    def leaderboard(self, k: int = 25) -> pd.DataFrame:
        return self.scores.sort_values("sharpe_is", ascending=False).head(k)


def _sr(x: np.ndarray) -> float:
    s = x.std()
    return float(x.mean() / s * math.sqrt(252)) if s > 0 else 0.0


def run_search(mf: MarketFeatures, configs: list[tuple[str, dict]], is_frac: float = 0.7,
               wf_train: int = 504, wf_test: int = 63, min_trades: int = 40, warmup: int = 61,
               progress=None) -> SearchResult:
    t0 = time.time()
    D = mf.panel.n_days
    N = len(configs)
    R = np.zeros((D, N))
    rows = []
    cut = warmup + int((D - warmup) * is_frac)
    for j, (fam, p) in enumerate(configs):
        tr = run_config(mf, fam, p)
        r, ok = trades_to_r(tr, mf)
        R[:, j] = daily_r(tr, r, ok, D)
        rv = r[ok]
        days = tr[ok, 0]
        is_m, oos_m = days < cut, days >= cut
        rows.append({
            "id": j, "family": fam, "params": p, "trades": int(ok.sum()),
            "trades_per_day": float(ok.sum() / max(D - warmup, 1)),
            "win_rate": float((rv > 0).mean()) if len(rv) else 0.0,
            "exp_r": float(rv.mean()) if len(rv) else 0.0,
            "exp_r_is": float(rv[is_m].mean()) if is_m.any() else 0.0,
            "exp_r_oos": float(rv[oos_m].mean()) if oos_m.any() else 0.0,
            "pf": float(rv[rv > 0].sum() / max(-rv[rv <= 0].sum(), 1e-9)) if len(rv) else 0.0,
            "sharpe_is": _sr(R[warmup:cut, j]),
            "sharpe_oos": _sr(R[cut:, j]),
            "trades_is": int(is_m.sum()),
        })
        if progress and j % 250 == 0:
            progress(j, N)
    scores = pd.DataFrame(rows)
    valid = scores["trades_is"] >= min_trades
    Rv = R[warmup:, valid.to_numpy()]
    # --- walk-forward re-selection: the honest OOS of the search procedure
    oos_daily, picks = [], []
    start = warmup
    while start + wf_train + wf_test <= D:
        tr_sl = slice(start, start + wf_train)
        te_sl = slice(start + wf_train, start + wf_train + wf_test)
        sr = R[tr_sl].mean(0) / np.maximum(R[tr_sl].std(0), 1e-12)
        sr[~valid.to_numpy()] = -np.inf
        b = int(np.argmax(sr))
        oos_daily.append(R[te_sl, b])
        picks.append({"test_start": str(mf.panel.dates[te_sl.start].date()), "config": b, "family": configs[b][0],
                      "train_sharpe": float(sr[b] * math.sqrt(252)), "test_sharpe": _sr(R[te_sl, b])})
        start += wf_test
    oos = np.concatenate(oos_daily) if oos_daily else np.array([])
    wf = {"oos_daily_r": oos.tolist(), "picks": picks,
          "oos_sharpe": _sr(oos) if len(oos) else None,
          "oos_mean_daily_r": float(oos.mean()) if len(oos) else None,
          "oos_psr": probabilistic_sharpe(oos.mean() / oos.std(), len(oos), stats.skew(oos), stats.kurtosis(oos, fisher=False))
          if len(oos) > 10 and oos.std() > 0 else None}
    pbo = cscv_pbo(Rv) if Rv.shape[1] > 1 else {"pbo": float("nan")}
    # --- deflated Sharpe of the IS winner, with raw and *effective* number of trials
    is_sr_daily = (scores.loc[valid, "sharpe_is"] / math.sqrt(252)).to_numpy()
    dsr = float("nan")
    n_eff = effective_trials(R[warmup:cut, valid.to_numpy()])
    if len(is_sr_daily) > 1:
        jbest = int(scores.loc[valid, "sharpe_is"].idxmax())
        x = R[warmup:cut, jbest]
        args = (x.mean() / x.std(), len(x), stats.skew(x), stats.kurtosis(x, fisher=False))
        var_sr = float(np.var(is_sr_daily, ddof=1))
        dsr = deflated_sharpe(*args, int(valid.sum()), var_sr)
        pbo["dsr_effective"] = deflated_sharpe(*args, max(int(round(n_eff)), 2), var_sr)
        pbo["n_effective_trials"] = n_eff
    return SearchResult(configs, R, scores, wf, pbo, dsr, time.time() - t0, mf.symbol, mf.panel.dates)


def effective_trials(R: np.ndarray, max_cols: int = 2500, seed: int = 0) -> float:
    """Effective number of independent strategies = participation ratio (Σλ)²/Σλ² of the
    correlation matrix of their daily returns (computed on a random subset of columns)."""
    cols = R.shape[1]
    if cols < 2:
        return float(cols)
    idx = np.random.default_rng(seed).choice(cols, min(cols, max_cols), replace=False)
    X = R[:, idx]
    X = X[:, X.std(0) > 0]
    if X.shape[1] < 2:
        return 1.0
    C = np.corrcoef(X, rowvar=False)
    lam = np.clip(np.linalg.eigvalsh(C), 0, None)
    return float(lam.sum() ** 2 / (lam ** 2).sum())


def config_trades(mf: MarketFeatures, fam: str, p: dict) -> pd.DataFrame:
    """Trade table for one configuration (for EmpiricalTradeModel / inspection)."""
    tr = run_config(mf, fam, p)
    r, ok = trades_to_r(tr, mf)
    risk = np.abs(tr[:, 4] - tr[:, 6])
    df = pd.DataFrame({
        "day": tr[:, 0].astype(int), "side": tr[:, 1], "entry_min": tr[:, 2], "exit_min": tr[:, 3],
        "entry": tr[:, 4], "exit": tr[:, 5], "stop": tr[:, 6], "risk_pts": risk,
        "r_gross": tr[:, 1] * (tr[:, 5] - tr[:, 4]) / np.maximum(risk, 1e-9),
        "r_net": r, "mae_r": tr[:, 7] / np.maximum(risk, 1e-9), "mfe_r": tr[:, 8] / np.maximum(risk, 1e-9)})
    return df[ok].reset_index(drop=True)


def wf_oos_trades(mf: MarketFeatures, res: SearchResult, wf_train: int = 504, wf_test: int = 63, warmup: int = 61) -> pd.DataFrame:
    """Trades actually taken by the walk-forward procedure in its test windows."""
    frames = []
    start = warmup
    for pk in res.wf["picks"]:
        fam, p = res.configs[pk["config"]]
        t = config_trades(mf, fam, p)
        lo, hi = start + wf_train, start + wf_train + wf_test
        frames.append(t[(t.day >= lo) & (t.day < hi)].assign(family=fam))
        start += wf_test
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def family_summary(res: SearchResult, min_trades: int = 40) -> pd.DataFrame:
    s = res.scores[res.scores.trades_is >= min_trades]
    rows = []
    for fam, g in s.groupby("family"):
        b = g.loc[g.sharpe_is.idxmax()]
        hw = g[g.win_rate >= 0.6]
        rows.append({"family": fam, "configs": len(g), "median_sharpe_is": g.sharpe_is.median(),
                     "best_sharpe_is": b.sharpe_is, "best_sharpe_oos": b.sharpe_oos,
                     "share_oos_positive": float((g.sharpe_oos > 0).mean()),
                     "high_winrate_configs": len(hw),
                     "high_winrate_median_exp_r_oos": float(hw.exp_r_oos.median()) if len(hw) else float("nan")})
    return pd.DataFrame(rows)
