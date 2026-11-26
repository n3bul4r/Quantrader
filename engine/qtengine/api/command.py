"""Command-center endpoints: background research jobs, fleet simulation, multi-account board."""
from __future__ import annotations

import json
import math
import threading
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import store
from ..backtest import Sizing, _clean, run_backtest
from ..data import load_bars, synthetic_bars
from ..features import build_panel
from ..prop import PRESET_MODELS, PropAccountTracker, get_program
from ..prop.fleet import MILESTONES, simulate_fleet
from ..prop.simulator import PayoutPolicy, SimSizing
from ..research.engine import (DEFAULT_SPACE, MarketFeatures, family_summary, run_search, sample_configs)
from ..strategies import REGISTRY

ROOT = Path(__file__).resolve().parents[3]
router = APIRouter()
JOBS: dict[str, dict] = {}


# ----------------------------------------------------------------------------- research jobs
class SearchIn(BaseModel):
    data_path: str | None = None          # server-side CSV/Parquet of 1-min bars; else synthetic
    symbol: str = "MES"
    days: int = Field(1500, ge=300, le=4000)
    momentum: float = 0.0
    seed: int = 7
    nam: int = Field(4000, le=50000)
    orb: int = Field(1000, le=5000)
    vwr: int = Field(1000, le=8000)
    ldm: bool = True


def _run_job(jid: str, req: SearchIn):
    job = JOBS[jid]
    try:
        job["stage"] = "building features"
        panel = build_panel(load_bars(req.data_path)) if req.data_path else \
            build_panel(synthetic_bars(n_days=req.days, momentum=req.momentum, seed=req.seed))
        mf = MarketFeatures.build(panel, req.symbol)
        configs = []
        for fam, n in (("NAM", req.nam), ("ORB", req.orb), ("VWR", req.vwr)):
            if n:
                configs += sample_configs({fam: DEFAULT_SPACE[fam]}, n, seed=req.seed)
        if req.ldm:
            configs += sample_configs({"LDM": DEFAULT_SPACE["LDM"]}, None)
        job.update(stage="searching", total=len(configs))

        def prog(j, n):
            job["done"] = j
        res = run_search(mf, configs, progress=prog)
        valid = res.scores[res.scores.trades_is >= 40]
        best = valid.loc[valid.sharpe_is.idxmax()] if len(valid) else None
        job["result"] = _clean({
            "source": req.data_path or f"SYNTHETIC κ={req.momentum} seed={req.seed} ({req.days} days)",
            "n_configs": len(configs), "elapsed_s": res.elapsed_s,
            "verdict": {
                "best_sharpe_is": None if best is None else best.sharpe_is,
                "best_sharpe_oos": None if best is None else best.sharpe_oos,
                "dsr_raw": res.dsr_best, "dsr_effective": res.pbo.get("dsr_effective"),
                "n_effective_trials": res.pbo.get("n_effective_trials"), "pbo": res.pbo.get("pbo"),
                "wf_oos_sharpe": res.wf["oos_sharpe"], "wf_oos_mean_daily_r": res.wf["oos_mean_daily_r"],
                "passes_gate": bool((res.wf["oos_sharpe"] or 0) > 0.5 and (res.pbo.get("pbo") or 1) < 0.2
                                    and (res.pbo.get("dsr_effective") or 0) >= 0.95),
            },
            "pbo_hist": res.pbo.get("logits_hist"),
            "families": family_summary(res).to_dict(orient="records"),
            "leaderboard": res.leaderboard(25).assign(params=lambda d: d.params.map(json.dumps)).to_dict(orient="records"),
            "wf_equity": [{"i": i, "r": float(x)} for i, x in enumerate(np.cumsum(res.wf["oos_daily_r"]))][::2],
            "wf_picks": res.wf["picks"],
        })
        job.update(stage="done", done=len(configs))
    except Exception as e:  # pragma: no cover - surfaced to UI
        job.update(stage="error", error=repr(e))


@router.post("/api/research/search")
def research_search(req: SearchIn):
    jid = uuid.uuid4().hex[:8]
    JOBS[jid] = {"id": jid, "stage": "queued", "done": 0, "total": 0, "started": time.time(), "request": req.model_dump()}
    threading.Thread(target=_run_job, args=(jid, req), daemon=True).start()
    return {"job": jid}


