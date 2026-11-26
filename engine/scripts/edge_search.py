"""Massive edge search + overfitting audit + Topstep objective.

    python scripts/edge_search.py --tag noise   --momentum 0.0          # what a big search finds in pure noise
    python scripts/edge_search.py --tag edge    --momentum 0.01         # can it find a small real edge?
    python scripts/edge_search.py --tag real --data mes_1m.csv          # real data (UTC 1-min OHLCV)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from qtengine.data import load_bars, synthetic_bars
from qtengine.features import build_panel
from qtengine.prop import SimSizing, get_program, simulate_lifecycle
from qtengine.prop.simulator import EmpiricalTradeModel
from qtengine.research.engine import (DEFAULT_SPACE, MarketFeatures, family_summary, run_search, sample_configs,
                                      wf_oos_trades)

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="noise")
    ap.add_argument("--data", default=None)
    ap.add_argument("--symbol", default="MES")
    ap.add_argument("--days", type=int, default=1500)
    ap.add_argument("--momentum", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--nam", type=int, default=8000)
    ap.add_argument("--orb", type=int, default=2000)
    ap.add_argument("--vwr", type=int, default=2000)
    a = ap.parse_args()

    if a.data:
        from qtengine.features import market_panel
        panel = market_panel(load_bars(a.data), a.symbol)
        source = f"real data: {a.data}"
    else:
        panel = build_panel(synthetic_bars(n_days=a.days, momentum=a.momentum, seed=a.seed))
        source = f"SYNTHETIC {a.days} days, injected momentum κ={a.momentum}"
    mf = MarketFeatures.build(panel, a.symbol)
    space = DEFAULT_SPACE
    configs = []
    for fam, n in (("NAM", a.nam), ("ORB", a.orb), ("VWR", a.vwr), ("LDM", None)):
        configs += sample_configs({fam: space[fam]}, n, seed=a.seed)
    res = run_search(mf, configs, progress=lambda j, n: print(f"{j}/{n}", flush=True))
    fam = family_summary(res)
    lb = res.leaderboard(15)
    oos_tr = wf_oos_trades(mf, res)

    md = [f"# Edge search — {a.tag}\n", f"Data: {source}. Instrument {a.symbol} (all-in cost ${mf.cost_rt:.2f}/RT). "
          f"**{len(configs):,} configurations** across 4 families, searched in {res.elapsed_s:,.0f} s. "
          "In-sample = first 70 % of days, out-of-sample = last 30 %.\n"]
    md.append("## Verdict on the search itself\n")
    md.append(f"| metric | value | meaning |\n|---|---|---|")
    best = res.scores.loc[res.scores[res.scores.trades_is >= 40].sharpe_is.idxmax()]
    md.append(f"| best in-sample Sharpe | {best.sharpe_is:.2f} | what a naive optimiser would show you |")
    md.append(f"| same config, out-of-sample Sharpe | {best.sharpe_oos:.2f} | what it actually did next |")
    md.append(f"| deflated Sharpe (P that the winner is real, {int((res.scores.trades_is >= 40).sum()):,} trials) | {res.dsr_best:.2f} | ≥ 0.95 required |")
    md.append(f"| deflated Sharpe with effective trials (≈ {res.pbo.get('n_effective_trials', float('nan')):,.0f} independent bets) | {res.pbo.get('dsr_effective', float('nan')):.2f} | configs are highly correlated; this is the fairer test |")
    md.append(f"| PBO (CSCV, {res.pbo.get('n_splits', 0)} splits) | {res.pbo.get('pbo', float('nan')):.2f} | ≥ 0.5 = the 'best' config is noise |")
    fx = lambda v, f="{:.2f}": "n/a (history too short)" if v is None else f.format(v)
    md.append(f"| walk-forward OOS Sharpe of the re-selection process | {fx(res.wf['oos_sharpe'])} | the honest number |")
    md.append(f"| walk-forward OOS mean daily R | {fx(res.wf['oos_mean_daily_r'], '{:+.3f}')} | |")
    md.append("\n## By family\n")
    md.append("| family | configs | median IS Sharpe | best IS Sharpe | its OOS Sharpe | share OOS > 0 | configs with win rate ≥ 60 % | their median OOS E[R] |")
    md.append("|---|---|---|---|---|---|---|---|")
    for _, r in fam.iterrows():
        md.append(f"| {r.family} | {r.configs:,} | {r.median_sharpe_is:.2f} | {r.best_sharpe_is:.2f} | {r.best_sharpe_oos:.2f} | "
                  f"{r.share_oos_positive:.0%} | {r.high_winrate_configs:,} | {r.high_winrate_median_exp_r_oos:+.3f} |")
    md.append("\n## In-sample leaderboard (top 15) — and what happened out of sample\n")
    md.append("| # | family | key params | trades/day | win % | IS Sharpe | OOS Sharpe | IS E[R] | OOS E[R] |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    for i, (_, r) in enumerate(lb.iterrows(), 1):
        keys = {k: v for k, v in r.params.items() if k in ("band_mult", "target_r", "trail_mode", "or_len", "band_k", "stop_k", "z_min", "regime_filter", "direction", "stop_frac", "time_stop")}
        md.append(f"| {i} | {r.family} | {keys} | {r.trades_per_day:.2f} | {r.win_rate:.0%} | {r.sharpe_is:.2f} | {r.sharpe_oos:.2f} | {r.exp_r_is:+.3f} | {r.exp_r_oos:+.3f} |")

    md.append("\n## Topstep objective: walk-forward OOS trades through the 50K lifecycle simulator (1 year)\n")
    js_top = []
    if len(oos_tr) > 50:
        model = EmpiricalTradeModel.from_trades(oos_tr.assign(risk_pts=oos_tr.risk_pts), point_value=mf.point_value,
                                                n_days=len(res.wf["oos_daily_r"]), cost_per_contract=mf.cost_rt, name=f"wf_oos_{a.tag}")
        md.append(f"Empirical model: {len(oos_tr):,} OOS trades, {model.trades_per_day:.2f} trades/day, net E[R] {model.expected_net_r():+.3f}.\n")
        md.append("| risk $/trade | net mean $ | net median $ | P(net>0) | pass rate/attempt |\n|---|---|---|---|---|")
        prog = get_program("topstep_50k")
        for risk in (200, 400, 600):
            s = simulate_lifecycle(prog, model, SimSizing(risk_dollars=risk), n_paths=3000, record_paths=False, seed=3)
            js_top.append({"risk": risk, **{k: s[k] for k in ("net_mean", "net_median", "p_net_positive", "pass_rate_per_attempt")}})
            md.append(f"| {risk} | {s['net_mean']:,.0f} | {s['net_median']:,.0f} | {s['p_net_positive']:.0%} | {s['pass_rate_per_attempt']:.0%} |")
    out = ROOT / "docs" / "results"
    (out / f"edge_search_{a.tag}.md").write_text("\n".join(md) + "\n")
    js = {"source": source, "n_configs": len(configs), "elapsed_s": res.elapsed_s, "pbo": res.pbo, "dsr_best": res.dsr_best,
          "wf": {k: v for k, v in res.wf.items() if k != "oos_daily_r"},
          "wf_equity": np.cumsum(res.wf["oos_daily_r"]).tolist(),
          "best": {"family": best.family, "params": best.params, "sharpe_is": best.sharpe_is, "sharpe_oos": best.sharpe_oos},
          "families": fam.to_dict(orient="records"),
          "leaderboard": lb.drop(columns=[]).to_dict(orient="records"), "topstep": js_top}
    (out / f"edge_search_{a.tag}.json").write_text(json.dumps(js, indent=1, default=float))
    print("\n".join(md))


if __name__ == "__main__":
    main()
