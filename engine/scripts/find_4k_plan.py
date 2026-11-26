"""Find the Topstep plan with the best chance of $4,000/month net, starting from €300 + €100/month.

Assumed-edge mode (now):
    python scripts/find_4k_plan.py
Real-data mode (once 1-minute CSVs exist, one file per market: MES.csv, MNQ.csv, MCL.csv, MGC.csv):
    python scripts/find_4k_plan.py --data-dir ../data/real

Real-data mode runs the full research pipeline per market (search → walk-forward → PBO →
deflated Sharpe), keeps the markets that pass the gate, replays their walk-forward trades day
by day across accounts (real correlations), and then searches the account plan.

Objective: P(average monthly net cash in months 13-24 ≥ target). Net cash = payouts (your
share) − every Combine/renewal/activation fee. Your €100/month top-ups are funding, not income.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from qtengine.data import load_bars
from qtengine.features import market_panel
from qtengine.prop import PRESET_MODELS, get_program
from qtengine.prop.empirical import MarketTradeLog, SlotDayModel, slot_assignment
from qtengine.prop.fleet import simulate_bootstrap
from qtengine.prop.simulator import PayoutPolicy, SimSizing
from qtengine.research.engine import DEFAULT_SPACE, MarketFeatures, run_search, sample_configs, wf_oos_trades

ROOT = Path(__file__).resolve().parents[2]
# Small grid fixed in advance around the published noise-area strategy: few trials = trustworthy out-of-sample numbers
PREREG = {"lookback": [14], "band_mult": [0.8, 1.0, 1.2], "first_dec": [30], "dec_every": [30], "last_entry": [360],
          "exit_min": [389], "stop_floor": [0.5, 1.0], "trail_mode": [0, 3], "target_r": [0.0], "max_entries": [1, 3],
          "regime_filter": [0], "direction": [0]}
PROGRAMS = ["topstep_50k", "topstep_100k", "topstep_150k"]
RISK_FRACS = [0.15, 0.25, 0.35]
SLOTS = [1, 3, 5]


def evaluate(prog, model, risk, slots, cushion, a, slot_model=None):
    r = simulate_bootstrap(prog, model, a.budget, max_slots=slots, rho=0.4, sizing=SimSizing(risk_dollars=risk),
                           payout_policy=PayoutPolicy(min_profit_to_request=cushion), horizon_days=a.months * 21,
                           n_paths=a.paths, seed=11, monthly_topup=a.topup, slot_model=slot_model, return_monthly=True)
    mc = r["monthly_cash"]                                   # [months, paths]
    y2 = mc[12:24].mean(axis=0) if mc.shape[0] >= 24 else mc[-12:].mean(axis=0)
    roll = np.stack([mc[max(0, i - 2):i + 1].mean(axis=0) for i in range(mc.shape[0])])   # trailing 3-month average
    hit = roll >= a.target
    first = np.where(hit.any(0), hit.argmax(0) + 1, -1)
    cum = mc.sum(axis=0)
    return {"program": prog.key, "risk": risk, "risk_frac": risk / prog.evaluation.max_loss, "slots": slots, "cushion": cushion,
            "p_target_y2": float((y2 >= a.target).mean()), "y2_median": float(np.median(y2)), "y2_mean": float(y2.mean()),
            "y2_p25": float(np.quantile(y2, 0.25)), "y2_p75": float(np.quantile(y2, 0.75)),
            "p_ever_3m_target": float(hit.any(0).mean()),
            "median_month_3m_target": float(np.median(first[first > 0])) if (first > 0).any() else None,
            "p_net_negative_2y": float((cum < 0).mean()), "cum_median_2y": float(np.median(cum)),
            "monthly_quantiles": [[float(x) for x in np.quantile(mc[m], [0.25, 0.5, 0.75])] for m in range(mc.shape[0])]}


def search_plans(model, a, slot_factory=None, label=""):
    rows = []
    modes = (("all", "leave_one_out") if getattr(a, "_n_markets", 2) > 1 else ("all",)) if slot_factory else (None,)
    for pk in PROGRAMS:
        prog = get_program(pk)
        for f in RISK_FRACS:
            risk = round(f * prog.evaluation.max_loss)
            for n in SLOTS:
                for cushion in (0.0, prog.funded.max_loss):
                    for mode in modes:
                        if mode == "leave_one_out" and n == 1:
                            continue
                        sm = slot_factory(n, mode) if slot_factory else None
                        r = evaluate(prog, model, risk, n, cushion, a, sm)
                        r["assignment"] = mode or "parametric (ρ = 0.4)"
                        rows.append(r)
        print(label, pk, "done", flush=True)
    return sorted(rows, key=lambda r: (r["p_target_y2"], r["y2_median"]), reverse=True)


def real_data_logs(data_dir: Path, a):
    logs, report, calendar = {}, [], None
    panels = {}
    for f in sorted(data_dir.glob("*.csv")) + sorted(data_dir.glob("*.parquet")):
        mk = f.stem.upper()
        if a.markets and mk not in a.markets:
            continue
        panels[mk] = market_panel(load_bars(f), mk)
    if not panels:
        raise SystemExit(f"no CSV/Parquet files in {data_dir}")
    calendar = sorted(set().union(*[set(p.dates) for p in panels.values()]))
    results = {}
    for mk, panel in panels.items():
        mf = MarketFeatures.build(panel, mk)
        if a.space == "prereg":
            from qtengine.research.engine import grid
            cfgs = [("NAM", c) for c in grid(PREREG)]
        else:
            cfgs = []
            for fam, n in (("NAM", a.nam), ("ORB", a.orb), ("VWR", a.vwr), ("LDM", None)):
                cfgs += sample_configs({fam: DEFAULT_SPACE[fam]}, n, seed=7)
        res = run_search(mf, cfgs)
        wf, pbo = res.wf, res.pbo
        share_pos = float((res.scores.sharpe_oos > 0).mean())
        if a.space == "prereg":
            # near-identical pre-registered variants: PBO (rank stability) is uninformative; require the family to work instead
            passed = bool((wf["oos_sharpe"] or 0) > 0.5 and (pbo.get("dsr_effective") or 0) >= 0.95 and share_pos >= 0.6)
        else:
            passed = bool((wf["oos_sharpe"] or 0) > 0.5 and (pbo.get("pbo") or 1) < 0.2 and (pbo.get("dsr_effective") or 0) >= 0.95)
        candidate = bool(a.min_wf is not None and (wf["oos_sharpe"] or -9) >= a.min_wf and (pbo.get("pbo") or 1) < 0.3)
        report.append({"market": mk, "days": panel.n_days, "configs": len(cfgs), "wf_oos_sharpe": wf["oos_sharpe"], "share_oos_positive": share_pos,
                       "pbo": pbo.get("pbo"), "dsr_effective": pbo.get("dsr_effective"), "passed": passed, "candidate": candidate})
        print(mk, report[-1], flush=True)
        if passed or candidate or a.no_gate:
            t = wf_oos_trades(mf, res)
            first_oos = panel.dates[61 + 504] if panel.n_days > 61 + 504 else panel.dates[-1]
            results[mk] = (panel, t, first_oos)
    if not results:
        return {}, 0, report
    # replay only the period every kept market was trading out-of-sample (otherwise empty days bias results down)
    start = max(r[2] for r in results.values())
    calendar = [d for d in calendar if d >= start]
    cal_idx = {d: i for i, d in enumerate(calendar)}
    for mk, (panel, t, _) in results.items():
        t = t.assign(date=[panel.dates[d] for d in t["day"]])
        t = t[t["date"].isin(cal_idx)]
        t["day"] = [cal_idx[d] for d in t["date"]]
        logs[mk] = MarketTradeLog(mk, t[["day", "entry_min", "r_gross", "mae_r", "mfe_r", "risk_pts"]])
    print(f"replay calendar: {len(calendar)} days from {start.date()}", flush=True)
    return logs, len(calendar), report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=None)
    ap.add_argument("--no-gate", action="store_true", help="use markets even if they fail the gate (NOT for real money)")
    ap.add_argument("--space", choices=["default", "prereg"], default="default")
    ap.add_argument("--markets", nargs="*", default=None, help="restrict to these market files, e.g. MNQ MES")
    ap.add_argument("--min-wf", type=float, default=None,
                    help="also keep 'candidate' markets: walk-forward OOS Sharpe >= this and PBO < 30 %% (paper-trade only)")
    ap.add_argument("--target", type=float, default=4000)
    ap.add_argument("--budget", type=float, default=348)     # €300
    ap.add_argument("--topup", type=float, default=116)      # €100/month
    ap.add_argument("--months", type=int, default=24)
    ap.add_argument("--paths", type=int, default=500)
    ap.add_argument("--nam", type=int, default=6000)
    ap.add_argument("--orb", type=int, default=2000)
    ap.add_argument("--vwr", type=int, default=1000)
    ap.add_argument("--tag", default=None)
    a = ap.parse_args()
    tag = a.tag or ("real" if a.data_dir else "assumed")
    md = [f"# Best plan for ${a.target:,.0f}/month — {tag}\n",
          f"Start ${a.budget:.0f} (€300) + ${a.topup:.0f}/month (€100). Every Combine, renewal and activation fee is paid from "
          "that bankroll plus payouts; payouts buy more accounts. Target = average monthly net cash (payouts − all fees) "
          f"over months 13-24 ≥ ${a.target:,.0f}. {a.paths} paths per plan; plans searched: account size × risk/trade × "
          "number of accounts × payout cushion (54 per edge).\n"]
    js = {"args": vars(a), "results": {}}
    if a.data_dir:
        logs, n_days, report = real_data_logs(Path(a.data_dir), a)
        js["gate_report"] = report
        md.append("## Validation gate per market (real data)\n")
        md.append("| market | days | configs | walk-forward OOS Sharpe | PBO | deflated Sharpe (eff.) | strict gate | candidate |\n|---|---|---|---|---|---|---|---|")
        for r in report:
            md.append(f"| {r['market']} | {r['days']} | {r['configs']:,} | {r['wf_oos_sharpe'] or float('nan'):.2f} | "
                      f"{r['pbo'] or float('nan'):.0%} | {r['dsr_effective'] or float('nan'):.2f} | {'PASS' if r['passed'] else 'fail'} | "
                      f"{'yes' if r.get('candidate') else '—'} |")
        if not logs:
            md.append("\n**No market passed the gate. Do not trade this with real money.**")
            (ROOT / "docs" / "results" / f"find_4k_plan_{tag}.md").write_text("\n".join(md) + "\n")
            print("\n".join(md))
            return
        markets = sorted(logs)
        a._n_markets = len(markets)
        factory = lambda n, mode: SlotDayModel(logs, n_days, slot_assignment(markets, n, mode), a.paths, name="real_days")
        edges = {"real (walk-forward OOS trades, day replay)": (PRESET_MODELS["basket_planning"], factory)}
    else:
        edges = {k: (PRESET_MODELS[k], None) for k in ("S1_planning", "basket_planning", "basket_optimistic")}

    for label, (model, factory) in edges.items():
        rows = search_plans(model, a, factory, label)
        js["results"][label] = rows
        best = rows[0]
        md.append(f"\n## Edge: {label}\n")
        md.append(f"**Best plan:** {best['slots']} × {best['program']} at ${best['risk']}/trade ({best['risk_frac']:.0%} of max loss), "
                  f"markets per account: {best['assignment']}, "
                  f"payout cushion ${best['cushion']:,.0f}. P(≥ ${a.target:,.0f}/month in year 2) = **{best['p_target_y2']:.0%}**; "
                  f"year-2 monthly net: median ${best['y2_median']:,.0f} (25–75 %: ${best['y2_p25']:,.0f} … ${best['y2_p75']:,.0f}); "
                  f"P(any 3-month stretch ≥ ${a.target:,.0f}/month) {best['p_ever_3m_target']:.0%}"
                  + (f", first reached around month {best['median_month_3m_target']:.0f} (median)" if best['median_month_3m_target'] else "")
                  + f"; P(net loss after 2 years) {best['p_net_negative_2y']:.0%}.\n")
        md.append("| rank | account | risk/trade | accounts | markets per account | cushion | P(≥ target, yr 2) | yr-2 median $/month | yr-2 mean | P(any 3-mo ≥ target) | P(2-yr net < 0) |")
        md.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for i, r in enumerate(rows[:10], 1):
            md.append(f"| {i} | {r['program']} | ${r['risk']} ({r['risk_frac']:.0%}) | {r['slots']} | {r['assignment']} | ${r['cushion']:,.0f} | "
                      f"{r['p_target_y2']:.0%} | ${r['y2_median']:,.0f} | ${r['y2_mean']:,.0f} | {r['p_ever_3m_target']:.0%} | {r['p_net_negative_2y']:.0%} |")
        md.append("\nMonth-by-month net cash of the best plan (25th / median / 75th percentile):\n")
        md.append("| month | " + " | ".join(str(m) for m in (3, 6, 9, 12, 15, 18, 21, 24)) + " |\n|---|" + "---|" * 8)
        q = best["monthly_quantiles"]
        md.append("| net $ | " + " | ".join(f"{q[m - 1][0]:,.0f} / **{q[m - 1][1]:,.0f}** / {q[m - 1][2]:,.0f}" for m in (3, 6, 9, 12, 15, 18, 21, 24)) + " |")
    if a.data_dir:
        md.append("\n## Fixed plans on the real trades, 36 months (50K accounts, $500 risk/trade, $2,000 payout cushion)\n")
        md.append("All accounts trade the same validated market(s) on the same historical days (perfectly correlated when only one market passes).\n")
        md.append("| accounts | top-up | year-2 median $/mo | year-3 median $/mo | P(year-3 avg ≥ target) | P(a 3-month stretch ≥ target) | 36-month net median | P(net loss) |")
        md.append("|---|---|---|---|---|---|---|---|")
        js["fixed36"] = []
        prog = get_program("topstep_50k")
        for slots in (1, 5, 10):
            for eur, usd in ((100, 116.0), (200, 232.0)):
                sm = factory(slots, "all")
                r = simulate_bootstrap(prog, None, a.budget, max_slots=slots, sizing=SimSizing(risk_dollars=500),
                                       payout_policy=PayoutPolicy(min_profit_to_request=2000), horizon_days=36 * 21,
                                       n_paths=a.paths, seed=29, monthly_topup=usd, slot_model=sm, return_monthly=True)
                mc = r["monthly_cash"]
                roll = np.stack([mc[max(0, i - 2):i + 1].mean(axis=0) for i in range(mc.shape[0])])
                row = {"slots": slots, "topup_eur": eur, "y2": float(np.median(mc[12:24].mean(0))), "y3": float(np.median(mc[24:36].mean(0))),
                       "p_y3": float((mc[24:36].mean(0) >= a.target).mean()), "p_3m": float((roll >= a.target).any(0).mean()),
                       "cum": float(np.median(mc.sum(0))), "p_loss": float((mc.sum(0) < 0).mean())}
                js["fixed36"].append(row)
                md.append(f"| {slots} | €{eur}/mo | ${row['y2']:,.0f} | ${row['y3']:,.0f} | {row['p_y3']:.0%} | {row['p_3m']:.0%} | ${row['cum']:,.0f} | {row['p_loss']:.0%} |")
    out = ROOT / "docs" / "results"
    (out / f"find_4k_plan_{tag}.md").write_text("\n".join(md) + "\n")
    (out / f"find_4k_plan_{tag}.json").write_text(json.dumps(js, indent=1, default=float))
    print("\n".join(md))


if __name__ == "__main__":
    main()
