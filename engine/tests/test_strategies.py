import numpy as np
import pandas as pd
import pytest

from qtengine.backtest import Sizing, run_backtest
from qtengine.data import synthetic_bars
from qtengine.features import build_panel, noise_sigma, session_vwap
from qtengine.journal import TagConfig, tag_trades
from qtengine.metrics import deflated_sharpe, min_track_record_length, probabilistic_sharpe
from qtengine.strategies import LateDayMomentum, NoiseAreaMomentum, VwapReversion
from qtengine.validation import bootstrap_ci, sign_flip_pvalue


@pytest.fixture(scope="module")
def noise_panel():
    return build_panel(synthetic_bars(n_days=260, momentum=0.0, seed=11))


@pytest.fixture(scope="module")
def trend_panel():
    return build_panel(synthetic_bars(n_days=260, momentum=0.06, seed=12))


def test_panel_shape(noise_panel):
    assert noise_panel.close.shape == (260, 390)


def test_noise_sigma_has_no_lookahead(noise_panel):
    sig = noise_sigma(noise_panel, 14)
    assert np.isnan(sig[:14]).all()
    p2 = build_panel(synthetic_bars(n_days=260, momentum=0.0, seed=11))
    p2.close[100:] *= 1.5   # change the future
    sig2 = noise_sigma(p2, 14)
    np.testing.assert_allclose(sig[:101], sig2[:101])


def test_vwap_within_bar_range(noise_panel):
    vwap, sd = session_vwap(noise_panel)
    lo = np.minimum.accumulate(noise_panel.low, axis=1)
    hi = np.maximum.accumulate(noise_panel.high, axis=1)
    assert (vwap >= lo - 1e-9).all() and (vwap <= hi + 1e-9).all() and (sd >= 0).all()


@pytest.mark.parametrize("strat", [NoiseAreaMomentum(), LateDayMomentum(high_vol_only=False), VwapReversion(low_vol_only=False)])
def test_strategies_flat_by_close_and_stops_valid(noise_panel, strat):
    res = run_backtest(noise_panel, [strat], "MES")
    t = res.trades
    assert len(t) > 0
    assert (t.exit_min <= 389).all()
    assert (t.risk_pts > 0).all()
    assert (t.entry_min < t.exit_min).all() or (t.exit_reason == "reverse").any()


def test_s1_has_no_edge_on_martingale_but_finds_injected_momentum(noise_panel, trend_panel):
    flat = run_backtest(noise_panel, [NoiseAreaMomentum()], "MES").summary["trades"]
    trend = run_backtest(trend_panel, [NoiseAreaMomentum()], "MES").summary["trades"]
    # on a martingale the net expectancy is not significantly positive
    assert flat["t_stat"] < 2.5
    assert trend["expectancy_r"] > flat["expectancy_r"]
    assert trend["t_stat"] > 2.0


def test_risk_sizing_mode(noise_panel):
    res = run_backtest(noise_panel, [NoiseAreaMomentum()], "MES", sizing=Sizing(mode="risk", risk_dollars=250))
    t = res.trades
    assert (t.risk_dollars <= 250 * 1.25 + 1e-6).all()


def test_psr_dsr_sanity():
    assert probabilistic_sharpe(0.1, 500, 0.0, 3.0) > 0.95
    assert probabilistic_sharpe(0.0, 500, 0.0, 3.0) == pytest.approx(0.5)
    # with many trials the same SR is much less convincing
    assert deflated_sharpe(0.1, 500, 0.0, 3.0, n_trials=200, var_sr=0.002) < probabilistic_sharpe(0.1, 500, 0.0, 3.0)
    assert min_track_record_length(0.05, 0, 3) > min_track_record_length(0.1, 0, 3)


def test_sign_flip_and_bootstrap():
    rng = np.random.default_rng(0)
    skilled = np.abs(rng.normal(0, 1, 400)) * np.where(rng.random(400) < 0.6, 1, -1)
    assert sign_flip_pvalue(skilled, 0.0, n_perm=3000) < 0.01
    lo, hi = bootstrap_ci(rng.normal(0.2, 1, 500))
    assert lo < 0.2 < hi


def test_journal_tags_behaviour():
    trades = pd.DataFrame([
        {"date": "2026-11-02", "entry_time": "09:45", "exit_time": "10:05", "side": 1, "pnl": -250, "risk_dollars": 200, "strategy": "S1"},
        {"date": "2026-11-02", "entry_time": "10:10", "exit_time": "10:30", "side": -1, "pnl": -200, "risk_dollars": 400, "strategy": "S1"},
        {"date": "2026-11-02", "entry_time": "14:01", "exit_time": "15:30", "side": 1, "pnl": 300, "risk_dollars": 200, "strategy": "S1"},
    ])
    out = tag_trades(trades, TagConfig(events=[("2026-11-02", "14:00", "FOMC")]))
    assert "behaviour:possible_revenge" in out.loc[1, "tags"]
    assert "violation:oversized" in out.loc[1, "tags"]
    assert "violation:after_daily_stop" in out.loc[2, "tags"]
    assert "news:FOMC" in out.loc[2, "tags"]
    assert "session:open_drive" in out.loc[0, "tags"]
