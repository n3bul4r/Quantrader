"""Deep dive on the chosen $4k/month plan: 5 × Topstep 50K, $500 risk/trade, $2,000 payout cushion.

    python scripts/best_4k_plan.py
Varies the edge (none → optimistic) and the monthly top-up (€0 / €100 / €200) over 36 months.
Writes docs/results/best_4k_plan.{md,json}.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from qtengine.prop import PRESET_MODELS, get_program
from qtengine.prop.fleet import simulate_bootstrap
from qtengine.prop.simulator import PayoutPolicy, SimSizing

ROOT = Path(__file__).resolve().parents[2]
TARGET, MONTHS, PATHS = 4000, 36, 1500


def run(model, topup, slots=5, risk=500, cushion=2000, paths=PATHS):
    prog = get_program("topstep_50k")
    r = simulate_bootstrap(prog, model, 348, max_slots=slots, rho=0.4, sizing=SimSizing(risk_dollars=risk),
                           payout_policy=PayoutPolicy(min_profit_to_request=cushion), horizon_days=MONTHS * 21,
                           n_paths=paths, seed=23, monthly_topup=topup, return_monthly=True)
    mc = r["monthly_cash"]
    roll = np.stack([mc[max(0, i - 2):i + 1].mean(axis=0) for i in range(MONTHS)])
    hit = roll >= TARGET
    first = np.where(hit.any(0), hit.argmax(0) + 1, -1)
    cum = np.cumsum(mc, axis=0)
    return {
        "p_3m_by": {m: float((first[(first > 0)] <= m).sum() / mc.shape[1]) for m in (12, 24, 36)},
        "median_first_month": float(np.median(first[first > 0])) if (first > 0).any() else None,
        "y2_median": float(np.median(mc[12:24].mean(0))), "y3_median": float(np.median(mc[24:36].mean(0))),
        "y3_mean": float(mc[24:36].mean()), "p_y3_target": float((mc[24:36].mean(0) >= TARGET).mean()),
        "cum36_median": float(np.median(cum[-1])), "cum36_p05": float(np.quantile(cum[-1], 0.05)),
        "p_loss_36": float((cum[-1] < 0).mean()),
        "quarterly_median": [float(np.median(mc[q * 3:(q + 1) * 3].mean(0))) for q in range(MONTHS // 3)],
    }


def main():
    zero = replace(PRESET_MODELS["zero_edge"], name="zero_edge_basket", trades_per_day=2.4, max_trades_per_day=6)
    models = [zero, PRESET_MODELS["S1_planning"], PRESET_MODELS["basket_planning"], PRESET_MODELS["basket_optimistic"]]
    md = ["# The $4k/month plan, in depth: 5 × Topstep 50K, $500 risk per trade\n",
          "Start €300 ($348); every Combine ($49/month), renewal and $149 activation is paid from the bankroll (start money + "
          "top-ups + payouts); payouts buy new Combines until 5 accounts run. $500 risk per trade (25 % of the $2,000 max loss), "
          "daily stop $1,000, payouts only after a $2,000 cushion. Accounts trade different market mixes (ρ = 0.4). "
          f"{PATHS} paths, {MONTHS} months. 'Net' = payouts − all fees (top-ups are your money, not income).\n",
          "| edge | top-up | P(a 3-month stretch ≥ $4k/mo) by month 12 | by 24 | by 36 | median month it first happens | year-2 median $/mo | year-3 median $/mo | P(year-3 avg ≥ $4k) | 36-month net median | P(net loss after 3 y) |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    js = []
    for m in models:
        for eur, usd in ((0, 0.0), (100, 116.0), (200, 232.0)):
            r = run(m, usd)
            js.append({"model": m.name, "topup_eur": eur, **r})
            fm = "—" if r["median_first_month"] is None else f"{r['median_first_month']:.0f}"
            md.append(f"| {m.name} | €{eur}/mo | {r['p_3m_by'][12]:.0%} | {r['p_3m_by'][24]:.0%} | {r['p_3m_by'][36]:.0%} | {fm} | "
                      f"${r['y2_median']:,.0f} | ${r['y3_median']:,.0f} | {r['p_y3_target']:.0%} | ${r['cum36_median']:,.0f} | {r['p_loss_36']:.0%} |")
            print(m.name, eur, "done", flush=True)
    md.append("\n## Median net per month, by quarter (€100/month top-up)\n")
    md.append("| edge | " + " | ".join(f"Q{q + 1}" for q in range(MONTHS // 3)) + " |\n|---|" + "---|" * (MONTHS // 3))
    for r in js:
        if r["topup_eur"] == 100:
            md.append(f"| {r['model']} | " + " | ".join(f"${x:,.0f}" for x in r["quarterly_median"]) + " |")
    md.append("\n## Levers that move the planning case toward $4k/month\n")
    md.append("6 markets = MES, MNQ, M2K, MCL, MGC, M6E ≈ 3.2 effectively independent trades/day (assumption: equity indices "
              "count ≈ 1.3 markets because they are ~0.85 correlated). 10 accounts = 5 Topstep 50K + 5 at a second firm, "
              "approximated with Topstep 50K economics.\n")
    md.append("| setup (planning edge) | top-up | P(3-mo ≥ $4k by 24 / 36) | year-2 median $/mo | year-3 median $/mo | P(year-3 avg ≥ $4k) | 36-month net median | P(net loss) |")
    md.append("|---|---|---|---|---|---|---|---|")
    b6 = replace(PRESET_MODELS["basket_planning"], name="basket6_planning", trades_per_day=3.2, max_trades_per_day=8)
    levers = []
    for label, model, slots, eur, usd, paths in (
            ("4 markets × 5 accounts", PRESET_MODELS["basket_planning"], 5, 100, 116.0, PATHS),
            ("6 markets × 5 accounts", b6, 5, 100, 116.0, PATHS),
            ("6 markets × 10 accounts", b6, 10, 100, 116.0, 800),
            ("6 markets × 10 accounts", b6, 10, 200, 232.0, 800)):
        r = run(model, usd, slots=slots, paths=paths)
        levers.append({"setup": label, "topup_eur": eur, **r})
        md.append(f"| {label} | €{eur}/mo | {r['p_3m_by'][24]:.0%} / {r['p_3m_by'][36]:.0%} | ${r['y2_median']:,.0f} | ${r['y3_median']:,.0f} | "
                  f"{r['p_y3_target']:.0%} | ${r['cum36_median']:,.0f} | {r['p_loss_36']:.0%} |")
        print(label, eur, "done", flush=True)
    js.append({"levers": levers})
    (ROOT / "docs" / "results" / "best_4k_plan.md").write_text("\n".join(md) + "\n")
    (ROOT / "docs" / "results" / "best_4k_plan.json").write_text(json.dumps(js, indent=1, default=float))
    print("\n".join(md))


if __name__ == "__main__":
    main()
