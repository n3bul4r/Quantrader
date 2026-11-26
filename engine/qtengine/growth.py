"""Own-capital growth planner: start balance + monthly contributions, traded with a given
edge, vehicle and sizing policy — versus simply investing the same money in an index ETF.

Why a dedicated simulator: with small accounts the binding constraints are *granularity*
(one MES contract risks ~$110 on a typical S1 stop, i.e. ~19 % of a €500 account) and
*costs*, not the edge. Both are modelled explicitly here.

All money is simulated in USD internally and reported in EUR at a fixed EURUSD rate
(no FX risk modelled). Contributions arrive at the start of every 21-trading-day month.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, replace

import numpy as np

from .prop.simulator import PRESET_MODELS, TradeModel

TRADING_DAYS = 252
MONTH = 21


@dataclass(frozen=True)
class Vehicle:
    """How a trade is expressed. `unit_pv` = $ per index point of the smallest position step."""
    key: str
    name: str
    unit_pv: float            # $ per point per unit (MES 5.0; CFD in $0.10/pt steps -> 0.10)
    cost_per_unit_rt: float   # all-in $ per unit per round turn (fees/spread + slippage)
    margin_per_unit: float    # $ intraday margin per unit
    max_units: int = 10_000
    note: str = ""


VEHICLES: dict[str, Vehicle] = {
    # Retail futures broker (no prop): ~$1.9 commission+exchange+NFA + 2 ticks slippage; $50 day margin
    "MES": Vehicle("MES", "MES micro futures (retail broker)", 5.0, 4.40, 50.0,
                   note="CME regulated, central clearing; 1 contract = $5/pt, so ~$110 risk per S1 trade"),
    # Index CFD on the S&P 500, sized in $0.10/point steps; 0.6 pt spread + 0.25 pt slippage; ESMA 5 % margin
    "CFD_US500": Vehicle("CFD_US500", "US500 index CFD (EU broker, $0.10/pt steps)", 0.10, 0.085, 34.0,
                         note="OTC, broker is counterparty; ESMA 1:20 leverage, negative-balance protection; "
                              "74-89 % of retail CFD accounts lose money"),
}


@dataclass
class GrowthPolicy:
    risk_fraction: float = 0.01          # risk per trade as a fraction of current equity
    daily_stop_r: float = 2.0            # stop for the day after losing this many R
    min_unit_max_fraction: float = 0.0125  # take 1 unit if its risk <= this fraction of equity, else skip
    max_margin_use: float = 0.5          # never use more than 50 % of equity as margin
    start_trading_at_eur: float = 0.0    # save only (no trading) until equity reaches this


@dataclass
class GrowthScenario:
    key: str
    label: str
    kind: str = "trading"                # trading | etf | cash
    model: str | None = "S1_planning"    # PRESET_MODELS key (trading)
    vehicle: str = "CFD_US500"
    policy: GrowthPolicy = field(default_factory=GrowthPolicy)
    etf_return: float = 0.07             # annual expected (arithmetic) return, etf kind
    etf_vol: float = 0.15
    trades_per_day: float | None = None  # override model frequency (e.g. 1.4 for MES+MNQ)


def simulate_growth(
    scenario: GrowthScenario,
    start_eur: float = 500.0,
    monthly_eur: float = 100.0,
    years: int = 10,
    n_paths: int = 5000,
    eurusd: float = 1.16,
    seed: int = 0,
    checkpoints: tuple[int, ...] = (1, 3, 5, 10),
    tax_rate: float = 0.0,
) -> dict:
    """tax_rate: flat tax on net realised gains. Trading is taxed every year (all gains are
    realised; losses carried forward). The ETF is an accumulating fund taxed once, on the
    gain, at the checkpoint (as if sold then)."""
    rng = np.random.default_rng(seed)
    H = years * TRADING_DAYS
    P = n_paths
    usd = lambda e: e * eurusd
    eq = np.full(P, usd(start_eur))
    contributed = np.full(P, usd(start_eur))
    peak = eq.copy()
    max_dd = np.zeros(P)
    traded_days = np.zeros(P)
    halted_ever = np.zeros(P, dtype=bool)   # equity fell below 50 % of contributions at some point
    year_start = eq.copy()
    year_contrib = np.zeros(P)
    carry = np.zeros(P)                     # tax loss carry-forward (<= 0)
    taxes_paid = np.zeros(P)
    snaps: dict[int, dict] = {}
    monthly_pct = []

    if scenario.kind == "trading":
        model: TradeModel = PRESET_MODELS[scenario.model]
        if scenario.trades_per_day is not None:
            model = replace(model, trades_per_day=scenario.trades_per_day,
                            max_trades_per_day=max(model.max_trades_per_day, math.ceil(scenario.trades_per_day) + 2))
        veh = VEHICLES[scenario.vehicle]
        pol = scenario.policy
        start_trading = usd(pol.start_trading_at_eur)
    elif scenario.kind == "etf":
        mu_d = math.log(1 + scenario.etf_return) / TRADING_DAYS
        sd_d = scenario.etf_vol / math.sqrt(TRADING_DAYS)

    for d in range(H):
        if scenario.kind == "etf":
            eq *= np.exp(rng.normal(mu_d - 0.5 * sd_d ** 2, sd_d, P))
        elif scenario.kind == "trading":
            n_tr = np.minimum(rng.poisson(model.trades_per_day, P), model.max_trades_per_day)
            day_pnl = np.zeros(P)
            budget = pol.risk_fraction * eq
            stopped = eq < start_trading
            any_trade = np.zeros(P, dtype=bool)
            for k in range(model.max_trades_per_day):
                act = ~stopped & (k < n_tr)
                if not act.any():
                    break
                r, _, _, stop_d = model.sample(rng, P)
                stop_pts = stop_d / 5.0                      # model stops are defined on MES ($5/pt)
                per_unit = stop_pts * veh.unit_pv + veh.cost_per_unit_rt
                units = np.floor(budget / per_unit)
                units = np.where((units == 0) & (per_unit <= pol.min_unit_max_fraction * eq), 1, units)
                units = np.minimum(units, np.floor(pol.max_margin_use * np.maximum(eq, 0) / veh.margin_per_unit))
                units = np.minimum(units, veh.max_units)
                act &= units > 0
                pnl = units * (r * stop_pts * veh.unit_pv - veh.cost_per_unit_rt)
                day_pnl = np.where(act, day_pnl + pnl, day_pnl)
                any_trade |= act
                stopped |= act & (day_pnl <= -pol.daily_stop_r * budget)
            eq = np.maximum(eq + day_pnl, 0.0)
            traded_days += any_trade
        if (d + 1) % MONTH == 0:            # end-of-month contribution
            eq += usd(monthly_eur)
            contributed += usd(monthly_eur)
            year_contrib += usd(monthly_eur)
        if tax_rate and scenario.kind == "trading" and (d + 1) % TRADING_DAYS == 0:
            base = carry + (eq - year_start - year_contrib)
            tax = np.where(base > 0, tax_rate * base, 0.0)
            eq -= tax
            taxes_paid += tax
            carry = np.minimum(base, 0.0)
            year_start = eq.copy()
            year_contrib[:] = 0.0
        peak = np.maximum(peak, eq)
        max_dd = np.maximum(max_dd, 1 - eq / np.maximum(peak, 1e-9))
        halted_ever |= eq < 0.5 * contributed
        if (d + 1) % MONTH == 0:
            monthly_pct.append(np.quantile(eq, [0.05, 0.25, 0.5, 0.75, 0.95]) / eurusd)
        y = (d + 1) / TRADING_DAYS
        if y in checkpoints:
            e = eq / eurusd
            c = contributed[0] / eurusd
            if tax_rate and scenario.kind == "etf":
                e = e - tax_rate * np.maximum(e - c, 0.0)
            snaps[int(y)] = {
                "years": int(y), "contributed_eur": float(c),
                "mean": float(e.mean()), "p05": float(np.quantile(e, 0.05)), "p25": float(np.quantile(e, 0.25)),
                "median": float(np.median(e)), "p75": float(np.quantile(e, 0.75)), "p95": float(np.quantile(e, 0.95)),
                "p_below_contributed": float((e < c).mean()),
                "p_double_contributed": float((e >= 2 * c).mean()),
                "median_gain_eur": float(np.median(e) - c),
                "median_max_drawdown": float(np.median(max_dd)),
                "p_halved_vs_contributions": float(halted_ever.mean()),
                "share_of_days_traded": float(traded_days.mean() / (d + 1)) if scenario.kind == "trading" else None,
                "taxes_paid_mean": float(taxes_paid.mean() / eurusd),
            }
    out = {"scenario": {**asdict(scenario), "policy": asdict(scenario.policy)}, "start_eur": start_eur, "tax_rate": tax_rate,
           "monthly_eur": monthly_eur, "eurusd": eurusd, "n_paths": n_paths, "checkpoints": [snaps[k] for k in sorted(snaps)],
           "fan": [{"day": (i + 1) * MONTH, "month": i + 1, "p05": float(q[0]), "p25": float(q[1]), "p50": float(q[2]),
                    "p75": float(q[3]), "p95": float(q[4])} for i, q in enumerate(monthly_pct)]}
    if scenario.kind == "trading":
        out["model"] = PRESET_MODELS[scenario.model].summary()
        out["vehicle"] = asdict(VEHICLES[scenario.vehicle])
    return out


def future_value(start: float, monthly: float, annual_return: float, years: int) -> float:
    """Deterministic value with monthly compounding and end-of-month contributions."""
    r = (1 + annual_return) ** (1 / 12) - 1
    n = 12 * years
    if r == 0:
        return start + monthly * n
    return start * (1 + r) ** n + monthly * ((1 + r) ** n - 1) / r


def months_to_target(start: float, monthly: float, annual_return: float, target: float, max_years: int = 100) -> float | None:
    r = (1 + annual_return) ** (1 / 12) - 1
    v = start
    for m in range(1, 12 * max_years + 1):
        v = v * (1 + r) + monthly
        if v >= target:
            return m
    return None


SCENARIOS: dict[str, GrowthScenario] = {
    "etf": GrowthScenario("etf", "Index ETF (MSCI World-like, 7 %/yr, 15 % vol)", kind="etf", model=None),
    "cash": GrowthScenario("cash", "Contributions only (0 %)", kind="cash", model=None),
    "no_edge_cfd_1pct": GrowthScenario("no_edge_cfd_1pct", "Day trading with NO edge (costs only), CFD, 1 % risk",
                                       model="zero_edge"),
    "s1_plan_cfd_1pct": GrowthScenario("s1_plan_cfd_1pct", "S1 planning edge, CFD, 1 % risk/trade", model="S1_planning"),
    "s1_plan_cfd_2pct": GrowthScenario("s1_plan_cfd_2pct", "S1 planning edge, CFD, 2 % risk/trade", model="S1_planning",
                                       policy=GrowthPolicy(risk_fraction=0.02, min_unit_max_fraction=0.025)),
    "s1_plan_mes_1pct": GrowthScenario("s1_plan_mes_1pct", "S1 planning edge, MES futures, 1 % risk (skips trades it can't size)",
                                       model="S1_planning", vehicle="MES"),
    "s1_plan_mes_1lot": GrowthScenario("s1_plan_mes_1lot", "S1 planning edge, always ≥1 MES from day one (over-leveraged)",
                                       model="S1_planning", vehicle="MES",
                                       policy=GrowthPolicy(risk_fraction=0.01, min_unit_max_fraction=1.0, daily_stop_r=1e9)),
    "no_edge_mes_1lot": GrowthScenario("no_edge_mes_1lot", "NO edge, always ≥1 MES from day one (over-leveraged)",
                                       model="zero_edge", vehicle="MES",
                                       policy=GrowthPolicy(risk_fraction=0.01, min_unit_max_fraction=1.0, daily_stop_r=1e9)),
    "s1_plan_cfd_2mkts_1pct": GrowthScenario("s1_plan_cfd_2mkts_1pct", "S1 planning edge on US500 + US100 CFDs, 1 % risk",
                                             model="S1_planning", trades_per_day=1.4),
    "s1_opt_cfd_1pct": GrowthScenario("s1_opt_cfd_1pct", "S1 optimistic edge, CFD, 1 % risk/trade", model="S1_optimistic"),
    "s1_opt_cfd_2pct": GrowthScenario("s1_opt_cfd_2pct", "S1 optimistic edge, CFD, 2 % risk/trade", model="S1_optimistic",
                                      policy=GrowthPolicy(risk_fraction=0.02, min_unit_max_fraction=0.025)),
}