@router.get("/api/research/jobs/{jid}")
def research_job(jid: str):
    if jid not in JOBS:
        raise HTTPException(404, "unknown job")
    j = JOBS[jid]
    return {k: v for k, v in j.items() if k != "result"} | ({"result": j["result"]} if "result" in j else {})


@router.get("/api/research/precomputed")
def research_precomputed():
    out = {}
    for tag in ("noise", "edge", "real"):
        p = ROOT / "docs" / "results" / f"edge_search_{tag}.json"
        if p.exists():
            js = json.loads(p.read_text())
            out[tag] = {k: js[k] for k in ("source", "n_configs", "pbo", "dsr_best", "wf", "best", "families") if k in js}
            out[tag]["wf_equity"] = [{"i": i, "r": r} for i, r in enumerate(js.get("wf_equity", []))][::2]
    return _clean(out)


# ----------------------------------------------------------------------------- fleet simulation
class FleetIn(BaseModel):
    program: str = "topstep_150k"
    model: str = "basket_planning"
    slots: int = Field(5, ge=1, le=20)
    rho: float = Field(0.4, ge=0, le=1)
    eval_risk: float = 1125
    funded_risk: float | None = None
    up_frac: float = 0.0
    cushion: float = 0.0
    years: int = Field(3, ge=1, le=5)
    n_paths: int = Field(400, le=1500)


@router.post("/api/fleet/simulate")
def fleet_simulate(req: FleetIn):
    prog = get_program(req.program)
    sz = SimSizing(risk_dollars=req.eval_risk, funded_risk_dollars=req.funded_risk, up_frac=req.up_frac,
                   up_max_risk=1.5 * req.eval_risk)
    f = simulate_fleet(prog, PRESET_MODELS[req.model], req.slots, req.rho, sz,
                       payout_policy=PayoutPolicy(min_profit_to_request=req.cushion),
                       horizon_days=252 * req.years, n_paths=req.n_paths, seed=13)
    cum = np.cumsum(f.pop("monthly_cash"), axis=0)
    q = np.quantile(cum, [0.05, 0.25, 0.5, 0.75, 0.95], axis=1)
    f["fan"] = [{"month": m + 1, "p05": q[0, m], "p25": q[1, m], "p50": q[2, m], "p75": q[3, m], "p95": q[4, m]}
                for m in range(cum.shape[0])]
    return _clean(f)


# ----------------------------------------------------------------------------- multi-account board
class AccountIn(BaseModel):
    id: str
    program: str = "topstep_150k"
    phase: str = "evaluation"
    start_date: str | None = None
    model: str = "basket_planning"
    eval_risk: float | None = None   # default 25 % of max loss


def tier_table(max_loss: float, eval_risk: float) -> list[dict]:
    """Funded scaling ladder (SYSTEM: AGGRESSIVE §3): risk steps up with the buffer above the
    max-loss lock; never steps down below the base until the buffer itself shrinks."""
    base = 0.5 * eval_risk
    return [{"tier": i, "min_buffer": max_loss * m, "risk": round(base * k)}
            for i, (m, k) in enumerate([(0, 1.0), (1.5, 1.5), (2.0, 2.0), (3.0, 3.0), (5.0, 4.0), (8.0, 6.0)])]


