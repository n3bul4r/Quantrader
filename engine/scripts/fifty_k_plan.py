"""One Topstep 50K at ~$500 risk per trade: what does a month really pay?

    python scripts/fifty_k_plan.py
Writes docs/results/fifty_k_plan.{md,json}.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from qtengine.prop import PRESET_MODELS, get_program
from qtengine.prop.fleet import MONTH, CorrelatedModel
from qtengine.prop.simulator import PayoutPolicy, SimSizing, simulate_lifecycle

ROOT = Path(__file__).resolve().parents[2]
MONTHS = 6
PATHS = 4000


class NoRebuy:
    """Every slot starts active; a lost account is NOT replaced (isolates one account's economics)."""
    def initial_active(self, n):
        return np.ones(n, dtype=bool)

    def open_slots(self, phase, fees, paid_net, program):
        return np.zeros(phase.shape[0], dtype=bool)

    def can_pay(self, due, fees, paid_net, program):
        return np.ones(due.shape[0], dtype=bool)


def funded_start(prog):
    """Same funded rules, but the account starts funded on day 1 with no fees (pure funded economics)."""
    ev = replace(prog.evaluation, profit_target=-1e9, min_trading_days=0, consistency_pct=None, max_micros=0)
    return replace(prog, evaluation=ev, eval_fee=0.0, activation_fee=0.0, eval_fee_recurring_days=None)


def funded_run(prog, model, risk, n_accounts=1, rho=1.0, paths=PATHS, cushion=0.0):
    m = CorrelatedModel(model, n_accounts, paths, rho) if n_accounts > 1 else model
    res = simulate_lifecycle(funded_start(prog), m, SimSizing(risk_dollars=risk), horizon_days=MONTHS * MONTH + 1,
                             n_paths=n_accounts * paths, seed=17, record_paths=False, return_cash_path=True,
                             controller=NoRebuy(), payout_policy=PayoutPolicy(min_profit_to_request=cushion))
    cash = res.pop("_cash_path").reshape(-1, n_accounts, paths).sum(axis=1)       # cumulative payouts (trader share)
    total = cash[-1]
    monthly = total / MONTHS
    return {"p_blown": res["funded_blowups_mean"], "total_mean": float(total.mean()), "total_median": float(np.median(total)),
            "monthly_mean": float(monthly.mean()), "monthly_median": float(np.median(monthly)),
            "p_3k": float((monthly >= 3000).mean()), "p_zero": float((total <= 0).mean())}


def main():
    prog = get_program("topstep_50k")
    models = [PRESET_MODELS["S1_planning"], PRESET_MODELS["basket_planning"], PRESET_MODELS["basket_optimistic"],
              replace(PRESET_MODELS["zero_edge"], name="zero_edge_basket", trades_per_day=2.4, max_trades_per_day=6)]
    md = ["# One Topstep 50K at ~$500 risk per trade — what a month really pays\n",
          f"Funded-account economics: account starts funded, trades {MONTHS} months, a lost account is NOT replaced. "
          "Topstep 50K XFA rules (max loss $2,000 EOD-trailing, payouts after 5 winning days ≥ $150, up to 50 % of the "
          "balance, cap $2,000 per payout, 90 % to you). Daily stop 2R. Trade models are assumptions.\n"]
    js = {"expectation": [], "single": [], "eval": [], "multi": []}

    md.append("## 1. '$500 per trade' is risk, not profit\n")
    md.append("| edge model | win rate | avg win / avg loss at $500 risk | expected profit per trade | trades/day | expected P&L per month (before rules) | risk per trade needed for $3,500/month |")
    md.append("|---|---|---|---|---|---|---|")
    for m in models[:3]:
        s = m.summary()
        per_trade = s["expected_net_r"] * 500
        per_month = per_trade * m.trades_per_day * MONTH
        need = 3500 / (s["expected_net_r"] * m.trades_per_day * MONTH)
        js["expectation"].append({"model": m.name, "per_trade": per_trade, "per_month": per_month, "risk_needed": need})
        md.append(f"| {m.name} | {s['net_win_rate']:.0%} | +${s['avg_win_r'] * 500:,.0f} / −${s['avg_loss_r'] * 500:,.0f} | "
                  f"**${per_trade:,.0f}** | {m.trades_per_day} | ${per_month:,.0f} | ${need:,.0f} ({need / 2000:.0%} of the $2,000 max loss) |")

    md.append("\n## 2. Passing the 50K Combine (one attempt)\n")
    md.append("| edge model | risk/trade | P(pass) | P(fail) | median days to pass |\n|---|---|---|---|---|")
    for m in models:
        for risk in (200, 300, 500):
            r = simulate_lifecycle(prog, m, SimSizing(risk_dollars=risk), single_attempt=True, horizon_days=252, n_paths=3000, seed=3)
            js["eval"].append({"model": m.name, "risk": risk, "p_pass": r["p_pass"], "days": r["median_days_to_pass"]})
            md.append(f"| {m.name} | ${risk} | {r['p_pass']:.0%} | {r['p_fail']:.0%} | {r['median_days_to_pass'] or '—'} |")

    md.append(f"\n## 3. One funded 50K, first {MONTHS} months\n")
    md.append("| edge model | risk/trade | P(account lost within 6 months) | average payout per month (mean) | (median) | P(≥ $3,000/month on average) | P(no payout at all) |")
    md.append("|---|---|---|---|---|---|---|")
    for m in models:
        for risk in (200, 300, 500):
            r = funded_run(prog, m, risk)
            js["single"].append({"model": m.name, "risk": risk, **r})
            md.append(f"| {m.name} | ${risk} | {r['p_blown']:.0%} | ${r['monthly_mean']:,.0f} | ${r['monthly_median']:,.0f} | {r['p_3k']:.0%} | {r['p_zero']:.0%} |")

    md.append(f"\n## 4. Several funded 50Ks (different market mix per account, ρ = 0.4), first {MONTHS} months\n")
    md.append("| edge model | accounts | risk/trade | average payout per month (mean) | (median) | P(≥ $3,000/month) | P(all accounts lost) |")
    md.append("|---|---|---|---|---|---|---|")
    for m in models[1:3]:
        for n, risk in ((1, 300), (3, 300), (5, 300), (5, 500)):
            r = funded_run(prog, m, risk, n_accounts=n, rho=0.4, paths=1500)
            js["multi"].append({"model": m.name, "accounts": n, "risk": risk, **r})
            md.append(f"| {m.name} | {n} | ${risk} | ${r['monthly_mean']:,.0f} | ${r['monthly_median']:,.0f} | {r['p_3k']:.0%} | — |")
    md.append(f"\n## 5. Bigger and more accounts (payout only after a cushion = max loss), first {MONTHS} months, no replacement\n")
    md.append("| edge model | setup | risk/trade | average payout per month (mean) | (median) | P(≥ $3,000/month) | P(no payout at all) |")
    md.append("|---|---|---|---|---|---|---|")
    p150 = get_program("topstep_150k")
    js["bigger"] = []
    for m in models[1:3]:
        for label, pg, n, risk, cush in (("1 × 50K", prog, 1, 500, 2000), ("1 × 150K", p150, 1, 1125, 4500),
                                          ("5 × 50K", prog, 5, 500, 2000), ("3 × 150K", p150, 3, 1125, 4500)):
            r = funded_run(pg, m, risk, n_accounts=n, rho=0.4, paths=2000 if n == 1 else 1000, cushion=cush)
            js["bigger"].append({"model": m.name, "setup": label, "risk": risk, **r})
            md.append(f"| {m.name} | {label} | ${risk} | ${r['monthly_mean']:,.0f} | ${r['monthly_median']:,.0f} | {r['p_3k']:.0%} | {r['p_zero']:.0%} |")
    out = ROOT / "docs" / "results"
    (out / "fifty_k_plan.md").write_text("\n".join(md) + "\n")
    (out / "fifty_k_plan.json").write_text(json.dumps(js, indent=1, default=float))
    print("\n".join(md))


if __name__ == "__main__":
    main()
