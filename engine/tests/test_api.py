import os
import tempfile

os.environ["QT_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")

from fastapi.testclient import TestClient  # noqa: E402

from qtengine.api.main import app  # noqa: E402

c = TestClient(app)


def test_health_and_presets():
    assert c.get("/api/health").json()["ok"]
    assert "topstep_50k" in c.get("/api/presets").json()
    assert "S1_planning" in c.get("/api/models").json()


def test_simulate_and_ruin_and_guard():
    r = c.post("/api/prop/simulate", json={"program": "topstep_50k", "risk_dollars": 300, "n_paths": 500, "horizon_days": 60})
    assert r.status_code == 200 and "net_mean" in r.json() and "cash_fan" in r.json()
    r = c.post("/api/risk/ruin", json={"daily_mean": 0, "daily_sd": 250})
    assert abs(r.json()["p_target_before_static_ruin"] - 0.4) < 1e-9
    r = c.post("/api/risk/guard", json={"state": {"now": "10:00", "day_pnl": -500, "day_peak_pnl": 0, "trades_today": 1,
                                                  "consecutive_losses": 1, "minutes_since_last_loss": 20, "equity": 0, "mll_level": -2000}})
    assert r.json()["allow_new_trade"] is False


def test_backtest_and_demo_flow():
    r = c.post("/api/backtest/synthetic", json={"strategies": ["S1"], "days": 120})
    assert r.status_code == 200 and "SYNTHETIC" in r.json()["data_source"]
    assert c.post("/api/demo/seed?days=150").json()["inserted"] > 0
    a = c.get("/api/journal/analytics").json()
    assert a["trades"]["n"] > 0 and a["by_session"]
    s = c.get("/api/account/status").json()
    assert "buffer_to_mll" in s["status"] and "guard" in s
