"""Own-capital growth study: €500 start + €100/month, 1/3/5/10 years, trading vs ETF.

    python scripts/own_capital_growth.py [--paths 5000]

Writes docs/results/own_capital_growth.md and .json. Trading scenarios use the same
assumed S1 trade models as the prop study (planning = published edge after a 58 % haircut).
"""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from qtengine.growth import SCENARIOS, future_value, months_to_target, simulate_growth

ROOT = Path(__file__).resolve().parents[2]
ORDER = ["cash", "etf", "no_edge_cfd_1pct", "no_edge_mes_1lot", "s1_plan_mes_1pct", "s1_plan_mes_1lot",
         "s1_plan_cfd_1pct", "s1_plan_cfd_2pct", "s1_plan_cfd_2mkts_1pct", "s1_opt_cfd_1pct", "s1_opt_cfd_2pct"]


def e(x):
    return f"€{x:,.0f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=5000)
    ap.add_argument("--start", type=float, default=500)
    ap.add_argument("--monthly", type=float, default=100)
    a = ap.parse_args()
    md, js = [], {"start": a.start, "monthly": a.monthly, "paths": a.paths, "runs": {}}
    md.append(f"# Own-capital growth: €{a.start:,.0f} start + €{a.monthly:,.0f}/month\n")
    md.append(f"Monte Carlo, {a.paths:,} paths per scenario, 252 trading days/year, contribution at each month end, "
              "EURUSD 1.16 fixed, **pre-tax** unless stated. Trade models are assumptions (see SYSTEM_DESIGN.md §1).\n")

    md.append("## 1. Deterministic compounding (what a constant return would give)\n")
    md.append("| annual return | 1 year | 3 years | 5 years | 10 years |\n|---|---|---|---|---|")
    det = {}
    for r in (0, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.30, 0.50):
        vals = [future_value(a.start, a.monthly, r, y) for y in (1, 3, 5, 10)]
        det[r] = vals
        md.append(f"| {r:.0%} | " + " | ".join(e(v) for v in vals) + " |")
    js["deterministic"] = {str(k): v for k, v in det.items()}

    md.append("\n## 2. Monte Carlo by scenario\n")
    md.append("p05/p95 = 5th/95th percentile outcome. 'Below contributed' = ended with less than you put in. "
              "Max DD = median of each path's worst peak-to-trough drop.\n")
    md.append("| scenario | years | put in | p05 | median | mean | p95 | P(below put in) | median max DD |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    for k in ORDER:
        res = simulate_growth(SCENARIOS[k], a.start, a.monthly, years=10, n_paths=a.paths, seed=1)
        js["runs"][k] = res
        for c in res["checkpoints"]:
            md.append(f"| {SCENARIOS[k].label} | {c['years']} | {e(c['contributed_eur'])} | {e(c['p05'])} | **{e(c['median'])}** | "
                      f"{e(c['mean'])} | {e(c['p95'])} | {c['p_below_contributed']:.0%} | {c['median_max_drawdown']:.0%} |")
        print(k, "done", flush=True)

    md.append("\n## 3. After an illustrative 30 % flat tax (e.g. France's PFU — check your own country)\n")
    md.append("Trading gains are realised and taxed every year; the accumulating ETF is taxed once, on exit at the horizon "
              "(tax-advantaged wrappers such as a French PEA would lower this further).\n")
    md.append("| scenario | median after 5 y | median after 10 y | mean after 10 y |\n|---|---|---|---|")
    js["after_tax"] = {}
    for k in ("etf", "s1_plan_cfd_1pct", "s1_opt_cfd_1pct"):
        res = simulate_growth(SCENARIOS[k], a.start, a.monthly, years=10, n_paths=a.paths, seed=1, tax_rate=0.30)
        c5, c10 = res["checkpoints"][2], res["checkpoints"][3]
        js["after_tax"][k] = res["checkpoints"]
        md.append(f"| {SCENARIOS[k].label} | {e(c5['median'])} | {e(c10['median'])} | {e(c10['mean'])} |")

    md.append("\n## 4. The contribution lever (S1 planning edge, CFD, 1 % risk — median after 10 years)\n")
    md.append("| monthly contribution | put in | median 10 y | ETF median 10 y |\n|---|---|---|---|")
    js["contrib_sensitivity"] = []
    for m in (100, 200, 300, 500):
        r1 = simulate_growth(SCENARIOS["s1_plan_cfd_1pct"], a.start, m, years=10, n_paths=2000, seed=2, checkpoints=(10,))
        r2 = simulate_growth(SCENARIOS["etf"], a.start, m, years=10, n_paths=2000, seed=2, checkpoints=(10,))
        c1, c2 = r1["checkpoints"][0], r2["checkpoints"][0]
        js["contrib_sensitivity"].append({"monthly": m, "put_in": c1["contributed_eur"], "s1": c1["median"], "etf": c2["median"]})
        md.append(f"| €{m} | {e(c1['contributed_eur'])} | {e(c1['median'])} | {e(c2['median'])} |")

    md.append("\n## 5. When does trading become an income?\n")
    md.append("Capital needed for **€100/day (≈ €25,000/yr)** from trading = 25,000 ÷ net annual return. "
              "At the planning edge sized at ~1 % risk (≈ 15 %/yr expected, ~25-30 % vol) that is ≈ **€165,000**.\n")
    md.append("| monthly contribution | years to €165k at 7 % | at 15 % | at 30 % |\n|---|---|---|---|")
    js["years_to_165k"] = []
    for m in (100, 300, 500, 1000):
        ys = [months_to_target(a.start, m, r, 165_000) for r in (0.07, 0.15, 0.30)]
        js["years_to_165k"].append({"monthly": m, "years": [y / 12 if y else None for y in ys]})
        md.append(f"| €{m} | " + " | ".join(f"{y / 12:.1f}" if y else "> 100" for y in ys) + " |")
    out = ROOT / "docs" / "results"
    (out / "own_capital_growth.md").write_text("\n".join(md) + "\n")
    (out / "own_capital_growth.json").write_text(json.dumps(js, indent=1, default=float))
    print("\n".join(md))


if __name__ == "__main__":
    main()
