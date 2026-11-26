"""Fleet + flywheel: many Topstep accounts at once, and payouts recycled into an own account.

Fleet
    `n_slots` concurrent account lifecycles (each slot: buy Combine → pass → XFA → payouts →
    blow-up → buy again). Trade outcomes across slots are correlated with coefficient `rho`
    (copy-trading the same signals = 1.0; different markets/strategies per slot < 1).
Flywheel
    Every month the fleet's net cash (payouts − fees) is transferred into a personal
    futures account that trades the same edge with fractional-Kelly sizing and no payout caps.
    This is the only route in this repo whose growth is not capped by the firm.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from .rules import PropProgram
from .simulator import PayoutPolicy, SimGuard, SimSizing, TradeModel, simulate_lifecycle

MONTH = 21
MILESTONES = (10_000, 50_000, 100_000, 250_000, 1_000_000)


@dataclass
class CorrelatedModel:
    """Wraps a trade model so that `n_slots` blocks of `n_paths` share outcomes with
    pairwise correlation ≈ rho (each draw is the shared draw with probability sqrt(rho))."""
    base: TradeModel
    n_slots: int
    n_paths: int
    rho: float

    @property
    def trades_per_day(self):
        return self.base.trades_per_day

    @property
    def max_trades_per_day(self):
        return self.base.max_trades_per_day

    @property
    def cost_per_contract(self):
        return self.base.cost_per_contract

    def _mix(self, rng, common, idio):
        use = rng.random(idio.shape[0]) < math.sqrt(self.rho)
        return np.where(use, np.tile(common, self.n_slots), idio)

    def sample(self, rng, n):
        c = self.base.sample(rng, self.n_paths)
        i = self.base.sample(rng, n)
        return tuple(self._mix(rng, a, b) for a, b in zip(c, i))

    def n_trades(self, rng, n):
        lam, mx = self.base.trades_per_day, self.base.max_trades_per_day
        c = np.minimum(rng.poisson(lam, self.n_paths), mx)
        i = np.minimum(rng.poisson(lam, n), mx)
        return self._mix(rng, c, i)

    def summary(self):
        return {**self.base.summary(), "rho": self.rho, "n_slots": self.n_slots}


def _milestones(cash: np.ndarray) -> dict:
    """cash: [H, P] cumulative net cash. Probability and median day of first reaching each milestone."""
    H, P = cash.shape
    out = {}
    for m in MILESTONES:
        hit = cash >= m
        reached = hit.any(axis=0)
        first = np.where(reached, hit.argmax(axis=0), -1)
        out[str(m)] = {"p_reach": float(reached.mean()),
                       "median_months": float(np.median(first[reached]) / MONTH) if reached.any() else None}
    return out


def simulate_fleet(program: PropProgram, model: TradeModel, n_slots: int = 5, rho: float = 1.0,
                   sizing: SimSizing | None = None, guard: SimGuard | None = None,
                   payout_policy: PayoutPolicy | None = None, horizon_days: int = 756, n_paths: int = 1000,
                   seed: int = 0) -> dict:
    cm = CorrelatedModel(model, n_slots, n_paths, rho)
    res = simulate_lifecycle(program, cm, sizing, guard, horizon_days=horizon_days, n_paths=n_slots * n_paths,
                             seed=seed, record_paths=False, payout_policy=payout_policy, return_cash_path=True)
    cash = res.pop("_cash_path").reshape(horizon_days, n_slots, n_paths).sum(axis=1)   # [H, P]
    years = [y for y in (1, 2, 3, 5) if y * 252 <= horizon_days]
    by_year = {}
    for y in years:
        x = cash[y * 252 - 1]
        by_year[y] = {"mean": float(x.mean()), "median": float(np.median(x)), "p05": float(np.quantile(x, 0.05)),
                      "p95": float(np.quantile(x, 0.95)), "p_positive": float((x > 0).mean())}
    monthly = np.diff(np.concatenate([np.zeros((1, n_paths)), cash[MONTH - 1::MONTH]]), axis=0)   # [months, P]
    return {"program": program.key, "n_slots": n_slots, "rho": rho, "model": model.summary(),
            "by_year": by_year, "milestones": _milestones(cash), "monthly_cash": monthly,
            "evals_bought_per_slot": res["evals_bought_mean"], "pass_rate_per_attempt": res["pass_rate_per_attempt"],
            "p_any_payout_per_slot": res["p_any_payout"]}


def simulate_flywheel(monthly_cash: np.ndarray, model: TradeModel, risk_fraction: float = 0.02,
                      point_value: float = 5.0, cost_per_contract: float = 4.40, seed: int = 1,
                      daily_stop_r: float = 3.0, max_contracts: int = 500) -> dict:
    """monthly_cash [months, P]: cash transferred in (+) or fees paid from the account (−).
    Own account trades `model` sized at `risk_fraction` of equity per trade (MES contracts), capped at
    `max_contracts` per trade so that compounding cannot assume unlimited market capacity."""
    rng = np.random.default_rng(seed)
    months, P = monthly_cash.shape
    eq = np.zeros(P)
    out_of_pocket = np.zeros(P)
    wealth = np.zeros((months, P))
    for m in range(months):
        for _ in range(MONTH):
            n_tr = np.minimum(rng.poisson(model.trades_per_day, P), model.max_trades_per_day)
            budget = risk_fraction * eq
            day = np.zeros(P)
            stopped = np.zeros(P, dtype=bool)
            for k in range(model.max_trades_per_day):
                act = ~stopped & (k < n_tr)
                if not act.any():
                    break
                r, _, _, stop = model.sample(rng, P)
                per = stop / 5.0 * point_value + cost_per_contract
                n = np.minimum(np.floor(budget / per), max_contracts)   # capacity: ≤ 500 MES ≈ 50 ES per trade
                act &= n > 0
                day = np.where(act, day + n * (r * stop / 5.0 * point_value - cost_per_contract), day)
                stopped |= act & (day <= -daily_stop_r * budget)
            eq = np.maximum(eq + day, 0.0)
        flow = monthly_cash[m]
        eq = eq + np.maximum(flow, 0.0)
        pay = np.minimum(eq, np.maximum(-flow, 0.0))       # fees paid from the account if possible
        eq -= pay
        out_of_pocket += np.maximum(-flow, 0.0) - pay
        wealth[m] = eq - out_of_pocket
    cash_like = np.repeat(wealth, MONTH, axis=0)
    years = [y for y in (1, 2, 3, 5) if y * 12 <= months]
    return {"risk_fraction": risk_fraction,
            "by_year": {y: {"median": float(np.median(wealth[y * 12 - 1])), "mean": float(wealth[y * 12 - 1].mean()),
                            "p05": float(np.quantile(wealth[y * 12 - 1], 0.05)), "p95": float(np.quantile(wealth[y * 12 - 1], 0.95))}
                        for y in years},
            "milestones": _milestones(cash_like)}


def kelly_years_to_multiple(sharpe: float, multiple: float, kelly_fraction: float = 1.0) -> float:
    """Continuous-time growth law: at fraction c of the Kelly leverage the log-growth rate is
    g = c(2 − c)/2 · SR². Years to multiply wealth by `multiple` = ln(multiple) / g."""
    g = kelly_fraction * (2 - kelly_fraction) / 2 * sharpe ** 2
    return math.log(multiple) / g if g > 0 else float("inf")


def theoretical_payout_ceiling(payout_cap: float, min_days_per_cycle: int, n_accounts: int, split: float = 0.9,
                               trading_days: int = 252) -> float:
    """Upper bound on annual XFA extraction if every cycle hits the cap in the minimum days."""
    return payout_cap * split * (trading_days / min_days_per_cycle) * n_accounts
