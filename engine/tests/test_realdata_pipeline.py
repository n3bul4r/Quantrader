import numpy as np
import pandas as pd
import pytest

from qtengine.data import load_bars, synthetic_bars
from qtengine.features import build_session_panel, market_panel
from qtengine.prop import PRESET_MODELS, get_program
from qtengine.prop.empirical import MarketTradeLog, SlotDayModel, slot_assignment
from qtengine.prop.fleet import simulate_bootstrap
from qtengine.prop.simulator import SimSizing
from qtengine.research.engine import DEFAULT_SPACE, MarketFeatures, run_config, sample_configs


def test_loaders_dukascopy_and_databento(tmp_path):
    df = synthetic_bars(n_days=3, seed=1).tz_convert("UTC").iloc[:300]
    pd.DataFrame({"Gmt time": df.index.strftime("%d.%m.%Y %H:%M:%S.000"), "Open": df.open, "High": df.high,
                  "Low": df.low, "Close": df.close, "Volume": df.volume}).to_csv(tmp_path / "d.csv", index=False)
    a = load_bars(tmp_path / "d.csv")
    assert a.index[0].hour == 9 and a.index[0].minute == 30 and len(a) == 300
    ns = (df.index.as_unit("ns").asi8)
    pd.DataFrame({"ts_event": ns, "open": df.open.values, "high": df.high.values, "low": df.low.values,
                  "close": df.close.values, "volume": df.volume.values, "symbol": "MESH6"}).to_csv(tmp_path / "b.csv", index=False)
    b = load_bars(tmp_path / "b.csv")
    assert b.index[0] == a.index[0]


def test_session_panels_and_clamping():
    df = synthetic_bars(n_days=40, seed=2)
    p = build_session_panel(df, "09:30", 310)
    assert p.close.shape == (40, 310)
    mf = MarketFeatures.build(p, "MGC")
    for fam in DEFAULT_SPACE:
        for _, c in sample_configs({fam: DEFAULT_SPACE[fam]}, 5, seed=1):
            tr = run_config(mf, fam, c)
            assert (tr[:, 3] <= 309).all()
    with pytest.raises(ValueError):
        market_panel(df, "MGC")   # synthetic data has no 08:20 gold session


def _logs(n_days=60):
    rng = np.random.default_rng(0)
    out = {}
    for mk in ("MES", "MGC"):
        days = np.sort(rng.integers(0, n_days, 80))
        out[mk] = MarketTradeLog(mk, pd.DataFrame({"day": days, "entry_min": rng.integers(30, 300, 80),
                                                   "r_gross": rng.normal(0.1, 1.2, 80), "mae_r": rng.uniform(0, 1, 80),
                                                   "mfe_r": rng.uniform(0, 2, 80), "risk_pts": rng.uniform(5, 20, 80)}))
    return out


def test_slot_day_model_replays_same_day_across_slots():
    logs = _logs()
    m = SlotDayModel(logs, 60, slot_assignment(["MES", "MGC"], 2, "all"), n_paths=50)
    n = m.n_trades(None, 100)
    assert n.shape == (100,) and (n[:50] == n[50:]).all()     # both slots see the same historical day
    r, mae, mfe, stop = m.sample(None, 100)
    assert r.shape == (100,) and (stop > 0).all()
    assert slot_assignment(["MES", "MNQ", "MGC"], 3, "leave_one_out") == [["MGC", "MNQ"], ["MES", "MNQ"], ["MES", "MGC"]]


def test_bootstrap_with_slot_model_runs():
    logs = _logs()
    sm = SlotDayModel(logs, 60, slot_assignment(["MES", "MGC"], 2, "all"), n_paths=60)
    r = simulate_bootstrap(get_program("topstep_50k"), PRESET_MODELS["basket_planning"], 348, max_slots=2,
                           sizing=SimSizing(risk_dollars=300), horizon_days=126, n_paths=60, slot_model=sm,
                           monthly_topup=116, return_monthly=True)
    assert r["monthly_cash"].shape == (6, 60)
