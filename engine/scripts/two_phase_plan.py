"""Two-phase plan: (1) prop fleet until $100k has been withdrawn, (2) trade that money as your own account.

    python scripts/two_phase_plan.py

Phase 1 uses the fleet simulator (5 × Topstep 150K, decorrelated, 35 % of max loss per trade).
Phase 2 trades own capital with the same edge at fractional-Kelly risk. Variants: stop the prop
fleet at $100k vs keep it running and keep feeding the own account. Also: what happens to the
own $100k if the edge is gone (zero edge). Writes docs/results/two_phase_plan.{md,json}.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from qtengine.prop import PRESET_MODELS, get_program
from qtengine.prop.fleet import MONTH, simulate_fleet
from qtengine.prop.simulator import PayoutPolicy, SimSizing

ROOT = Path(__file__).resolve().parents[2]
TARGET = 100_000
YEARS = 5
PATHS = 600


def own_account(start_month, monthly_cash, keep_feeding, model, risk_fraction, rng, max_contracts=500,
                point_value=5.0, cost=4.40, tax_on_payouts=0.0):
    """Simulate own account per path. Before the switch month: nothing. At the switch: transfer
    cumulative fleet cash (after tax). After: optionally keep adding fleet cash."""
    months, P = monthly_cash.shape
    eq = np.zeros(P)
    peak = np.zeros(P)
    max_dd = np.zeros(P)
    cum = np.cumsum(monthly_cash, axis=0)
    started = np.zeros(P, dtype=bool)
    wealth = np.zeros((months, P))
    banked = np.zeros(P)          # fleet cash not transferred (when prop keeps running but we don't feed)
    for m in range(months):
        switch = (~started) & (start_month == m)
        eq = np.where(switch, cum[m] * (1 - tax_on_payouts), eq)
        started |= switch
        if m > 0:
            flow = monthly_cash[m] * (1 - tax_on_payouts)
            after = started & ~switch
            if keep_feeding:
                eq = np.where(after, eq + flow, eq)
            else:
                banked += np.where(after, 0.0, 0.0)   # prop stopped after the switch
        # trade one month
        for _ in range(MONTH):
            n_tr = np.minimum(rng.poisson(model.trades_per_day, P), model.max_trades_per_day)
            budget = risk_fraction * eq * started
            day = np.zeros(P)
            stopped = np.zeros(P, dtype=bool)
            for k in range(model.max_trades_per_day):
                act = ~stopped & (k < n_tr) & started
                if not act.any():
                    break
                r, _, _, stop = model.sample(rng, P)
                per = stop + cost
                n = np.minimum(np.floor(budget / per), max_contracts)
                act &= n > 0
                day = np.where(act, day + n * (r * stop - cost), day)
                stopped |= act & (day <= -3 * budget)
            eq = np.maximum(eq + day, 0.0)
        peak = np.maximum(peak, eq)
        dd = np.where(peak > 0, 1 - eq / np.maximum(peak, 1e-9), 0.0)
        max_dd = np.where(started, np.maximum(max_dd, dd), max_dd)
        pre = np.where(started, 0.0, cum[m] * (1 - tax_on_payouts))   # still in phase 1: cash on hand
        wealth[m] = eq + pre
    return wealth, max_dd, started


def main():
    prog = get_program("topstep_150k")
    md = ["# Two-phase plan: prop until $100k withdrawn → trade it as your own account\n",
          f"Phase 1: 5 × Topstep 150K slots, decorrelated (ρ = 0.4), 35 % of max loss per trade ($1,575), cushion before payouts. "
          f"Phase 2: switch when cumulative net prop cash ≥ ${TARGET:,}; own account trades the same edge (MES-equivalent, ≤ 500 contracts/trade). "
          f"{PATHS} paths, {YEARS}-year horizon, pre-tax unless stated. Trade models are assumptions.\n"]
    js = {"runs": []}
    for mk in ("basket_planning", "basket_optimistic"):
        model = PRESET_MODELS[mk]
        f = simulate_fleet(prog, model, 5, 0.4, SimSizing(risk_dollars=1575), payout_policy=PayoutPolicy(min_profit_to_request=4500),
                           horizon_days=252 * YEARS, n_paths=PATHS, seed=21)
        mc = f["monthly_cash"]
        cum = np.cumsum(mc, axis=0)
        hit = cum >= TARGET
        reached = hit.any(axis=0)
        start_month = np.where(reached, hit.argmax(axis=0), 10 ** 6)
        md.append(f"\n## Edge: {mk}\n")
        md.append(f"**Phase 1:** P(reach ${TARGET:,} withdrawn within {YEARS} y) = {reached.mean():.0%}; "
                  f"months to get there: median {np.median(start_month[reached]):.0f}, "
                  f"25th–75th pct {np.quantile(start_month[reached], 0.25):.0f}–{np.quantile(start_month[reached], 0.75):.0f}.\n")
        md.append("| phase 2 variant | own risk/trade | wealth median 3y | median 5y | 5th pct 5y | P(own account ever −30 %) | P(−50 %) | median own-account return/yr after switch |")
        md.append("|---|---|---|---|---|---|---|---|")
        variants = [("stop prop at $100k", False), ("keep prop running, keep feeding", True)]
        for name, feed in variants:
            for rf in (0.005, 0.01, 0.02):
                rng = np.random.default_rng(5)
                w, dd, started = own_account(start_month, mc, feed, model, rf, rng)
                ok = started
                # annualised own-account growth for paths that switched and did not get fed (pure trading return)
                yrs_after = (w.shape[0] - 1 - np.minimum(start_month, w.shape[0] - 1)) / 12
                g = np.where(ok & (yrs_after > 0.5), (np.maximum(w[-1], 1) / TARGET) ** (1 / np.maximum(yrs_after, 1e-9)) - 1, np.nan)
                ret_txt = f"{np.nanmedian(g):.0%}" if not feed and np.isfinite(np.nanmedian(g)) else "n/a (fed)"
                row = {"model": mk, "variant": name, "risk": rf, "median_3y": float(np.median(w[35])), "median_5y": float(np.median(w[-1])),
                       "p05_5y": float(np.quantile(w[-1], 0.05)), "p_dd30": float((dd[ok] >= 0.3).mean()) if ok.any() else None,
                       "p_dd50": float((dd[ok] >= 0.5).mean()) if ok.any() else None}
                js["runs"].append(row)
                md.append(f"| {name} | {rf:.1%} | ${row['median_3y']:,.0f} | ${row['median_5y']:,.0f} | ${row['p05_5y']:,.0f} | "
                          f"{row['p_dd30']:.0%} | {row['p_dd50']:.0%} | {ret_txt} |")
        js[mk] = {"p_reach": float(reached.mean()), "median_months": float(np.median(start_month[reached]))}

    # what $100k of own money does on its own (no prop), including the no-edge case
    md.append("\n## Phase 2 alone: $100,000 of your own money, no further contributions\n")
    md.append("| edge | risk/trade | median after 1y | after 3y | 5th pct 3y | P(lose money over 3y) | P(drawdown ≥ 30 %) | median income if you withdraw gains yearly |")
    md.append("|---|---|---|---|---|---|---|---|")
    zero = replace(PRESET_MODELS["zero_edge"], name="zero_edge_basket", trades_per_day=2.4, max_trades_per_day=6)
    for model in (zero, PRESET_MODELS["basket_planning"], PRESET_MODELS["basket_optimistic"]):
        for rf in (0.005, 0.01):
            rng = np.random.default_rng(9)
            P, months = 2000, 36
            mc = np.zeros((months, P))
            mc[0] = TARGET
            w, dd, _ = own_account(np.zeros(P, dtype=int), mc, False, model, rf, rng)
            # income: withdraw everything above $100k each year end (median yearly withdrawal)
            yearly = [np.maximum(w[11], TARGET) - TARGET]
            md.append(f"| {model.name} | {rf:.1%} | ${np.median(w[11]):,.0f} | ${np.median(w[35]):,.0f} | ${np.quantile(w[35], 0.05):,.0f} | "
                      f"{(w[35] < TARGET).mean():.0%} | {(dd >= 0.3).mean():.0%} | ${np.median(yearly[0]) / 252:,.0f}/trading day (year 1) |")
    out = ROOT / "docs" / "results"
    (out / "two_phase_plan.md").write_text("\n".join(md) + "\n")
    (out / "two_phase_plan.json").write_text(json.dumps(js, indent=1, default=float))
    print("\n".join(md))


if __name__ == "__main__":
    main()
