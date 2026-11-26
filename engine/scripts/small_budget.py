"""What is the best use of €300? Bootstrap simulation: every Combine, renewal and activation fee
is paid from the bankroll (start money + payouts); payouts buy more accounts (up to 5).

    python scripts/small_budget.py
Writes docs/results/small_budget.{md,json}.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from qtengine.growth import SCENARIOS, simulate_growth
from qtengine.prop import PRESET_MODELS, get_program
from qtengine.prop.fleet import simulate_bootstrap
from qtengine.prop.simulator import PayoutPolicy, SimSizing

ROOT = Path(__file__).resolve().parents[2]
START = 348.0          # €300 at EURUSD 1.16
YEARS = 3
PATHS = 800


def firms():
    top = get_program("topstep_50k")
    apex = get_program("apex_50k_eod")
    apex_cheap = replace(apex, key="apex_50k_eod_discounted", name="Apex 50K EOD at a ~70 % discount ($30 eval, $99 activation)",
                         eval_fee=30.0, activation_fee=99.0)
    return [top, apex_cheap]


def main():
    zero = replace(PRESET_MODELS["zero_edge"], name="zero_edge_basket", trades_per_day=2.4, max_trades_per_day=6)
    models = [PRESET_MODELS["S1_planning"], PRESET_MODELS["basket_planning"], PRESET_MODELS["basket_optimistic"], zero]
    md = ["# Starting with €300: bootstrap into a prop fleet\n",
          f"Bankroll ${START:.0f} (€300). Every Combine purchase, monthly renewal and activation fee is paid from the bankroll "
          "(start money + payouts); a new Combine is only bought when the bankroll still covers its activation fee afterwards. "
          f"Payouts buy more accounts, up to 5. ρ = 0.4 between slots, payout once profit ≥ max loss. {PATHS} paths, {YEARS} years. "
          "Net = bankroll − €300 start. Trade models are assumptions; firm prices vary with promotions.\n"]
    js = {"runs": []}
    for prog in firms():
        md.append(f"\n## {prog.name}\n")
        md.append("| edge | risk/trade (% of max loss) | P(ever ahead) | P(busted) | median net 1y | mean net 1y | mean net 3y | P(≥$10k by 3y) | P(≥$100k by 3y) | median months to $10k |")
        md.append("|---|---|---|---|---|---|---|---|---|---|")
        for m in models:
            for f in (0.10, 0.15, 0.25, 0.35):
                risk = round(f * prog.evaluation.max_loss)
                r = simulate_bootstrap(prog, m, START, sizing=SimSizing(risk_dollars=risk),
                                       payout_policy=PayoutPolicy(min_profit_to_request=prog.funded.max_loss),
                                       horizon_days=252 * YEARS, n_paths=PATHS, seed=4)
                y1, y3 = r["by_year"][1], r["by_year"][YEARS]
                m10, m100 = r["milestones"]["10000"], r["milestones"]["100000"]
                row = {"firm": prog.key, "model": m.name, "risk": risk, "risk_frac": f, "p_ahead": r["p_net_positive_ever"],
                       "p_bust": r["p_stuck_broke_end"], "y1": y1, "y3": y3, "m10": m10, "m100": m100}
                js["runs"].append(row)
                mm = "—" if m10["median_months"] is None else f"{m10['median_months']:.0f}"
                md.append(f"| {m.name} | ${risk} ({f:.0%}) | {r['p_net_positive_ever']:.0%} | {r['p_stuck_broke_end']:.0%} | "
                          f"${y1['median']:,.0f} | ${y1['mean']:,.0f} | ${y3['mean']:,.0f} | {m10['p_reach']:.0%} | {m100['p_reach']:.0%} | {mm} |")
            print(prog.key, m.name, "done", flush=True)

    md.append("\n## The biggest lever: adding €100/month ($116) to the bankroll\n")
    md.append("Net = payouts − every fee, i.e. the result versus everything you put in (€300 + €100/month = $4,524 over 3 years).\n")
    md.append("| firm | edge | risk/trade | top-up | P(busted) | median net 3y | mean net 3y | 5th pct 3y | P(≥$10k) | P(≥$100k) | median months to $10k |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|")
    js["topup"] = []
    top, apex_cheap = firms()
    for prog, risk in ((top, 300), (top, 500), (apex_cheap, 200)):
        for m in (PRESET_MODELS["basket_planning"], zero):
            for tu in (0.0, 116.0):
                r = simulate_bootstrap(prog, m, START, sizing=SimSizing(risk_dollars=risk),
                                       payout_policy=PayoutPolicy(min_profit_to_request=prog.funded.max_loss),
                                       horizon_days=252 * YEARS, n_paths=PATHS, seed=4, monthly_topup=tu)
                y3, m10, m100 = r["by_year"][YEARS], r["milestones"]["10000"], r["milestones"]["100000"]
                js["topup"].append({"firm": prog.key, "model": m.name, "risk": risk, "topup": tu, "p_bust": r["p_stuck_broke_end"],
                                    "y3": y3, "m10": m10, "m100": m100})
                mm = "—" if m10["median_months"] is None else f"{m10['median_months']:.0f}"
                md.append(f"| {prog.key} | {m.name} | ${risk} | {'€100/mo' if tu else 'none'} | {r['p_stuck_broke_end']:.0%} | "
                          f"${y3['median']:,.0f} | ${y3['mean']:,.0f} | ${y3['p05']:,.0f} | {m10['p_reach']:.0%} | {m100['p_reach']:.0%} | {mm} |")

    md.append("\n## For comparison: €300 traded as your own account (CFD, 1 % risk per trade, no contributions)\n")
    md.append("| edge | median after 1 y | after 3 y | P(below €300 at 3 y) |\n|---|---|---|---|")
    for key in ("no_edge_cfd_1pct", "s1_plan_cfd_1pct", "s1_opt_cfd_1pct"):
        g = simulate_growth(SCENARIOS[key], 300, 0, years=3, n_paths=2000, checkpoints=(1, 3))
        c1, c3 = g["checkpoints"]
        md.append(f"| {SCENARIOS[key].label} | €{c1['median']:,.0f} | €{c3['median']:,.0f} | {c3['p_below_contributed']:.0%} |")
    out = ROOT / "docs" / "results"
    (out / "small_budget.md").write_text("\n".join(md) + "\n")
    (out / "small_budget.json").write_text(json.dumps(js, indent=1, default=float))
    print("\n".join(md))


if __name__ == "__main__":
    main()
