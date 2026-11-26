"""FastAPI service exposing the quant engine to the dashboard.

Run:  uvicorn qtengine.api.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
from __future__ import annotations

import asyncio
import io
import json
import math
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .. import store
from ..backtest import Sizing, _clean, run_backtest
from ..data import load_bars, synthetic_bars
from ..features import build_panel, day_type, vol_regime
from ..journal import TagConfig, tag_trades
from ..metrics import breakdown, daily_stats, drawdown, trade_stats
from ..prop import PRESET_MODELS, PropAccountTracker, SimGuard, SimSizing, TradeModel, get_program, load_presets, simulate_lifecycle
from ..risk import guard as guard_mod
from ..risk import ruin
from ..strategies import REGISTRY

ROOT = Path(__file__).resolve().parents[3]
app = FastAPI(title="Quantrader engine", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ----------------------------------------------------------------------------- schemas
class TradeModelIn(BaseModel):
    preset: str | None = "S1_planning"
    win_rate: float | None = None
    avg_win_r: float | None = None
    avg_loss_r: float | None = None
    trades_per_day: float | None = None
    stop_dollars: float | None = None
    cost_per_contract: float | None = None

    def build(self) -> TradeModel:
        base = PRESET_MODELS.get(self.preset or "S1_planning", TradeModel())
        kw = {k: v for k, v in self.model_dump().items() if k != "preset" and v is not None}
        if not kw:
            return base
        from dataclasses import replace
        return replace(base, name=f"{base.name}*", **kw)


class SimIn(BaseModel):
    program: str = "topstep_50k"
    model: TradeModelIn = Field(default_factory=TradeModelIn)
    risk_dollars: float = 300
    horizon_days: int = 252
    n_paths: int = Field(4000, le=20000)
    n_accounts: int = 1
    daily_stop_r: float | None = 2.0
    daily_profit_cap: float | None = None
    single_attempt: bool = False


class SweepIn(SimIn):
    risks: list[float] = [100, 150, 200, 300, 400, 500]


class RuinIn(BaseModel):
    daily_mean: float
    daily_sd: float
    target: float = 3000
    max_loss: float = 2000


class GuardIn(BaseModel):
    config: dict[str, Any] = {}
    state: dict[str, Any]


class BacktestIn(BaseModel):
    strategies: list[str] = ["S1"]
    symbol: str = "MES"
    days: int = Field(400, le=1500)
    momentum: float = 0.0
    seed: int = 0
    risk_dollars: float | None = 200


class TradeIn(BaseModel):
    date: str
    entry_time: str
    exit_time: str
    side: int
    pnl: float
    symbol: str = "MES"
    strategy: str | None = None
    contracts: int = 1
    entry: float | None = None
    exit: float | None = None
    stop: float | None = None
    risk_dollars: float | None = None
    r_net: float | None = None
    exit_reason: str | None = None
    notes: str | None = None
    source: str = "manual"


class AccountConfigIn(BaseModel):
    program: str = "topstep_50k"
    phase: str = "evaluation"
    start_date: str | None = None
    daily_target: float = 250
    guard: dict[str, Any] = {}


# ----------------------------------------------------------------------------- basics
@app.get("/api/health")
def health():
    return {"ok": True, "time": datetime.now().isoformat(timespec="seconds")}


@app.get("/api/presets")
def presets():
    return {k: v.to_dict() for k, v in load_presets().items()}


@app.get("/api/models")
def models():
    return {k: _clean(m.summary()) for k, m in PRESET_MODELS.items()}


@app.get("/api/economics")
def economics():
    p = ROOT / "docs" / "results" / "prop_economics.json"
    if not p.exists():
        raise HTTPException(404, "run engine/scripts/prop_economics.py first")
    return json.loads(p.read_text())


# ----------------------------------------------------------------------------- prop simulator
@app.post("/api/prop/simulate")
def prop_simulate(req: SimIn):
    prog = get_program(req.program)
    res = simulate_lifecycle(prog, req.model.build(), SimSizing(risk_dollars=req.risk_dollars),
                             SimGuard(daily_stop_r=req.daily_stop_r, daily_profit_cap=req.daily_profit_cap),
                             horizon_days=req.horizon_days, n_paths=req.n_paths, n_accounts=req.n_accounts,
                             single_attempt=req.single_attempt)
    return _clean(res)


@app.post("/api/prop/sweep")
def prop_sweep(req: SweepIn):
    prog = get_program(req.program)
    model = req.model.build()
    rows = []
    for r in req.risks:
        res = simulate_lifecycle(prog, model, SimSizing(risk_dollars=r), SimGuard(daily_stop_r=req.daily_stop_r),
                                 horizon_days=req.horizon_days, n_paths=min(req.n_paths, 4000), record_paths=False)
        rows.append({"risk_dollars": r, **{k: res[k] for k in ("net_mean", "net_median", "net_p05", "net_p95", "p_net_positive",
                                                               "p_any_payout", "pass_rate_per_attempt")}})
    return _clean({"program": req.program, "model": model.summary(), "rows": rows})


# ----------------------------------------------------------------------------- risk
@app.post("/api/risk/ruin")
def risk_ruin(req: RuinIn):
    mu, sd = req.daily_mean, req.daily_sd
    return _clean({
        "p_target_before_static_ruin": ruin.bm_prob_target_before_ruin(mu, sd, req.target, req.max_loss),
        "p_reach_lock_before_trailing_breach": ruin.prob_reach_lock_before_trailing_breach(mu, sd, req.max_loss, req.max_loss),
        "p_ruin_infinite_static": ruin.bm_prob_ruin_infinite(mu, sd, req.max_loss),
        "expected_days_to_drawdown": ruin.expected_time_to_trailing_breach(mu, sd, req.max_loss),
        "expected_days_to_target_drift_only": req.target / mu if mu > 0 else None,
    })


@app.post("/api/risk/guard")
def risk_guard(req: GuardIn):
    cfg = guard_mod.GuardConfig(**req.config)
    st = guard_mod.GuardState(**req.state)
    return guard_mod.evaluate(cfg, st).to_dict()


# ----------------------------------------------------------------------------- backtest
@lru_cache(maxsize=16)
def _synthetic(days: int, momentum: float, seed: int):
    end = pd.Timestamp.today().normalize() - pd.offsets.BDay(1)
    start = end - pd.offsets.BDay(days - 1)
    return build_panel(synthetic_bars(n_days=days, momentum=momentum, seed=seed, start=str(start.date())))


def _bt_payload(res, panel) -> dict:
    out = res.to_dict()
    eq = res.equity.to_numpy()
    out["drawdown"] = [{"date": str(d.date()), "dd": float(x)} for d, x in zip(res.daily.index, drawdown(eq))]
    t = res.trades
    if len(t):
        t = t.copy()
        t["hour"] = t["entry_time"].str[:2] + ":00"
        t["weekday"] = pd.to_datetime(t["date"]).dt.day_name()
        out["by_hour"] = _clean(breakdown(t, "hour").to_dict(orient="records"))
        out["by_weekday"] = _clean(breakdown(t, "weekday").to_dict(orient="records"))
        out["by_exit"] = _clean(breakdown(t, "exit_reason").to_dict(orient="records"))
        out["by_strategy"] = _clean(breakdown(t, "strategy").to_dict(orient="records"))
        r = t["r_net"].to_numpy()
        out["r_hist"] = np.histogram(np.clip(r, -2, 6), bins=32, range=(-2, 6))[0].tolist()
    return out


@app.post("/api/backtest/synthetic")
def backtest_synthetic(req: BacktestIn):
    panel = _synthetic(req.days, req.momentum, req.seed)
    strats = [REGISTRY[s]() for s in req.strategies]
    sizing = Sizing(mode="risk", risk_dollars=req.risk_dollars) if req.risk_dollars else Sizing()
    res = run_backtest(panel, strats, req.symbol, sizing)
    out = _bt_payload(res, panel)
    out["data_source"] = f"SYNTHETIC (momentum={req.momentum}, seed={req.seed}) — pipeline demo, proves nothing about real markets"
    return out


@app.post("/api/backtest/upload")
async def backtest_upload(file: UploadFile = File(...), strategies: str = "S1", symbol: str = "MES",
                          risk_dollars: float = 200, tz: str = "UTC"):
    raw = await file.read()
    tmp = ROOT / "data" / "uploads"
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / Path(file.filename or "bars.csv").name
    path.write_bytes(raw)
    df = load_bars(path, tz_in=tz)
    panel = build_panel(df)
    res = run_backtest(panel, [REGISTRY[s]() for s in strategies.split(",")], symbol, Sizing(mode="risk", risk_dollars=risk_dollars))
    out = _bt_payload(res, panel)
    out["data_source"] = f"uploaded: {path.name}"
    return out


# ----------------------------------------------------------------------------- journal
@app.get("/api/journal/trades")
def journal_trades(account: str = "main"):
    return store.list_trades(account)


@app.post("/api/journal/trades")
def journal_add(trades: list[TradeIn], account: str = "main"):
    rows = [{**t.model_dump(), "account": account} for t in trades]
    n = store.insert_trades(rows)
    return {"inserted": n}


@app.delete("/api/journal/trades")
def journal_clear(account: str = "main", source: str | None = None):
    store.clear_trades(account, source)
    return {"ok": True}


def _journal_frame(account: str) -> pd.DataFrame:
    rows = store.list_trades(account)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    cfg = store.get_config("account", {})
    g = cfg.get("guard", {})
    tagged = tag_trades(df.drop(columns=["tags"]), TagConfig(
        planned_risk=g.get("planned_risk", 200), internal_daily_stop=g.get("internal_daily_stop", 400),
        max_trades_per_day=g.get("max_trades_per_day", 4)))
    return tagged


@app.get("/api/journal/analytics")
def journal_analytics(account: str = "main"):
    t = _journal_frame(account)
    if t.empty:
        return {"empty": True}
    t["r_net"] = t["r_net"].fillna(t["pnl"] / t["risk_dollars"].replace(0, np.nan))
    daily = t.groupby(t["date"].dt.date)["pnl"].sum()
    out = {
        "trades": trade_stats(t["pnl"].to_numpy(), t["r_net"].dropna().to_numpy()),
        "daily": daily_stats(daily),
        "equity": [{"date": str(d), "pnl": float(v), "equity": float(e)} for d, v, e in zip(daily.index, daily.values, daily.cumsum().values)],
        "drawdown": [{"date": str(d), "dd": float(x)} for d, x in zip(daily.index, drawdown(daily.cumsum().to_numpy()))],
        "by_session": breakdown(t.assign(session=t["tags"].map(lambda x: next((s for s in x if s.startswith("session:")), "?"))), "session").to_dict(orient="records"),
        "by_strategy": breakdown(t.fillna({"strategy": "?"}), "strategy").to_dict(orient="records"),
        "by_tag": breakdown(t.explode("tags"), "tags").sort_values("total").to_dict(orient="records"),
        "rolling_expectancy": [{"i": int(i), "exp": float(v)} for i, v in t["pnl"].rolling(30).mean().dropna().items()],
        "recent": t.tail(50).assign(date=lambda x: x["date"].dt.strftime("%Y-%m-%d")).to_dict(orient="records"),
    }
    return _clean(out)


# ----------------------------------------------------------------------------- account / risk dashboard
@app.get("/api/account/config")
def account_config_get():
    return store.get_config("account", AccountConfigIn().model_dump())


@app.post("/api/account/config")
def account_config_set(cfg: AccountConfigIn):
    get_program(cfg.program)
    store.set_config("account", cfg.model_dump())
    return cfg


@app.get("/api/account/status")
def account_status(account: str = "main"):
    cfg = AccountConfigIn(**store.get_config("account", {}))
    prog = get_program(cfg.program)
    t = _journal_frame(account)
    tracker = PropAccountTracker(prog, phase=cfg.phase)
    events = []
    daily = pd.Series(dtype=float)
    if not t.empty:
        if cfg.start_date:
            t = t[t["date"] >= pd.Timestamp(cfg.start_date)]
        daily = t.groupby(t["date"].dt.date)["pnl"].sum()
        for d, v in daily.items():
            day_tr = t[t["date"].dt.date == d]
            low = min(0.0, day_tr["pnl"].cumsum().min())
            o = tracker.apply_day(float(v), intraday_low=float(low))
            if o["events"]:
                events.append({"date": str(d), "events": o["events"]})
            if tracker.state.status == "passed":
                tracker.promote_to_funded()
                events.append({"date": str(d), "events": ["promoted to funded (simulated)"]})
            if tracker.state.status == "failed":
                break
    st = tracker.status()
    rules = tracker.rules
    # forward-looking risk of ruin from the empirical daily P&L distribution
    ror = None
    if len(daily) >= 15:
        x = daily.to_numpy()
        buffer = st["buffer_to_mll"]
        trailing = not st["trailing_locked"] and rules.drawdown_type != "static"
        lock_gain = None
        if trailing and rules.lock_level is not None:
            lock_gain = rules.lock_level - tracker.state.mll  # HWM gain needed before the MLL locks
        ror = {
            "p_breach_20d": ruin.monte_carlo_ruin(x, buffer, horizon=20, n_paths=5000, trailing=trailing, lock_gain=lock_gain)["p_ruin"],
            "p_breach_60d": ruin.monte_carlo_ruin(x, buffer, horizon=60, n_paths=5000, trailing=trailing, lock_gain=lock_gain)["p_ruin"],
            "lundberg_bound": ruin.lundberg_ruin_bound(x, buffer),
            "daily_mean": float(x.mean()), "daily_sd": float(x.std(ddof=1)),
        }
        if rules.profit_target and tracker.state.phase == "evaluation":
            ror["p_pass_before_fail"] = ruin.monte_carlo_ruin(x, buffer, target=max(rules.profit_target - tracker.state.profit, 1),
                                                              horizon=250, n_paths=4000, trailing=trailing, lock_gain=lock_gain)["p_target_first"]
    today = daily.iloc[-1] if len(daily) else 0.0
    g = guard_mod.GuardConfig(**{k: v for k, v in cfg.guard.items() if k in guard_mod.GuardConfig.__dataclass_fields__})
    g.firm_daily_loss_limit = rules.daily_loss_limit
    decision = guard_mod.evaluate(g, guard_mod.GuardState(
        now=datetime.now().strftime("%H:%M"), day_pnl=float(today), day_peak_pnl=max(float(today), 0.0),
        trades_today=0, consecutive_losses=0, minutes_since_last_loss=None,
        equity=tracker.state.profit, mll_level=tracker.state.mll))
    return _clean({"program": prog.to_dict(), "config": cfg.model_dump(), "status": st, "events": events,
                   "risk_of_ruin": ror, "guard": decision.to_dict(), "daily_target": cfg.daily_target,
                   "last_day": str(daily.index[-1]) if len(daily) else None, "last_day_pnl": float(today)})


@app.post("/api/demo/seed")
def demo_seed(days: int = 320, momentum: float = 0.01, seed: int = 4):
    """Fill the journal with SYNTHETIC S1+S2 trades so the dashboard has data. Clearly flagged."""
    store.clear_trades("main", "demo-synthetic")
    panel = _synthetic(days, momentum, seed)
    res = run_backtest(panel, [REGISTRY["S1"](), REGISTRY["S2"]()], "MES", Sizing(mode="risk", risk_dollars=200))
    t = res.trades
    rows = [{"source": "demo-synthetic", "date": str(r.date.date()), "entry_time": r.entry_time, "exit_time": r.exit_time,
             "symbol": "MES", "strategy": r.strategy, "side": int(r.side), "contracts": int(r.contracts), "entry": float(r.entry),
             "exit": float(r.exit), "stop": float(r.stop), "risk_dollars": float(r.risk_dollars), "pnl": float(r.pnl),
             "r_net": float(r.r_net), "exit_reason": r.exit_reason, "mae_r": float(r.mae_r), "mfe_r": float(r.mfe_r)}
            for r in t.itertuples()]
    store.insert_trades(rows)
    start = str(pd.Timestamp(rows[-1]["date"]) - pd.offsets.BDay(35))[:10] if rows else None
    store.set_config("account", AccountConfigIn(program="topstep_50k", phase="evaluation", start_date=start).model_dump())
    return {"inserted": len(rows), "start_date": start, "warning": "synthetic demo data"}


# ----------------------------------------------------------------------------- live (demo stream)
@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    """Demo stream of intraday P&L + guard decisions. In production the execution adapter
    publishes fills/positions to Redis and this endpoint relays them."""
    await ws.accept()
    rng = np.random.default_rng()
    pnl, peak, trades, consec = 0.0, 0.0, 0, 0
    cfg = guard_mod.GuardConfig()
    try:
        while True:
            pnl += rng.normal(0.4, 18.0)
            peak = max(peak, pnl)
            if rng.random() < 0.01:
                trades += 1
            st = guard_mod.GuardState(now=datetime.now().strftime("%H:%M"), day_pnl=pnl, day_peak_pnl=peak, trades_today=trades,
                                      consecutive_losses=consec, minutes_since_last_loss=None, equity=500 + pnl, mll_level=-1500)
            d = guard_mod.evaluate(cfg, st)
            await ws.send_json({"ts": datetime.now().isoformat(timespec="seconds"), "demo": True, "day_pnl": round(pnl, 2),
                                "peak": round(peak, 2), "trades": trades, "guard": d.to_dict()})
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        return