@router.get("/api/fleet/accounts")
def fleet_accounts():
    accts = [AccountIn(**a) for a in store.get_config("accounts", [])]
    out = []
    for a in accts:
        prog = get_program(a.program)
        tr = PropAccountTracker(prog, phase=a.phase)
        rows = store.list_trades(a.id)
        daily = pd.Series(dtype=float)
        attempts, fails, passes, history = 1, 0, 0, []
        if rows:
            df = pd.DataFrame(rows)
            df["date"] = pd.to_datetime(df["date"])
            if a.start_date:
                df = df[df.date >= pd.Timestamp(a.start_date)]
            daily = df.groupby(df.date.dt.date)["pnl"].sum()
            for d, v in daily.items():
                low = min(0.0, float(df[df.date.dt.date == d]["pnl"].cumsum().min()))
                tr.apply_day(float(v), intraday_low=low)
                if tr.state.status == "passed":
                    tr.promote_to_funded()
                    passes += 1
                    history.append({"date": str(d), "event": "passed → funded"})
                elif tr.state.status == "failed":
                    # a slot never dies: buy a new Combine and continue from the next session
                    fails += 1
                    attempts += 1
                    history.append({"date": str(d), "event": f"{tr.state.phase} account lost → new Combine #{attempts}"})
                    tr = PropAccountTracker(prog, phase="evaluation")
        st = tr.status()
        rules = tr.rules
        ml = rules.max_loss
        eval_risk = a.eval_risk or round(0.25 * prog.evaluation.max_loss)
        model = PRESET_MODELS[a.model]
        if st["phase"] == "evaluation":
            risk, tiers, cur, nxt = eval_risk, [], None, None
        else:
            tiers = tier_table(ml, eval_risk)
            cur = max((t for t in tiers if st["buffer_to_mll"] >= t["min_buffer"]), key=lambda t: t["tier"])
            nxt = next((t for t in tiers if t["tier"] == cur["tier"] + 1), None)
            risk = cur["risk"]
        exp_day = model.trades_per_day * model.expected_net_r() * risk
        out.append({
            "id": a.id, "program": prog.name, "phase": st["phase"], "status": st["status"],
            "profit": st["profit"], "buffer": st["buffer_to_mll"], "max_loss": ml,
            "risk_per_trade": risk, "daily_stop": 2 * risk,
            "daily_target": exp_day, "weekly_target": 5 * exp_day,
            "tier": cur, "next_tier": nxt, "tiers": tiers,
            "target_remaining": st.get("target_remaining"), "best_day_share": st.get("best_day_share"),
            "max_profit_today_consistent": st.get("max_profit_today_consistent"),
            "payout_eligible": st.get("payout_eligible"), "payout_amount": st.get("payout_amount"),
            "payout_blockers": st.get("payout_blockers"),
            "last_day_pnl": float(daily.iloc[-1]) if len(daily) else 0.0,
            "attempt": attempts, "losses": fails, "passes": passes, "events": history[-5:],
            "equity": [{"date": str(d), "equity": float(e)} for d, e in zip(daily.index, daily.cumsum().values)][-120:],
        })
    tot = {"accounts": len(out), "funded": sum(o["phase"] == "funded" for o in out),
           "total_buffer": sum(o["buffer"] for o in out), "fleet_daily_target": sum(o["daily_target"] for o in out),
           "payouts_ready": sum(o["payout_amount"] or 0 for o in out if o.get("payout_eligible"))}
    return _clean({"accounts": out, "totals": tot})


@router.post("/api/fleet/accounts")
def fleet_accounts_set(accts: list[AccountIn]):
    for a in accts:
        get_program(a.program)
    store.set_config("accounts", [a.model_dump() for a in accts])
    return {"saved": len(accts)}


@router.post("/api/fleet/demo")
def fleet_demo():
    """Three demo accounts with SYNTHETIC trades (different seeds) so the board has data."""
    accts = []
    for i, (prog, seed) in enumerate((("topstep_150k", 21), ("topstep_150k", 22), ("topstep_50k", 23)), 1):
        aid = f"demo-{i}"
        store.clear_trades(aid)
        end = pd.Timestamp.today().normalize() - pd.offsets.BDay(1)
        panel = build_panel(synthetic_bars(n_days=140, momentum=0.012, seed=seed, start=str((end - pd.offsets.BDay(139)).date())))
        risk = 0.25 * get_program(prog).evaluation.max_loss
        t = run_backtest(panel, [REGISTRY["S1"]()], "MES", Sizing(mode="risk", risk_dollars=risk)).trades
        store.insert_trades([{"account": aid, "source": "demo-synthetic", "date": str(r.date.date()), "entry_time": r.entry_time,
                              "exit_time": r.exit_time, "symbol": "MES", "strategy": r.strategy, "side": int(r.side),
                              "contracts": int(r.contracts), "risk_dollars": float(r.risk_dollars), "pnl": float(r.pnl),
                              "r_net": float(r.r_net), "exit_reason": r.exit_reason} for r in t.itertuples()])
        accts.append(AccountIn(id=aid, program=prog, start_date=str(t.date.min().date()) if len(t) else None))
    store.set_config("accounts", [a.model_dump() for a in accts])
    return {"accounts": [a.id for a in accts], "warning": "synthetic demo data"}


@router.get("/api/aggressive/results")
def aggressive_results():
    p = ROOT / "docs" / "results" / "aggressive_topstep.json"
    if not p.exists():
        raise HTTPException(404, "run engine/scripts/aggressive_topstep.py first")
    js = json.loads(p.read_text())
    return {k: js[k] for k in ("fleet", "growth_law", "ceilings") if k in js}
