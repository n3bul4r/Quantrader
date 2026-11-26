"""Vectorised Monte Carlo of the full prop-firm lifecycle:

    buy evaluation -> trade -> (fail -> buy again) | (pass -> pay activation -> funded)
    funded -> collect payouts per the payout policy -> (blown -> buy a new evaluation)

Everything a trader actually cares about is an output: probability of passing,
time to first payout, payouts received, fees paid, and NET cash per year — per account
and scaled by the number of (copy-traded, hence perfectly correlated) accounts.

The economically correct way to think about a prop account: your downside is capped at
fees, your upside is the payouts. It is a call option on your edge, written by a firm
that sets the strike (target), the knock-out (trailing MLL) and the payout caps.
This simulator prices that option for a given trade model and sizing policy.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from .rules import PhaseRules, PropProgram


# ----------------------------------------------------------------------------- trade models
@dataclass
class TradeModel:
    """Parametric per-trade outcome model in R (gross of costs).

    win:  R ~ LogNormal with mean avg_win_r and coefficient of variation win_cv
    loss: R ~ -clip(Normal(avg_loss_r, loss_sd), 0.05, 1.0); with prob gap_prob the loss
          slips to -gap_r (fast-market stop slippage / gap)
    Per-contract $ risk ~ LogNormal(mean stop_dollars, cv stop_cv); costs per contract RT.
    """
    name: str = "custom"
    win_rate: float = 0.37
    avg_win_r: float = 1.85
    win_cv: float = 0.8
    avg_loss_r: float = 0.95
    loss_sd: float = 0.15
    gap_prob: float = 0.02
    gap_r: float = 1.6
    trades_per_day: float = 0.8
    max_trades_per_day: int = 3
    stop_dollars: float = 110.0     # MES: ~22 pts * $5
    stop_cv: float = 0.35
    cost_per_contract: float = 3.90  # MES: $1.40 fees + 2 ticks slippage

    def _mc(self, n: int = 400_000) -> dict:
        r, _, _, stop = self.sample(np.random.default_rng(12345), n)
        net = r - self.cost_per_contract / stop
        return {"gross": float(r.mean()), "net": float(net.mean()), "sd": float(net.std()),
                "pf": float(net[net > 0].sum() / -net[net <= 0].sum()), "win": float((net > 0).mean())}

    def expected_gross_r(self) -> float:
        return self._mc()["gross"]

    def expected_net_r(self) -> float:
        return self._mc()["net"]

    def profit_factor_net(self) -> float:
        return self._mc()["pf"]

    def annual_sharpe(self, trading_days: int = 252) -> float:
        m = self._mc()
        return m["net"] / m["sd"] * math.sqrt(self.trades_per_day * trading_days)

    def sample(self, rng: np.random.Generator, n: int):
        win = rng.random(n) < self.win_rate
        s2 = math.log(1 + self.win_cv ** 2)
        wr = rng.lognormal(math.log(self.avg_win_r) - s2 / 2, math.sqrt(s2), n)
        lr = -np.clip(rng.normal(self.avg_loss_r, self.loss_sd, n), 0.05, 1.0)
        gap = rng.random(n) < self.gap_prob
        lr = np.where(gap, -self.gap_r, lr)
        r = np.where(win, wr, lr)
        mae = np.where(win, rng.uniform(0.0, 0.8, n), -r)
        mfe = np.where(win, r * rng.uniform(1.0, 1.4, n), rng.uniform(0.0, 0.8, n))
        s2s = math.log(1 + self.stop_cv ** 2)
        stop = rng.lognormal(math.log(self.stop_dollars) - s2s / 2, math.sqrt(s2s), n)
        return r, mae, mfe, stop

    def summary(self) -> dict:
        m = self._mc()
        return {**asdict(self), "expected_gross_r": m["gross"], "expected_net_r": m["net"],
                "sd_net_r": m["sd"], "profit_factor_net": m["pf"], "net_win_rate": m["win"],
                "annual_sharpe": m["net"] / m["sd"] * math.sqrt(self.trades_per_day * 252)}


@dataclass
class EmpiricalTradeModel:
    """Bootstrap trade outcomes from a backtest/forward-test trade list
    (columns r_gross, mae_r, mfe_r, risk_pts) — preferred once real data exists."""
    r: np.ndarray
    mae: np.ndarray
    mfe: np.ndarray
    stop_dollars_arr: np.ndarray
    trades_per_day: float
    max_trades_per_day: int = 3
    cost_per_contract: float = 3.90
    name: str = "empirical"

    @classmethod
    def from_trades(cls, trades: pd.DataFrame, point_value: float, n_days: int, cost_per_contract: float, **kw):
        return cls(trades["r_gross"].to_numpy(), trades["mae_r"].to_numpy(), trades["mfe_r"].to_numpy(),
                   (trades["risk_pts"] * point_value).to_numpy(), len(trades) / max(n_days, 1),
                   cost_per_contract=cost_per_contract, **kw)

    def sample(self, rng, n):
        i = rng.integers(0, len(self.r), n)
        return self.r[i], self.mae[i], self.mfe[i], self.stop_dollars_arr[i]

    def expected_net_r(self) -> float:
        return float(np.mean(self.r - self.cost_per_contract / self.stop_dollars_arr))

    def summary(self) -> dict:
        return {"name": self.name, "n": len(self.r), "trades_per_day": self.trades_per_day,
                "expected_net_r": self.expected_net_r(), "win_rate": float((self.r > 0).mean())}


# ----------------------------------------------------------------------------- policies
@dataclass
class SimSizing:
    """mode 'fixed': risk_dollars per trade.
    mode 'buffer': risk = clip(fraction * buffer, min_risk, max_risk), halved while the
    buffer is below half of the starting max-loss."""
    mode: str = "fixed"
    risk_dollars: float = 200.0
    fraction: float = 0.10
    min_risk: float = 75.0
    max_risk: float = 600.0
    round_up_tolerance: float = 1.25
    funded_risk_dollars: float | None = None  # different fixed risk once funded (None = same)
    up_frac: float = 0.0                      # funded: add up_frac * (buffer - max_loss) to risk (scale UP only)
    up_max_risk: float = 5000.0


@dataclass
class PayoutPolicy:
    """When to pull money out of a funded account.
    min_profit_to_request: only request once profit above start >= this (builds a cushion first)
    request_fraction: request this fraction of the allowed amount"""
    min_profit_to_request: float = 0.0
    request_fraction: float = 1.0


@dataclass
class SimGuard:
    internal_daily_stop: float | None = None   # explicit $ daily stop; if None use daily_stop_r * base risk
    daily_stop_r: float | None = 2.0
    daily_profit_cap: float | None = None   # explicit cap on day P&L (stop trading once reached)
    auto_profit_cap: bool = True            # if no explicit cap: derive one from consistency rules
    max_consecutive_losses: int = 3


PRESET_MODELS = {
    # Planning case: published S1 edge (SPY Sharpe 1.33) after a 58% post-publication haircut
    # (McLean & Pontiff 2016) -> annual Sharpe ~0.56, net +0.064R / trade, PF ~1.10
    "S1_planning": TradeModel(name="S1_planning", win_rate=0.37),
    # Paper-like case: Sharpe ~1.26, net +0.147R / trade, PF ~1.25 (optimistic: in-sample level)
    "S1_optimistic": TradeModel(name="S1_optimistic", win_rate=0.40),
    # Zero GROSS edge, same payoff profile: what you get with no skill (costs only)
    "zero_edge": TradeModel(name="zero_edge", win_rate=0.333),
    # 'Prop-friendly' high-win-rate scalper with the SAME gross edge per R as S1_planning,
    # 3 trades/day, $50 stops: costs eat ~90% of the edge
    # Multi-market intraday-momentum basket (ES/NQ/CL/GC micros): same per-trade edge, but
    # ≈2.4 effectively independent bets/day (equity indices count as ~1.2 because ρ≈0.85)
    "basket_planning": TradeModel(name="basket_planning", win_rate=0.37, trades_per_day=2.4, max_trades_per_day=6),
    "basket_optimistic": TradeModel(name="basket_optimistic", win_rate=0.40, trades_per_day=2.4, max_trades_per_day=6),
    "scalper_planning": TradeModel(name="scalper_planning", win_rate=0.62, avg_win_r=0.75, win_cv=0.3,
                                   avg_loss_r=1.0, loss_sd=0.05, trades_per_day=3.0, max_trades_per_day=6,
                                   stop_dollars=50.0, stop_cv=0.2),
}


# ----------------------------------------------------------------------------- simulator
def _arr(phase: np.ndarray, ev: PhaseRules, fu: PhaseRules, attr: str, none_value: float) -> np.ndarray:
    a = getattr(ev, attr)
    b = getattr(fu, attr)
    a = none_value if a is None else a
    b = none_value if b is None else b
    return np.where(phase == 1, b, a).astype(float)


def simulate_lifecycle(
    program: PropProgram,
    model: TradeModel | EmpiricalTradeModel,
    sizing: SimSizing | None = None,
    guard: SimGuard | None = None,
    horizon_days: int = 252,
    n_paths: int = 10000,
    n_accounts: int = 1,
    single_attempt: bool = False,
    seed: int = 0,
    record_paths: bool = True,
    payout_policy: PayoutPolicy | None = None,
    return_cash_path: bool = False,
) -> dict:
    sizing = sizing or SimSizing()
    guard = guard or SimGuard()
    payout_policy = payout_policy or PayoutPolicy()
    rng = np.random.default_rng(seed)
    E, F = program.evaluation, program.funded
    P = n_paths
    INF = 1e18

    profit_cap_eval = profit_cap_fund = INF
    if guard.daily_profit_cap is not None:
        profit_cap_eval = profit_cap_fund = guard.daily_profit_cap
    elif guard.auto_profit_cap:
        # keep any single day safely below the consistency threshold
        if E.consistency_pct and E.profit_target:
            profit_cap_eval = 0.9 * E.consistency_pct * E.profit_target
        if F.payout_consistency_pct:
            profit_cap_fund = 0.9 * F.payout_consistency_pct * (F.payout_cap or 2000) + F.payout_reserve * 0.25
    if F.scaling_plan:
        sp_thr = np.array([t for t, _ in F.scaling_plan], dtype=float)
        sp_val = np.minimum(np.array([v for _, v in F.scaling_plan], dtype=float), F.max_micros)

    phase = np.zeros(P, dtype=int)          # 0 eval, 1 funded, 2 done
    p = np.zeros(P)
    mll = np.full(P, -E.max_loss)
    hwm = np.zeros(P)
    best_day = np.zeros(P)
    tdays = np.zeros(P, dtype=int)
    dphase = np.zeros(P, dtype=int)
    win_days = np.zeros(P, dtype=int)
    prof_since = np.zeros(P)
    best_since = np.zeros(P)
    fees = np.full(P, float(program.eval_fee))
    paid_gross = np.zeros(P)
    paid_net = np.zeros(P)
    n_payouts = np.zeros(P, dtype=int)
    evals = np.ones(P, dtype=int)
    passes = np.zeros(P, dtype=int)
    eval_fails = np.zeros(P, dtype=int)
    funded_blown = np.zeros(P, dtype=int)
    first_pass_day = np.full(P, -1)
    first_payout_day = np.full(P, -1)
    outcome = np.zeros(P, dtype=int)        # single_attempt: 1 pass, -1 fail, 0 unresolved
    funded_days = np.zeros(P, dtype=int)
    cash_path = np.zeros((horizon_days, P)) if (record_paths or return_cash_path) else None
    day_pnls_eval, day_pnls_fund = [], []

    cost = model.cost_per_contract
    for d in range(horizon_days):
        active = phase < 2
        if program.eval_fee_recurring_days:
            due = (phase == 0) & (dphase > 0) & (dphase % program.eval_fee_recurring_days == 0)
            fees += np.where(due, program.eval_fee, 0.0)
        is_f = phase == 1
        maxloss = _arr(phase, E, F, "max_loss", 0)
        lock = _arr(phase, E, F, "lock_level", INF)
        dll = _arr(phase, E, F, "daily_loss_limit", INF)
        dll_fail = np.where(is_f, F.dll_action == "fail", E.dll_action == "fail")
        intraday = np.where(is_f, F.drawdown_type == "intraday_trailing", E.drawdown_type == "intraday_trailing")
        static = np.where(is_f, F.drawdown_type == "static", E.drawdown_type == "static")
        cap = np.where(is_f, profit_cap_fund, profit_cap_eval)
        if F.scaling_plan:
            f_micros = sp_val[np.maximum(np.searchsorted(sp_thr, p, side="right") - 1, 0)]
        else:
            f_micros = F.max_micros
        max_micros = np.where(is_f, f_micros, E.max_micros)
        if guard.internal_daily_stop is not None:
            istop = guard.internal_daily_stop
        elif guard.daily_stop_r is not None:
            if sizing.mode == "fixed":
                base = np.full(P, sizing.risk_dollars)
                if sizing.funded_risk_dollars is not None:
                    base = np.where(is_f, sizing.funded_risk_dollars, base)
                if sizing.up_frac > 0:
                    base = np.where(is_f, np.minimum(base + sizing.up_frac * np.maximum(p - mll - maxloss, 0.0),
                                                     sizing.up_max_risk), base)
            else:
                base = sizing.max_risk
            istop = guard.daily_stop_r * base
        else:
            istop = INF

        day_pnl = np.zeros(P)
        stopped = ~active
        failed = np.zeros(P, dtype=bool)
        consec = np.zeros(P, dtype=int)
        if hasattr(model, "n_trades"):
            n_tr = model.n_trades(rng, P)
        else:
            n_tr = np.minimum(rng.poisson(model.trades_per_day, P), model.max_trades_per_day)
        traded = active & (n_tr > 0)
        for k in range(model.max_trades_per_day):
            act = ~stopped & (k < n_tr)
            if not act.any():
                break
            eq = p + day_pnl
            buffer = eq - mll
            if sizing.mode == "fixed":
                risk = np.full(P, sizing.risk_dollars)
                if sizing.funded_risk_dollars is not None:
                    risk = np.where(is_f, sizing.funded_risk_dollars, risk)
                if sizing.up_frac > 0:
                    extra = sizing.up_frac * np.maximum(buffer - maxloss, 0.0)
                    risk = np.where(is_f, np.minimum(risk + extra, sizing.up_max_risk), risk)
            else:
                risk = np.clip(sizing.fraction * buffer, sizing.min_risk, sizing.max_risk)
                risk = np.where(buffer < 0.5 * maxloss, risk * 0.5, risk)
            risk = np.minimum(risk, 0.8 * (dll + day_pnl))
            risk = np.minimum(risk, istop + day_pnl)
            r, mae, mfe, stop = model.sample(rng, P)
            per = stop + cost
            n = np.floor(risk / per)
            n = np.where((n == 0) & (per <= sizing.round_up_tolerance * risk), 1, n)
            n = np.minimum(n, max_micros)
            act &= n > 0
            pnl = n * (r * stop - cost)
            mae_d = n * mae * stop + n * cost
            mfe_d = n * mfe * stop
            loser = r < 0
            trail_ok = intraday & ~static
            # losers: favourable excursion happens before the adverse one
            pre = np.where(act & trail_ok & loser, np.maximum(mll, np.minimum(eq + mfe_d - maxloss, lock)), mll)
            breach = act & (eq - mae_d <= pre)
            dll_hit = act & ~breach & (day_pnl - mae_d <= -dll)
            real = np.where(breach, pre - eq, pnl)
            real = np.where(dll_hit, -dll - day_pnl, real)   # liquidated at the DLL
            day_pnl = np.where(act, day_pnl + real, day_pnl)
            post_peak = eq + np.maximum(mfe_d, real)
            mll = np.where(act & trail_ok & ~loser & ~breach, np.maximum(pre, np.minimum(post_peak - maxloss, lock)), pre)
            failed |= breach | (dll_hit & dll_fail)
            consec = np.where(act, np.where(real < 0, consec + 1, 0), consec)
            stopped |= breach | dll_hit
            stopped |= act & ((day_pnl <= -istop) | (day_pnl >= cap) | (consec >= guard.max_consecutive_losses))

        # ---- end of day
        p = np.where(active, p + day_pnl, p)
        tdays += traded
        dphase += active
        best_day = np.where(active, np.maximum(best_day, day_pnl), best_day)
        hwm = np.maximum(hwm, p)
        eod = active & ~intraday & ~static
        mll = np.where(eod, np.maximum(mll, np.minimum(hwm - maxloss, lock)), mll)
        if traded.any():
            day_pnls_eval.append(day_pnl[traded & (phase == 0)])
            day_pnls_fund.append(day_pnl[traded & (phase == 1)])

        ev = (phase == 0) & active
        cons_ok = np.ones(P, dtype=bool) if E.consistency_pct is None else best_day <= E.consistency_pct * p
        passed = ev & ~failed & (p >= (E.profit_target or INF)) & cons_ok & (tdays >= E.min_trading_days)
        failed_eval = ev & failed
        fu = (phase == 1) & active
        funded_days += fu
        failed_fund = fu & failed

        # ---- payouts
        win_days += fu & ~failed & (day_pnl >= F.winning_day_threshold)
        prof_since = np.where(fu, prof_since + day_pnl, prof_since)
        best_since = np.where(fu, np.maximum(best_since, day_pnl), best_since)
        avail = np.maximum(p - F.payout_reserve, 0.0)
        amount = F.payout_fraction * avail
        if F.payout_cap is not None:
            amount = np.minimum(amount, F.payout_cap)
        pc_ok = np.ones(P, dtype=bool) if F.payout_consistency_pct is None else \
            (best_since <= F.payout_consistency_pct * np.maximum(prof_since, 1e-9))
        amount = amount * payout_policy.request_fraction
        elig = fu & ~failed & (win_days >= F.payout_winning_days) & (amount >= max(F.payout_min, 1e-9)) & pc_ok
        elig &= p >= payout_policy.min_profit_to_request
        if elig.any():
            remaining_full = np.maximum(F.full_split_first - paid_gross, 0.0)
            at_full = np.minimum(amount, remaining_full)
            net = at_full + (amount - at_full) * F.profit_split
            paid_net += np.where(elig, net, 0.0)
            paid_gross += np.where(elig, amount, 0.0)
            p = np.where(elig, p - amount, p)
            n_payouts += elig
            first_payout_day = np.where(elig & (first_payout_day < 0), d, first_payout_day)
            win_days = np.where(elig, 0, win_days)
            prof_since = np.where(elig, 0.0, prof_since)
            best_since = np.where(elig, 0.0, best_since)
            if F.mll_after_payout == "lock_at_start":
                mll = np.where(elig, np.maximum(mll, 0.0), mll)

        # ---- transitions
        first_pass_day = np.where(passed & (first_pass_day < 0), d, first_pass_day)
        passes += passed
        eval_fails += failed_eval
        funded_blown += failed_fund
        if single_attempt:
            outcome = np.where(passed, 1, np.where(failed_eval, -1, outcome))
            phase = np.where(passed | failed_eval, 2, phase)
        else:
            to_f = passed
            to_e = failed_eval | failed_fund
            fees += np.where(to_f, program.activation_fee, 0.0) + np.where(to_e, program.eval_fee, 0.0)
            evals += to_e
            reset = to_f | to_e
            phase = np.where(to_f, 1, np.where(to_e, 0, phase))
            newmax = np.where(to_f, F.max_loss, E.max_loss)
            p = np.where(reset, 0.0, p)
            mll = np.where(reset, -newmax, mll)
            hwm = np.where(reset, 0.0, hwm)
            best_day = np.where(reset, 0.0, best_day)
            tdays = np.where(reset, 0, tdays)
            dphase = np.where(reset, 0, dphase)
            win_days = np.where(reset, 0, win_days)
            prof_since = np.where(reset, 0.0, prof_since)
            best_since = np.where(reset, 0.0, best_since)
        if cash_path is not None:
            cash_path[d] = paid_net - fees

    net = (paid_net - fees) * n_accounts
    q = lambda x, a: float(np.quantile(x, a))
    res = {
        "program": program.key,
        "model": model.summary(),
        "sizing": asdict(sizing),
        "guard": asdict(guard),
        "payout_policy": asdict(payout_policy),
        "horizon_days": horizon_days,
        "n_paths": n_paths,
        "n_accounts": n_accounts,
    }
    if single_attempt:
        res.update({
            "p_pass": float((outcome == 1).mean()),
            "p_fail": float((outcome == -1).mean()),
            "p_unresolved": float((outcome == 0).mean()),
            "median_days_to_pass": float(np.median(first_pass_day[outcome == 1])) if (outcome == 1).any() else None,
            "mean_fees_per_attempt": float(fees.mean()),
        })
        return res
    fd = np.concatenate(day_pnls_fund) if day_pnls_fund else np.array([])
    res.update({
        "net_mean": float(net.mean()),
        "net_median": q(net, 0.5),
        "net_p05": q(net, 0.05), "net_p25": q(net, 0.25), "net_p75": q(net, 0.75), "net_p95": q(net, 0.95),
        "p_net_positive": float((net > 0).mean()),
        "payouts_mean": float(paid_net.mean() * n_accounts),
        "fees_mean": float(fees.mean() * n_accounts),
        "p_any_payout": float((n_payouts > 0).mean()),
        "payouts_count_mean": float(n_payouts.mean()),
        "evals_bought_mean": float(evals.mean()),
        "passes_mean": float(passes.mean()),
        "pass_rate_per_attempt": float(passes.sum() / max(passes.sum() + eval_fails.sum(), 1)),
        "funded_blowups_mean": float(funded_blown.mean()),
        "median_day_first_payout": float(np.median(first_payout_day[first_payout_day >= 0])) if (first_payout_day >= 0).any() else None,
        "funded_day_share": float(funded_days.mean() / horizon_days),
        "funded_day_pnl_mean": float(fd.mean()) if len(fd) else None,
        "net_per_trading_day_mean": float(net.mean() / horizon_days),
    })
    if return_cash_path:
        res["_cash_path"] = cash_path
    if record_paths:
        pct = np.quantile(cash_path * n_accounts, [0.05, 0.25, 0.5, 0.75, 0.95], axis=1)
        res["cash_fan"] = [{"day": int(i), "p05": float(pct[0, i]), "p25": float(pct[1, i]), "p50": float(pct[2, i]),
                            "p75": float(pct[3, i]), "p95": float(pct[4, i])} for i in range(0, horizon_days, 3)]
    return res


def risk_sweep(program: PropProgram, model, risks: list[float], **kw) -> list[dict]:
    """Expected net cash vs risk per trade — the sizing decision for a prop account."""
    out = []
    for r in risks:
        res = simulate_lifecycle(program, model, SimSizing(mode="fixed", risk_dollars=r), record_paths=False, **kw)
        out.append({"risk_dollars": r, **{k: res[k] for k in (
            "net_mean", "net_median", "net_p05", "net_p95", "p_net_positive", "p_any_payout",
            "pass_rate_per_attempt", "evals_bought_mean", "fees_mean", "payouts_mean")}})
    return out
