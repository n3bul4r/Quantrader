import pytest

from qtengine.growth import SCENARIOS, future_value, months_to_target, simulate_growth


def test_future_value_closed_form():
    assert future_value(500, 100, 0.0, 10) == pytest.approx(12_500)
    assert future_value(500, 100, 0.07, 10) == pytest.approx(18_089, rel=1e-3)
    assert months_to_target(500, 100, 0.0, 1_700) == 12


def test_cash_equals_contributions():
    r = simulate_growth(SCENARIOS["cash"], 500, 100, years=3, n_paths=50, checkpoints=(1, 3))
    c1, c3 = r["checkpoints"]
    assert c1["contributed_eur"] == pytest.approx(1_700) and c1["median"] == pytest.approx(1_700)
    assert c3["contributed_eur"] == pytest.approx(4_100)


def test_etf_mean_matches_closed_form():
    r = simulate_growth(SCENARIOS["etf"], 500, 100, years=5, n_paths=6000, checkpoints=(5,))
    assert r["checkpoints"][0]["mean"] == pytest.approx(future_value(500, 100, 0.07, 5), rel=0.03)


def test_no_edge_trading_loses_to_costs():
    r = simulate_growth(SCENARIOS["no_edge_cfd_1pct"], 500, 100, years=3, n_paths=1000, checkpoints=(3,))
    c = r["checkpoints"][0]
    assert c["median"] < c["contributed_eur"]


def test_mes_cannot_be_sized_on_a_small_account():
    r = simulate_growth(SCENARIOS["s1_plan_mes_1pct"], 500, 100, years=1, n_paths=200, checkpoints=(1,))
    assert r["checkpoints"][0]["share_of_days_traded"] < 0.01
    r2 = simulate_growth(SCENARIOS["s1_plan_cfd_1pct"], 500, 100, years=1, n_paths=200, checkpoints=(1,))
    assert r2["checkpoints"][0]["share_of_days_traded"] > 0.4


def test_tax_reduces_trading_outcome():
    a = simulate_growth(SCENARIOS["s1_opt_cfd_1pct"], 500, 100, years=3, n_paths=1000, seed=3, checkpoints=(3,))
    b = simulate_growth(SCENARIOS["s1_opt_cfd_1pct"], 500, 100, years=3, n_paths=1000, seed=3, checkpoints=(3,), tax_rate=0.3)
    assert b["checkpoints"][0]["median"] < a["checkpoints"][0]["median"]
    assert b["checkpoints"][0]["taxes_paid_mean"] > 0
