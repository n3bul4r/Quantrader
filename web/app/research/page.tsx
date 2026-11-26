"use client";

import { Cpu, Play } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { BarsChart, SmallLine } from "@/components/charts";
import { Badge, Card, Empty, Field, Stat } from "@/components/ui";
import { api, num, pct } from "@/lib/api";

const rfmt = (v: number) => `${v.toFixed(0)}R`;

function Verdict({ v }: { v: any }) {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
      <Stat label="Best in-sample Sharpe" value={num(v.best_sharpe_is)} sub="what a naive optimiser shows" />
      <Stat label="Same config out-of-sample" value={num(v.best_sharpe_oos)} tone={v.best_sharpe_oos > 0.5 ? "pos" : "neg"} />
      <Stat label="Walk-forward OOS Sharpe" value={num(v.wf_oos_sharpe)} tone={v.wf_oos_sharpe > 0.5 ? "pos" : "neg"} sub="the honest number" />
      <Stat label="PBO (CSCV)" value={pct(v.pbo)} tone={v.pbo < 0.2 ? "pos" : v.pbo < 0.5 ? "warn" : "neg"} sub="< 20 % to pass" />
      <Stat label="Deflated Sharpe (eff. trials)" value={num(v.dsr_effective)} tone={v.dsr_effective >= 0.95 ? "pos" : "warn"}
        sub={`≈ ${num(v.n_effective_trials, 0)} independent bets · raw ${num(v.dsr_raw)}`} />
      <Stat label="Promotion gate" value={v.passes_gate ? "PASS" : "FAIL"} tone={v.passes_gate ? "pos" : "neg"} sub="WF > 0.5 · PBO < 20 % · DSR ≥ 0.95" />
    </div>
  );
}

