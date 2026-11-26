import numpy as np
import pytest

from qtengine.data import synthetic_bars
from qtengine.features import build_panel
from qtengine.prop import PRESET_MODELS, get_program
from qtengine.prop.fleet import CorrelatedModel, kelly_years_to_multiple, simulate_fleet, simulate_flywheel
from qtengine.prop.simulator import PayoutPolicy, SimSizing, simulate_lifecycle
from qtengine.research.engine import DEFAULT_SPACE, MarketFeatures, effective_trials, run_config, run_search, sample_configs
from qtengine.research.overfit import cscv_pbo
from qtengine.strategies import NoiseAreaMomentum
from qtengine.strategies.base import FeatureCache


@pytest.fixture(scope="module")
def mf():
    return MarketFeatures.build(build_panel(synthetic_bars(n_days=320, momentum=0.01, seed=5)), "MES")


def test_kernel_matches_reference_strategy(mf):
    cfg = dict(lookback=14, band_mult=1.0, first_dec=30, dec_every=30, last_entry=360, exit_min=389, stop_floor=0.5,
               trail_mode=0, target_r=0.0, max_entries=3, regime_filter=0, direction=0)
    tr = run_config(mf, "NAM", cfg)
    ref = NoiseAreaMomentum().generate(FeatureCache(mf.panel))
    assert len(tr) == len(ref)
    assert float((tr[:, 1] * (tr[:, 5] - tr[:, 4])).sum()) == pytest.approx(sum(t.pnl_pts for t in ref))


def test_all_families_run(mf):
    for fam in DEFAULT_SPACE:
        cfg = sample_configs({fam: DEFAULT_SPACE[fam]}, 1, seed=1)[0][1]
        tr = run_config(mf, fam, cfg)
        assert tr.shape[1] == 9 and (tr[:, 3] >= tr[:, 2]).all()


def test_pbo_detects_noise_and_signal():
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 1, (1600, 200))
    assert cscv_pbo(noise, max_combos=300)["pbo"] > 0.3
    sig = noise.copy()
    sig[:, 0] += 0.25           # one genuinely better strategy
    assert cscv_pbo(sig, max_combos=300)["pbo"] < 0.1


def test_effective_trials_counts_clusters():
    rng = np.random.default_rng(1)
    base = rng.normal(0, 1, (1000, 3))
    X = np.repeat(base, 50, axis=1) + 0.05 * rng.normal(0, 1, (1000, 150))
    assert 2.5 < effective_trials(X) < 4


def test_search_runs_end_to_end(mf):
    cfgs = sample_configs({"NAM": DEFAULT_SPACE["NAM"]}, 40, seed=2) + sample_configs({"ORB": DEFAULT_SPACE["ORB"]}, 20, seed=2)
    res = run_search(mf, cfgs, wf_train=126, wf_test=42)
    assert res.R.shape == (mf.panel.n_days, len(cfgs))
    assert res.wf["picks"] and 0 <= res.pbo["pbo"] <= 1


def test_payout_cushion_and_funded_risk_options():
    prog, m = get_program("topstep_50k"), PRESET_MODELS["S1_optimistic"]
    a = simulate_lifecycle(prog, m, SimSizing(risk_dollars=500), n_paths=800, record_paths=False, seed=1)
    b = simulate_lifecycle(prog, m, SimSizing(risk_dollars=500), n_paths=800, record_paths=False, seed=1,
                           payout_policy=PayoutPolicy(min_profit_to_request=10_000_000))
    assert b["payouts_mean"] == 0 and a["payouts_mean"] > 0
    c = simulate_lifecycle(prog, m, SimSizing(risk_dollars=500, funded_risk_dollars=250, up_frac=0.25), n_paths=300,
                           record_paths=False, seed=1)
    assert np.isfinite(c["net_mean"])


def test_correlated_model_correlation():
    cm = CorrelatedModel(PRESET_MODELS["S1_planning"], n_slots=2, n_paths=20000, rho=0.5)
    r = cm.sample(np.random.default_rng(0), 40000)[0]
    assert np.corrcoef(r[:20000], r[20000:])[0, 1] == pytest.approx(0.5, abs=0.05)


def test_fleet_and_flywheel_shapes():
    f = simulate_fleet(get_program("topstep_50k"), PRESET_MODELS["S1_planning"], n_slots=2, rho=1.0,
                       sizing=SimSizing(risk_dollars=400), horizon_days=252, n_paths=100)
    assert f["monthly_cash"].shape == (12, 100) and "1000000" in f["milestones"]
    w = simulate_flywheel(f["monthly_cash"], PRESET_MODELS["S1_planning"], 0.02)
    assert 1 in w["by_year"]


def test_kelly_growth_law():
    assert kelly_years_to_multiple(1.0, np.e, 1.0) == pytest.approx(2.0)
    assert kelly_years_to_multiple(2.0, 1000, 1.0) < kelly_years_to_multiple(1.0, 1000, 1.0)
