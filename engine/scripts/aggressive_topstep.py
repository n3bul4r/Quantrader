"""Aggressive Topstep optimisation: maximise net cash speed under Topstep's 2026 rules.

    python scripts/aggressive_topstep.py [--paths 1500]

A. Single-slot optimiser: account type × evaluation risk × funded policy × edge model (2 years)
B. Fleet: best config, 1/3/5 slots, copy-traded (ρ=1) vs diversified (ρ=0.4), 3 years, milestones
C. Flywheel: fleet payouts recycled into an own MES account at 1/2/4 % risk, 3 years
D. Growth law and payout ceilings (analytic)
Writes docs/results/aggressive_topstep.{md,json}.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from qtengine.prop import PRESET_MODELS, get_program
from qtengine.prop.fleet import kelly_years_to_multiple, simulate_fleet, simulate_flywheel, theoretical_payout_ceiling
from qtengine.prop.simulator import PayoutPolicy, SimSizing, simulate_lifecycle

ROOT = Path(__file__).resolve().parents[2]
PROGRAMS = ["topstep_50k", "topstep_100k", "topstep_150k", "topstep_50k_consistency", "topstep_150k_consistency"]
MODELS = ["S1_planning", "basket_planning", "basket_optimistic"]
RISK_FRACS = [0.15, 0.25, 0.35, 0.50]
EURUSD = 1.16


def policies(prog, risk):
    ml = prog.evaluation.max_loss
    return {
        "same risk funded": (SimSizing(risk_dollars=risk), PayoutPolicy()),
        "half risk funded + scale-up 25 %": (SimSizing(risk_dollars=risk, funded_risk_dollars=0.5 * risk, up_frac=0.25,
                                                       up_max_risk=1.5 * risk), PayoutPolicy()),
        "same risk, cushion before payouts": (SimSizing(risk_dollars=risk), PayoutPolicy(min_profit_to_request=ml)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=1500)
    a = ap.parse_args()
    md, js = ["# Aggressive Topstep optimisation\n"], {"single": [], "fleet": [], "flywheel": []}
    md.append(f"Monte Carlo, {a.paths:,} paths per cell. Trade models are assumptions (see AGGRESSIVE_SYSTEM.md §1). "
              "Rules: Topstep 2026 presets (partly secondary sources). Net = trader share of payouts − every fee.\n")

    # ---------------- A
    md.append("## A. Single account slot, 2 years — best configuration per account type and edge\n")
    md.append("| edge model | account | eval risk $/trade (% of MLL) | funded policy | net mean 2y | net median 2y | P(net>0) | pass rate | evals bought |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    best_by_model = {}
    for mk in MODELS:
        model = PRESET_MODELS[mk]
        cells = []
        for pk in PROGRAMS:
            prog = get_program(pk)
            for f in RISK_FRACS:
                risk = round(f * prog.evaluation.max_loss)
                for pol_name, (sz, pp) in policies(prog, risk).items():
                    r = simulate_lifecycle(prog, model, sz, horizon_days=504, n_paths=a.paths, record_paths=False,
                                           payout_policy=pp, seed=5)
                    cells.append({"model": mk, "program": pk, "risk": risk, "risk_frac": f, "policy": pol_name,
                                  **{k: r[k] for k in ("net_mean", "net_median", "net_p05", "net_p95", "p_net_positive",
                                                       "pass_rate_per_attempt", "evals_bought_mean")}})
            print(mk, pk, "done", flush=True)
        js["single"] += cells
        for pk in PROGRAMS:
            sub = [c for c in cells if c["program"] == pk]
            b = max(sub, key=lambda c: c["net_mean"])
            md.append(f"| {mk} | {pk} | {b['risk']} ({b['risk_frac']:.0%}) | {b['policy']} | {b['net_mean']:,.0f} | "
                      f"{b['net_median']:,.0f} | {b['p_net_positive']:.0%} | {b['pass_rate_per_attempt']:.0%} | {b['evals_bought_mean']:.1f} |")
        best_by_model[mk] = max(cells, key=lambda c: c["net_mean"])

    md.append("\n### Policy comparison (basket_planning, topstep_150k, risk 25 % of MLL)\n")
    md.append("| funded policy | net mean 2y | net median 2y | P(net>0) |\n|---|---|---|---|")
    for c in js["single"]:
        if c["model"] == "basket_planning" and c["program"] == "topstep_150k" and c["risk_frac"] == 0.25:
            md.append(f"| {c['policy']} | {c['net_mean']:,.0f} | {c['net_median']:,.0f} | {c['p_net_positive']:.0%} |")

    # ---------------- B
    md.append("\n## B. Fleet: several account slots at once, 3 years\n")
    md.append("Each slot re-buys a Combine whenever its account is lost. ρ = correlation of trade outcomes between slots "
              "(1.0 = copy-trading the same signals; 0.4 = different markets/strategies per slot).\n")
    md.append("| edge model | account | slots | ρ | net mean 1y | median 1y | mean 3y | median 3y | p05 3y | P(≥$100k by 3y) | median months to $100k | P(≥$1M by 3y) |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    fleet_for_flywheel = None
    for mk in ("basket_planning", "basket_optimistic"):
        b = best_by_model[mk]
        prog = get_program(b["program"])
        sz, pp = policies(prog, b["risk"])[b["policy"]]
        for slots, rho in ((1, 1.0), (3, 1.0), (5, 1.0), (5, 0.4)):
            f = simulate_fleet(prog, PRESET_MODELS[mk], slots, rho, sz, payout_policy=pp, horizon_days=756,
                               n_paths=max(400, a.paths // 3), seed=9)
            y1, y3 = f["by_year"][1], f["by_year"][3]
            m100, m1m = f["milestones"]["100000"], f["milestones"]["1000000"]
            js["fleet"].append({"model": mk, "program": b["program"], "slots": slots, "rho": rho,
                                "by_year": f["by_year"], "milestones": f["milestones"]})
            months_100k = "—" if m100["median_months"] is None else f"{m100['median_months']:.0f}"
            md.append(f"| {mk} | {b['program']} | {slots} | {rho} | {y1['mean']:,.0f} | {y1['median']:,.0f} | {y3['mean']:,.0f} | "
                      f"{y3['median']:,.0f} | {y3['p05']:,.0f} | {m100['p_reach']:.0%} | {months_100k} | {m1m['p_reach']:.0%} |")
            if slots == 5 and rho == 0.4:
                if fleet_for_flywheel is None:
                    fleet_for_flywheel = {}
                fleet_for_flywheel[mk] = f
            print("fleet", mk, slots, rho, flush=True)

    # ---------------- C
    md.append("\n## C. Flywheel: 5 diversified slots, payouts recycled into an own MES account, 3 years\n")
    md.append("Own account trades the same edge (sized as % of its equity per trade, no payout caps, capped at 500 MES ≈ 50 ES "
              "per trade for market capacity; its trades are simulated independently of the prop accounts, which flatters "
              "diversification). Fees are paid from the account when possible, otherwise out of pocket. "
              "Wealth = own account − out-of-pocket fees. Full Kelly for the per-trade edge is ≈ 2.5 % (planning); 4 % is over-betting.\n")
    md.append("| edge model | own-account risk/trade | wealth median 1y | median 3y | mean 3y | p05 3y | p95 3y | P(≥$100k) | P(≥$1M) |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    for mk, f in (fleet_for_flywheel or {}).items():
        for rf in (0.01, 0.02, 0.04):
            w = simulate_flywheel(f["monthly_cash"], PRESET_MODELS[mk], risk_fraction=rf)
            js["flywheel"].append({"model": mk, "risk_fraction": rf, **w})
            b1, b3 = w["by_year"][1], w["by_year"][3]
            md.append(f"| {mk} | {rf:.0%} | {b1['median']:,.0f} | {b3['median']:,.0f} | {b3['mean']:,.0f} | {b3['p05']:,.0f} | "
                      f"{b3['p95']:,.0f} | {w['milestones']['100000']['p_reach']:.0%} | {w['milestones']['1000000']['p_reach']:.0%} |")

    # ---------------- D
    md.append("\n## D. The speed limit: growth law and payout ceilings\n")
    md.append("Years to multiply capital at Kelly leverage — growth rate g = c(2−c)/2 · Sharpe² (c = Kelly fraction):\n")
    md.append("| annual Sharpe | ×10 full Kelly | ×10 half Kelly | ×100 full | ×100 half | ×1000 full | ×1000 half |\n|---|---|---|---|---|---|---|")
    js["growth_law"] = []
    for sr in (0.5, 1.0, 1.5, 2.0, 3.0):
        row = [kelly_years_to_multiple(sr, m, c) for m in (10, 100, 1000) for c in (1.0, 0.5)]
        js["growth_law"].append({"sharpe": sr, "years": row})
        md.append(f"| {sr} | " + " | ".join(f"{x:.1f}" for x in row) + " |")
    md.append("\nTheoretical maximum XFA extraction per year if *every* payout cycle hits the cap in the minimum number of days "
              "(requires earning ≥ 2× the cap per cycle, because payouts are limited to 50 % of the balance):\n")
    md.append("| account / path | cap per payout | min days per cycle | 1 account | 5 accounts | daily profit needed per account |\n|---|---|---|---|---|---|")
    for name, cap, days in (("50K Standard", 2000, 5), ("150K Standard", 5000, 5), ("50K Consistency", 3000, 3), ("150K Consistency", 6000, 3)):
        c1 = theoretical_payout_ceiling(cap, days, 1)
        js.setdefault("ceilings", []).append({"name": name, "cap": cap, "days": days, "one": c1})
        md.append(f"| {name} | ${cap:,} | {days} | ${c1:,.0f} | ${5 * c1:,.0f} | ${2 * cap / days:,.0f} |")
    out = ROOT / "docs" / "results"
    (out / "aggressive_topstep.md").write_text("\n".join(md) + "\n")
    (out / "aggressive_topstep.json").write_text(json.dumps(js, indent=1, default=float))
    print("\n".join(md))


if __name__ == "__main__":
    main()
