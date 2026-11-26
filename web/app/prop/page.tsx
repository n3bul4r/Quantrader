"use client";

import { Play, SlidersHorizontal } from "lucide-react";
import { useEffect, useState } from "react";
import { FanChart, SweepChart } from "@/components/charts";
import { Badge, Card, Field, Stat } from "@/components/ui";
import { api, num, pct, usd } from "@/lib/api";

export default function PropSim() {
  const [presets, setPresets] = useState<Record<string, any>>({});
  const [models, setModels] = useState<Record<string, any>>({});
  const [econ, setEcon] = useState<any>(null);
  const [req, setReq] = useState<any>({ program: "topstep_50k", preset: "S1_planning", risk_dollars: 300, n_accounts: 1, horizon_days: 252, n_paths: 4000,
    win_rate: "", avg_win_r: "", trades_per_day: "", stop_dollars: "", cost_per_contract: "" });
  const [res, setRes] = useState<any>(null);
  const [sweep, setSweep] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    api("/presets").then(setPresets);
    api("/models").then(setModels);
    api("/economics").then(setEcon).catch(() => {});
  }, []);

  const body = () => {
    const ov = (k: string) => (req[k] === "" ? undefined : Number(req[k]));
    return { program: req.program, risk_dollars: Number(req.risk_dollars), n_accounts: Number(req.n_accounts), horizon_days: Number(req.horizon_days),
      n_paths: Number(req.n_paths), model: { preset: req.preset, win_rate: ov("win_rate"), avg_win_r: ov("avg_win_r"), trades_per_day: ov("trades_per_day"),
        stop_dollars: ov("stop_dollars"), cost_per_contract: ov("cost_per_contract") } };
  };
  const run = async () => { setBusy("sim"); try { setRes(await api("/prop/simulate", { method: "POST", json: body() })); } finally { setBusy(null); } };
  const runSweep = async () => {
    setBusy("sweep");
    const ml = presets[req.program]?.evaluation?.max_loss ?? 2000;
    try { setSweep(await api("/prop/sweep", { method: "POST", json: { ...body(), risks: [0.05, 0.1, 0.15, 0.2, 0.25, 0.35].map((f) => Math.round(f * ml)) } })); }
    finally { setBusy(null); }
  };
  const set = (k: string) => (e: any) => setReq({ ...req, [k]: e.target.value });
  const p = presets[req.program];
  const m = res?.model;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Prop-firm account simulator</h1>
        <p className="mt-1 max-w-3xl text-sm text-muted">Monte Carlo of the full lifecycle: buy evaluation → pass/fail → funded → payouts → blow-up → buy again.
          Net = your share of payouts minus every fee. The trade model is an assumption until you replace it with your own out-of-sample trades.</p>
      </div>
      <Card title="Inputs">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <Field label="Program"><select className="input" value={req.program} onChange={set("program")}>{Object.entries(presets).map(([k, v]) => <option key={k} value={k}>{v.name}</option>)}</select></Field>
          <Field label="Trade model"><select className="input" value={req.preset} onChange={set("preset")}>{Object.keys(models).map((k) => <option key={k}>{k}</option>)}</select></Field>
          <Field label="Risk $ / trade"><input className="input" type="number" value={req.risk_dollars} onChange={set("risk_dollars")} /></Field>
          <Field label="Copy-traded accounts"><input className="input" type="number" min={1} max={p?.max_accounts ?? 20} value={req.n_accounts} onChange={set("n_accounts")} /></Field>
          <Field label="Horizon (trading days)"><input className="input" type="number" value={req.horizon_days} onChange={set("horizon_days")} /></Field>
          <Field label="Win rate override"><input className="input" placeholder={String(models[req.preset]?.win_rate ?? "")} value={req.win_rate} onChange={set("win_rate")} /></Field>
          <Field label="Avg win R override"><input className="input" placeholder={String(models[req.preset]?.avg_win_r ?? "")} value={req.avg_win_r} onChange={set("avg_win_r")} /></Field>
          <Field label="Trades/day override"><input className="input" placeholder={String(models[req.preset]?.trades_per_day ?? "")} value={req.trades_per_day} onChange={set("trades_per_day")} /></Field>
          <Field label="Stop $/contract"><input className="input" placeholder={String(models[req.preset]?.stop_dollars ?? "")} value={req.stop_dollars} onChange={set("stop_dollars")} /></Field>
          <Field label="Cost $/contract RT"><input className="input" placeholder={String(models[req.preset]?.cost_per_contract ?? "")} value={req.cost_per_contract} onChange={set("cost_per_contract")} /></Field>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button className="btn" onClick={run} disabled={!!busy}><Play className="h-4 w-4" />{busy === "sim" ? "Simulating…" : "Simulate"}</button>
          <button className="btn-ghost" onClick={runSweep} disabled={!!busy}><SlidersHorizontal className="h-4 w-4" />{busy === "sweep" ? "Sweeping…" : "Sweep risk per trade"}</button>
        </div>
        {p && (
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <Badge>target {usd(p.evaluation.profit_target)}</Badge><Badge>max loss {usd(p.evaluation.max_loss)} · {p.evaluation.drawdown_type}</Badge>
            <Badge>DLL {p.evaluation.daily_loss_limit ? usd(p.evaluation.daily_loss_limit) : "none"}</Badge>
            <Badge>consistency {p.evaluation.consistency_pct ? pct(p.evaluation.consistency_pct) : "none"}</Badge>
            <Badge>payout: {p.funded.payout_winning_days} days ≥ {usd(p.funded.winning_day_threshold)}, cap {usd(p.funded.payout_cap)}</Badge>
            <Badge tone="warn">{p.last_checked}</Badge>
          </div>
        )}
      </Card>

      {res && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
            <Stat label="Net / horizon (mean)" value={usd(res.net_mean)} tone={res.net_mean > 0 ? "pos" : "neg"} sub={`median ${usd(res.net_median)}`} />
            <Stat label="P(net > 0)" value={pct(res.p_net_positive)} sub={`5–95%: ${usd(res.net_p05)} … ${usd(res.net_p95)}`} />
            <Stat label="Pass rate / attempt" value={pct(res.pass_rate_per_attempt)} sub={`${num(res.evals_bought_mean, 1)} evaluations bought`} />
            <Stat label="P(≥ 1 payout)" value={pct(res.p_any_payout)} sub={`first payout ~day ${res.median_day_first_payout ?? "—"}`} />
            <Stat label="Fees vs payouts" value={`${usd(res.fees_mean)} / ${usd(res.payouts_mean)}`} />
            <Stat label="€ per trading day" value={`€${num(res.net_per_trading_day_mean / 1.16, 2)}`} sub={`model edge ${num(m?.expected_net_r, 3)}R · Sharpe ${num(m?.annual_sharpe)}`} />
          </div>
          <Card title="Cumulative net cash (payouts − fees): 5/25/50/75/95th percentiles"><FanChart data={res.cash_fan} /></Card>
        </>
      )}
      {sweep && (
        <Card title={`Risk per trade vs annual net — ${sweep.program} · ${sweep.model.name}`}>
          <SweepChart data={sweep.rows} />
          <p className="mt-2 text-xs text-muted">The mean keeps rising with size because your loss is capped at fees (an option payoff) — the median tells you what usually happens.</p>
        </Card>
      )}
      {econ?.income && (
        <Card title="Pre-computed: accounts needed for a daily income target (EV-optimal risk, 1-year horizon)">
          <div className="overflow-x-auto">
            <table className="data">
              <thead><tr><th>program</th><th>model</th><th>risk $</th><th>€/day/account (mean)</th><th>(median)</th><th>accounts for €100/day</th></tr></thead>
              <tbody>
                {econ.income.map((r: any) => (
                  <tr key={r.program + r.model}>
                    <td className="font-sans">{r.program}</td><td className="font-sans">{r.model}</td><td>{r.risk}</td>
                    <td>{num(r.eur_day_mean)}</td><td>{num(r.eur_day_median)}</td><td>{r.eur_day_mean > 0 ? Math.ceil(100 / r.eur_day_mean) : "∞"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