export default function Research() {
  const [pre, setPre] = useState<any>(null);
  const [req, setReq] = useState({ momentum: 0.0, days: 1500, seed: 7, nam: 4000, orb: 1000, vwr: 1000, data_path: "" });
  const [job, setJob] = useState<any>(null);
  const timer = useRef<any>(null);
  useEffect(() => { api("/research/precomputed").then(setPre).catch(() => setPre({})); return () => clearInterval(timer.current); }, []);

  const launch = async () => {
    const body: any = { ...req, data_path: req.data_path || null };
    const { job: id } = await api("/research/search", { method: "POST", json: body });
    setJob({ id, stage: "queued" });
    clearInterval(timer.current);
    timer.current = setInterval(async () => {
      const s = await api(`/research/jobs/${id}`);
      setJob(s);
      if (s.stage === "done" || s.stage === "error") clearInterval(timer.current);
    }, 1000);
  };
  const set = (k: string) => (e: any) => setReq({ ...req, [k]: e.target.value === "" ? "" : (k === "data_path" ? e.target.value : Number(e.target.value)) });
  const r = job?.result;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Research lab</h1>
        <p className="mt-1 max-w-3xl text-sm text-muted">Massive parameter search across four strategy families (noise-area momentum, opening-range breakout,
          VWAP reversion, late-session momentum) with JIT kernels — then an audit of the search itself: walk-forward re-selection, probability of
          backtest overfitting, deflated Sharpe. Only configurations that pass the gate may trade an evaluation.</p>
      </div>

      {pre && (pre.noise || pre.edge) && (
        <Card title="Calibration runs: what the search finds in pure noise vs. a small real edge (synthetic, 12,144 configs each)">
          <div className="grid gap-4 lg:grid-cols-2">
            {(["noise", "edge"] as const).filter((k) => pre[k]).map((k) => (
              <div key={k}>
                <div className="mb-2 flex items-center gap-2"><Badge tone={k === "noise" ? "neg" : "pos"}>{k === "noise" ? "pure noise (κ = 0)" : "injected edge (κ = 0.01)"}</Badge></div>
                <table className="data mb-2"><tbody>
                  <tr><td className="font-sans">best in-sample Sharpe</td><td>{num(pre[k].best?.sharpe_is)}</td></tr>
                  <tr><td className="font-sans">its out-of-sample Sharpe</td><td>{num(pre[k].best?.sharpe_oos)}</td></tr>
                  <tr><td className="font-sans">walk-forward OOS Sharpe</td><td>{num(pre[k].wf?.oos_sharpe)}</td></tr>
                  <tr><td className="font-sans">PBO</td><td>{pct(pre[k].pbo?.pbo)}</td></tr>
                  <tr><td className="font-sans">deflated Sharpe (effective trials)</td><td>{num(pre[k].pbo?.dsr_effective)}</td></tr>
                </tbody></table>
                <SmallLine data={pre[k].wf_equity} x="i" y="r" fmt={rfmt} height={120} />
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card title={<span className="flex items-center gap-2"><Cpu className="h-4 w-4 text-accent" />Launch a search</span>}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-8">
          <div className="col-span-2"><Field label="Real data path on server (blank = synthetic)"><input className="input" value={req.data_path} onChange={set("data_path")} placeholder="/data/MES_1m.csv" /></Field></div>
          <Field label="Synthetic days"><input className="input" type="number" value={req.days} onChange={set("days")} /></Field>
          <Field label="Injected κ"><input className="input" type="number" step="0.005" value={req.momentum} onChange={set("momentum")} /></Field>
          <Field label="Seed"><input className="input" type="number" value={req.seed} onChange={set("seed")} /></Field>
          <Field label="NAM configs"><input className="input" type="number" value={req.nam} onChange={set("nam")} /></Field>
          <Field label="ORB configs"><input className="input" type="number" value={req.orb} onChange={set("orb")} /></Field>
          <Field label="VWR configs"><input className="input" type="number" value={req.vwr} onChange={set("vwr")} /></Field>
        </div>
        <div className="mt-3 flex items-center gap-3">
          <button className="btn" onClick={launch} disabled={job && !["done", "error"].includes(job.stage)}><Play className="h-4 w-4" />Run search</button>
          {job && (
            <div className="flex-1">
              <div className="mb-1 text-xs text-muted">{job.stage}{job.total ? ` · ${job.done.toLocaleString()} / ${job.total.toLocaleString()} configs` : ""}{job.error ? ` · ${job.error}` : ""}</div>
              <div className="h-1.5 overflow-hidden rounded-full bg-panel2"><div className="h-full bg-accent" style={{ width: `${job.total ? (100 * (job.stage === "done" ? job.total : job.done)) / job.total : 3}%` }} /></div>
            </div>
          )}
        </div>
      </Card>

      {r ? (
        <>
          <div className="flex flex-wrap gap-2"><Badge tone={r.source.startsWith("SYNTH") ? "warn" : "accent"}>{r.source}</Badge><Badge>{r.n_configs.toLocaleString()} configs · {num(r.elapsed_s, 0)} s</Badge></div>
          <Verdict v={r.verdict} />
          <div className="grid gap-4 lg:grid-cols-2">
            <Card title="Walk-forward OOS equity of the re-selection process (R)"><SmallLine data={r.wf_equity} x="i" y="r" fmt={rfmt} height={200} /></Card>
            <Card title="PBO: OOS rank logit of the IS winner (left of centre = overfit)">
              <BarsChart data={(r.pbo_hist || []).map((n: number, i: number) => ({ logit: (-4 + i * 0.5 + 0.25).toFixed(2), n }))} x="logit" y="n" money={false}
                positive={(d) => Number(d.logit) > 0} height={200} />
            </Card>
          </div>
          <Card title="By strategy family">
            <div className="overflow-x-auto"><table className="data">
              <thead><tr><th>family</th><th>configs</th><th>median IS Sharpe</th><th>best IS</th><th>its OOS</th><th>share OOS &gt; 0</th><th>win-rate ≥ 60 % configs</th><th>their OOS E[R]</th></tr></thead>
              <tbody>{r.families.map((f: any) => (
                <tr key={f.family}><td className="font-sans">{f.family}</td><td>{f.configs}</td><td>{num(f.median_sharpe_is)}</td><td>{num(f.best_sharpe_is)}</td>
                  <td>{num(f.best_sharpe_oos)}</td><td>{pct(f.share_oos_positive)}</td><td>{f.high_winrate_configs}</td><td>{num(f.high_winrate_median_exp_r_oos, 3)}</td></tr>
              ))}</tbody>
            </table></div>
          </Card>
          <Card title="In-sample leaderboard (top 25) vs out-of-sample">
            <div className="overflow-x-auto"><table className="data">
              <thead><tr><th>#</th><th>family</th><th>params</th><th>trades/d</th><th>win %</th><th>IS Sharpe</th><th>OOS Sharpe</th><th>IS E[R]</th><th>OOS E[R]</th></tr></thead>
              <tbody>{r.leaderboard.map((x: any, i: number) => (
                <tr key={x.id}><td>{i + 1}</td><td className="font-sans">{x.family}</td><td className="max-w-[340px] truncate font-mono text-[11px]" title={x.params}>{x.params}</td>
                  <td>{num(x.trades_per_day)}</td><td>{pct(x.win_rate)}</td><td>{num(x.sharpe_is)}</td>
                  <td className={x.sharpe_oos > 0 ? "text-pos" : "text-neg"}>{num(x.sharpe_oos)}</td><td>{num(x.exp_r_is, 3)}</td><td>{num(x.exp_r_oos, 3)}</td></tr>
              ))}</tbody>
            </table></div>
          </Card>
        </>
      ) : !job && <Empty>Run a search, or point it at real 1-minute data on the server (Databento/Rithmic export, UTC timestamps).</Empty>}
    </div>
  );
}
