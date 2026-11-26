"""Compare sizing / guard policies (SYSTEM_DESIGN §2.4). Topstep 50K, S1 planning edge on MES+MNQ, 2 years."""
from dataclasses import replace

from qtengine.prop import PRESET_MODELS, SimGuard, SimSizing, get_program, simulate_lifecycle

prog = get_program("topstep_50k")
m = replace(PRESET_MODELS["S1_planning"], name="S1_planning_MES+MNQ", trades_per_day=1.4, max_trades_per_day=4)
CASES = [
    ("fixed $500, daily stop 2R", SimSizing(risk_dollars=500), SimGuard()),
    ("fixed $500, daily stop 3R", SimSizing(risk_dollars=500), SimGuard(daily_stop_r=3.0)),
    ("fixed $500, daily stop 1R", SimSizing(risk_dollars=500), SimGuard(daily_stop_r=1.0)),
    ("fixed $500, no profit cap", SimSizing(risk_dollars=500), SimGuard(auto_profit_cap=False)),
    ("buffer 25% [150,700]", SimSizing(mode="buffer", fraction=0.25, min_risk=150, max_risk=700), SimGuard()),
    ("buffer 20% [150,600]", SimSizing(mode="buffer", fraction=0.20, min_risk=150, max_risk=600), SimGuard()),
]
if __name__ == "__main__":
    print("| policy | net mean | net median | p05 | P(net>0) | evaluations bought |\n|---|---|---|---|---|---|")
    for label, sz, g in CASES:
        r = simulate_lifecycle(prog, m, sz, g, horizon_days=504, n_paths=4000, record_paths=False, seed=11)
        print(f"| {label} | {r['net_mean']:,.0f} | {r['net_median']:,.0f} | {r['net_p05']:,.0f} | {r['p_net_positive']:.0%} | {r['evals_bought_mean']:.1f} |")
