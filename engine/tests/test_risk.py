import math

import numpy as np
import pytest

from qtengine.instruments import cost_report, get_instrument
from qtengine.risk import guard, ruin, sizing


def test_bm_target_before_ruin_zero_drift_is_gamblers_ruin():
    assert ruin.bm_prob_target_before_ruin(0.0, 1.0, 3000, 2000) == pytest.approx(0.4)


def test_bm_target_before_ruin_matches_monte_carlo():
    mu, sigma = 10.0, 150.0  # $/day
    analytic = ruin.bm_prob_target_before_ruin(mu, sigma, 3000, 2000)
    rng = np.random.default_rng(1)
    mc = ruin.monte_carlo_ruin(rng.normal(mu, sigma, 200_000), ruin=2000, target=3000, horizon=3000, n_paths=4000)
    assert mc["p_target_first"] == pytest.approx(analytic, abs=0.03)


def test_trailing_lock_probability_zero_edge_is_one_over_e():
    assert ruin.prob_reach_lock_before_trailing_breach(0.0, 1.0, 2000, 2000) == pytest.approx(math.exp(-1))


def test_trailing_lock_probability_matches_monte_carlo():
    mu, sigma, dd = 5.0, 120.0, 2000.0
    analytic = ruin.prob_reach_lock_before_trailing_breach(mu, sigma, dd, dd)
    rng = np.random.default_rng(2)
    x = rng.normal(mu, sigma, 300_000)
    mc = ruin.monte_carlo_ruin(x, ruin=dd, target=dd, horizon=6000, n_paths=4000, trailing=True)
    # target=dd with trailing floor == reaching the lock before the trailing breach
    assert mc["p_target_first"] == pytest.approx(analytic, abs=0.04)


def test_lundberg_bound_is_conservative():
    rng = np.random.default_rng(3)
    x = rng.normal(20, 200, 100_000)
    bound = ruin.lundberg_ruin_bound(x, 1500)
    mc = ruin.monte_carlo_ruin(x, ruin=1500, horizon=3000, n_paths=3000)["p_ruin"]
    assert mc <= bound + 0.02
    assert ruin.lundberg_ruin_bound(rng.normal(-1, 10, 1000), 100) == 1.0


def test_kelly_simple_bet():
    # +1 / -1 with p = 0.6  -> f* = 2p - 1 = 0.2
    r = np.array([1.0] * 60 + [-1.0] * 40)
    assert sizing.kelly_fraction_r(r) == pytest.approx(0.2, abs=1e-3)


def test_contracts_for_risk_respects_costs_and_rounding():
    mes = get_instrument("MES")
    assert sizing.contracts_for_risk(250, 20, mes) == 2       # (100 + 3.9) per contract
    assert sizing.contracts_for_risk(90, 20, mes) == 1        # rounds up within tolerance
    assert sizing.contracts_for_risk(50, 20, mes) == 0


def test_buffer_sizer_defensive_and_dll_caps():
    s = sizing.BufferSizer(fraction=0.1, initial_buffer=2000)
    assert s.risk_dollars(2000) == pytest.approx(200)
    assert s.risk_dollars(800) == pytest.approx(75)           # defensive halving, then min floor
    assert s.risk_dollars(2000, daily_remaining=100) == pytest.approx(80)


def test_scaling_policy_requires_evidence():
    pol = sizing.ScalingPolicy()
    tier, why = pol.evaluate(0, 3000, np.zeros(10))
    assert tier == 0 and "evidence" in why
    rng = np.random.default_rng(0)
    good = rng.normal(0.4, 1.0, 60)
    tier, why = pol.evaluate(0, 3000, good)
    assert tier == 1, why
    tier, why = pol.evaluate(2, 2000, good)
    assert tier == 1 and "down" in why


def test_guard_blocks_after_daily_stop_and_flags_profit_cap():
    cfg = guard.GuardConfig()
    st = guard.GuardState(now="11:00", day_pnl=-450, day_peak_pnl=0, trades_today=2, consecutive_losses=2,
                          minutes_since_last_loss=30, equity=1500, mll_level=-2000)
    d = guard.evaluate(cfg, st)
    assert not d.allow_new_trade and d.flatten_now
    st2 = guard.GuardState(now="11:00", day_pnl=1300, day_peak_pnl=1300, trades_today=2, consecutive_losses=0,
                           minutes_since_last_loss=None, equity=3000, mll_level=0)
    d2 = guard.evaluate(cfg, st2)
    assert not d2.allow_new_trade and any("profit cap" in r for r in d2.reasons)
    st3 = guard.GuardState(now="11:00", day_pnl=0, day_peak_pnl=0, trades_today=0, consecutive_losses=0,
                           minutes_since_last_loss=None, equity=0, mll_level=-2000)
    d3 = guard.evaluate(cfg, st3)
    assert d3.allow_new_trade and 0 < d3.max_risk_dollars <= 400


def test_cost_report_breakeven():
    rep = cost_report("MES", stop_points=2, target_points=2)   # 8-tick scalp
    assert rep.cost_as_frac_of_risk > 0.3
    assert rep.breakeven_winrate_net > 0.6
