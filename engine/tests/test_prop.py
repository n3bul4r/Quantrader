import pytest

from qtengine.prop import PRESET_MODELS, PropAccountTracker, SimSizing, get_program, load_presets, simulate_lifecycle
from qtengine.prop.simulator import TradeModel


def test_presets_load():
    presets = load_presets()
    assert {"topstep_50k", "apex_50k_eod", "topstep_50k_static_labs"} <= set(presets)
    t = presets["topstep_50k"]
    assert t.evaluation.profit_target == 3000 and t.evaluation.max_loss == 2000
    assert t.funded.max_micros_at(0) == 20 and t.funded.max_micros_at(2500) == 50


def test_tracker_eod_trailing_and_lock():
    acc = PropAccountTracker(get_program("topstep_50k"))
    acc.apply_day(1000)
    assert acc.state.mll == pytest.approx(-1000)
    acc.apply_day(1500)
    assert acc.state.mll == pytest.approx(0.0)       # locked at starting balance
    acc.apply_day(-200)
    assert acc.state.mll == pytest.approx(0.0)
    assert acc.status()["buffer_to_mll"] == pytest.approx(2300)


def test_tracker_consistency_blocks_pass():
    acc = PropAccountTracker(get_program("topstep_50k"))
    acc.apply_day(2000)
    out = acc.apply_day(1000)                         # total 3000 but best day 2000 > 50%
    assert out["status"] == "active"
    assert acc.max_profit_today_consistent() == pytest.approx(3000)
    acc.apply_day(1000)                               # total 4000, best 2000 = 50%
    assert acc.state.status == "passed"


def test_tracker_intraday_breach_fails():
    acc = PropAccountTracker(get_program("topstep_50k"))
    out = acc.apply_day(-100, intraday_low=-2100)
    assert out["status"] == "failed"


def test_tracker_payout_flow():
    acc = PropAccountTracker(get_program("topstep_50k"), phase="funded")
    for _ in range(5):
        acc.apply_day(400)
    ok, amount, why = acc.payout_eligible()
    assert ok, why
    assert amount == pytest.approx(1000)              # 50% of 2000
    acc.take_payout()
    assert acc.state.profit == pytest.approx(1000)
    assert acc.state.mll == pytest.approx(0.0)


def test_zero_edge_loses_money_in_expectation():
    res = simulate_lifecycle(get_program("topstep_50k"), PRESET_MODELS["zero_edge"], SimSizing(risk_dollars=300),
                             n_paths=3000, record_paths=False)
    assert res["net_mean"] < 0


def test_more_edge_more_money():
    prog = get_program("topstep_50k")
    lo = simulate_lifecycle(prog, PRESET_MODELS["S1_planning"], SimSizing(risk_dollars=300), n_paths=3000, record_paths=False)
    hi = simulate_lifecycle(prog, PRESET_MODELS["S1_optimistic"], SimSizing(risk_dollars=300), n_paths=3000, record_paths=False)
    assert hi["net_mean"] > lo["net_mean"]
    assert hi["pass_rate_per_attempt"] > lo["pass_rate_per_attempt"]


def test_single_attempt_probabilities_sum_to_one():
    res = simulate_lifecycle(get_program("apex_50k_eod"), TradeModel(), SimSizing(risk_dollars=250),
                             single_attempt=True, n_paths=2000)
    assert res["p_pass"] + res["p_fail"] + res["p_unresolved"] == pytest.approx(1.0)
