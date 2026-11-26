"""Steady-state economics: S1 traded on MES + MNQ (≈1.4 trades/day), 1- vs 2-year horizons,
extended risk grid, 1 vs 5 copy-traded accounts. Writes docs/results/portfolio_economics.md."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from qtengine.prop import PRESET_MODELS, SimSizing, get_program, simulate_lifecycle

ROOT = Path(__file__).resolve().parents[2]
EURUSD = 1.16
PATHS = 4000


def row(prog_key, model, risk, days, n_acc=1):
    prog = get_program(prog_key)
    r = simulate_lifecycle(prog, model, SimSizing(risk_dollars=risk), horizon_days=days, n_paths=PATHS,
                           n_accounts=n_acc, record_paths=False, seed=11)
    per_day = r["net_mean"] / days / EURUSD
    med_day = r["net_median"] / days / EURUSD
    return (f"| {prog_key} | {model.name} | {days // 252}y | {risk} | {n_acc} | {r['net_mean']:,.0f} | {r['net_median']:,.0f} | "
            f"{r['net_p05']:,.0f} | {r['net_p95']:,.0f} | {r['p_net_positive']:.0%} | {per_day:,.1f} | {med_day:,.1f} |")


def main():
    s1p = replace(PRESET_MODELS["S1_planning"], name="S1_planning_MES+MNQ", trades_per_day=1.4, max_trades_per_day=4)
    s1o = replace(PRESET_MODELS["S1_optimistic"], name="S1_optimistic_MES+MNQ", trades_per_day=1.4, max_trades_per_day=4)
    md = ["# Portfolio / steady-state economics\n",
          f"S1 on MES and MNQ treated as 1.4 independent trades/day (optimistic: the two are ~0.8 correlated). "
          f"{PATHS:,} paths/cell, EURUSD {EURUSD}. Net = payouts (trader share) − all fees over the horizon. "
          "€/day columns are per trading day over the whole horizon.\n",
          "| program | model | horizon | risk $/trade | accounts | net mean $ | net median $ | p05 $ | p95 $ | P(net>0) | €/day mean | €/day median |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for model in (s1p, s1o):
        for prog_key, risks in (("topstep_50k", [300, 500, 700]), ("topstep_150k", [675, 1125, 1500])):
            for days in (252, 504):
                for risk in risks:
                    md.append(row(prog_key, model, risk, days))
        md.append(row("topstep_150k", model, 1125, 504, n_acc=5))
    out = ROOT / "docs" / "results" / "portfolio_economics.md"
    out.write_text("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
