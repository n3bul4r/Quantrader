"use client";

import { Database, Layers, Play } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { FanChart, SmallLine } from "@/components/charts";
import { Badge, Card, Empty, Field, Meter, Stat } from "@/components/ui";
import { api, pct, signClass, usd } from "@/lib/api";

function AccountCard({ a }: { a: any }) {
  return (
    <div className="card space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold">{a.id}</span>
        <Badge tone="accent">{a.phase}</Badge>
        <Badge tone={a.status === "failed" ? "neg" : a.status === "passed" ? "pos" : "muted"}>{a.status}</Badge>
        {a.payout_eligible && <Badge tone="pos">payout ready {usd(a.payout_amount)}</Badge>}
      </div>
      <div className="text-xs text-muted">{a.program} · attempt #{a.attempt} · {a.passes} passed · {a.losses} lost</div>
      <div className="grid grid-cols-3 gap-2 text-sm">
        <div><div className="label">profit</div><div className={`num ${signClass(a.profit)}`}>{usd(a.profit)}</div></div>
        <div><div className="label">risk / trade</div><div className="num">{usd(a.risk_per_trade)}</div></div>
        <div><div className="label">daily stop</div><div className="num">{usd(a.daily_stop)}</div></div>
        <div><div className="label">daily target</div><div className="num">{usd(a.daily_target)}</div></div>
        <div><div className="label">weekly target</div><div className="num">{usd(a.weekly_target)}</div></div>
        <div><div className="label">last day</div><div className={`num ${signClass(a.last_day_pnl)}`}>{usd(a.last_day_pnl)}</div></div>
      </div>
      <Meter label="Buffer to max-loss level" used={Math.max(a.buffer, 0)} limit={Math.max(a.max_loss, a.buffer, 1)} invert format={(x) => usd(x)} />
      {a.phase === "evaluation" ? (
        <div className="text-xs text-muted">Target remaining {usd(a.target_remaining)}{a.best_day_share != null && ` · best-day share ${pct(a.best_day_share)}`}
          {a.max_profit_today_consistent != null && ` · max profit today ${usd(a.max_profit_today_consistent)}`}</div>
      ) : (
        <div className="text-xs">
          <span className="text-muted">Tier {a.tier?.tier} · </span>
          {a.next_tier ? <span>scale to <b>{usd(a.next_tier.risk)}</b>/trade when buffer ≥ <b>{usd(a.next_tier.min_buffer)}</b></span> : <span>top tier</span>}
          {!a.payout_eligible && a.payout_blockers?.length > 0 && <div className="mt-1 text-muted">payout: {a.payout_blockers.join(" · ")}</div>}
        </div>
      )}
      {a.equity?.length > 1 && <SmallLine data={a.equity} x="date" y="equity" height={90} />}
      {a.events?.length > 0 && <ul className="text-[11px] text-muted">{a.events.map((e: any, i: number) => <li key={i} className="num">{e.date} — {e.event}</li>)}</ul>}
    </div>
  );
}

export default function Fleet() {
  const [board, setBoard] = useState<any>(null);
  const [agg, setAgg] = useState<any>(null);
  const [sim, setSim] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [req, setReq] = useState<any>({ program: "topstep_150k", model: "basket_planning", slots: 5, rho: 0.4, eval_risk: 1125, funded_risk: "", up_frac: 0, cushion: 0, years: 3 });
  const load = useCallback(() => api("/fleet/accounts").then(setBoard).catch(() => setBoard({ accounts: [] })), []);
  useEffect(() => { load(); api("/aggressive/results").then(setAgg).catch(() => {}); }, [load]);
  const demo = async () => { await api("/fleet/demo", { method: "POST" }); load(); };
  const run = async () => {
    setBusy(true);
    try {
      setSim(await api("/fleet/simulate", { method: "POST", json: { ...req, funded_risk: req.funded_risk === "" ? null : Number(req.funded_risk),
        slots: Number(req.slots), rho: Number(req.rho), eval_risk: Number(req.eval_risk), up_frac: Number(req.up_frac), cushion: Number(req.cushion), years: Number(req.years) } }));
    } finally { setBusy(false); }
  };
  const set = (k: string) => (e: any) => setReq({ ...req, [k]: e.target.value });
  const t = board?.totals;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold tracking-tight">Fleet command</h1>
        {board?.accounts?.some((a: any) => a.id.startsWith("demo")) && <Badge tone="warn">DEMO · synthetic trades</Badge>}
        <button className="btn-ghost ml-auto" onClick={demo}><Database className="h-4 w-4" />Load demo fleet</button>
      </div>

      {t && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <Stat label="Accounts" value={t.accounts} sub={`${t.funded} funded`} />
          <Stat label="Total buffer" value={usd(t.total_buffer)} />
          <Stat label="Fleet daily target" value={usd(t.fleet_daily_target)} sub="expected P&L at current tiers" />
          <Stat label="Fleet weekly target" value={usd(5 * t.fleet_daily_target)} />
          <Stat label="Payouts ready" value={usd(t.payouts_ready)} tone={t.payouts_ready > 0 ? "pos" : ""} />
        </div>
      )}
      {board?.accounts?.length ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{board.accounts.map((a: any) => <AccountCard key={a.id} a={a} />)}</div>
      ) : <Empty>No accounts configured. POST /api/fleet/accounts with your Topstep accounts, or load the demo fleet.</Empty>}

      <Card title={<span className="flex items-center gap-2"><Layers className="h-4 w-4 text-accent" />Fleet simulator</span>}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-9">
          <div className="col-span-2"><Field label="Account"><select className="input" value={req.program} onChange={set("program")}>
            {["topstep_50k", "topstep_100k", "topstep_150k", "topstep_50k_consistency", "topstep_150k_consistency", "topstep_150k_uncapped_hypothetical"].map((p) => <option key={p}>{p}</option>)}</select></Field></div>
          <Field label="Edge model"><select className="input" value={req.model} onChange={set("model")}>
            {["S1_planning", "S1_optimistic", "basket_planning", "basket_optimistic", "zero_edge"].map((m) => <option key={m}>{m}</option>)}</select></Field>
          <Field label="Slots"><input className="input" type="number" value={req.slots} onChange={set("slots")} /></Field>
          <Field label="ρ between slots"><input className="input" type="number" step="0.1" value={req.rho} onChange={set("rho")} /></Field>
          <Field label="Eval risk $"><input className="input" type="number" value={req.eval_risk} onChange={set("eval_risk")} /></Field>
          <Field label="Funded risk $"><input className="input" placeholder="same" value={req.funded_risk} onChange={set("funded_risk")} /></Field>
          <Field label="Scale-up frac"><input className="input" type="number" step="0.05" value={req.up_frac} onChange={set("up_frac")} /></Field>
          <Field label="Years"><input className="input" type="number" value={req.years} onChange={set("years")} /></Field>
        </div>
        <button className="btn mt-3" onClick={run} disabled={busy}><Play className="h-4 w-4" />{busy ? "Simulating…" : "Simulate fleet"}</button>
        {sim && (
          <div className="mt-4 space-y-4">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
              {Object.entries(sim.by_year).map(([y, v]: any) => (
                <Stat key={y} label={`Net after ${y} y (median)`} value={usd(v.median)} tone={v.median > 0 ? "pos" : "neg"} sub={`mean ${usd(v.mean)} · 5th pct ${usd(v.p05)}`} />
              ))}
            </div>
            <div className="overflow-x-auto"><table className="data">
              <thead><tr><th>milestone (cumulative net)</th>{Object.keys(sim.milestones).map((m) => <th key={m}>{usd(Number(m))}</th>)}</tr></thead>
              <tbody>
                <tr><td className="font-sans">P(reach)</td>{Object.values(sim.milestones).map((v: any, i) => <td key={i}>{pct(v.p_reach)}</td>)}</tr>
                <tr><td className="font-sans">median months</td>{Object.values(sim.milestones).map((v: any, i) => <td key={i}>{v.median_months == null ? "—" : v.median_months.toFixed(0)}</td>)}</tr>
              </tbody>
            </table></div>
            <FanChart data={sim.fan} xKey="month" xLabel="month" />
          </div>
        )}
      </Card>

      {agg?.fleet && (
        <Card title="Pre-computed fleet scenarios (EV-optimal single-slot config, 3 years)">
          <div className="overflow-x-auto"><table className="data">
            <thead><tr><th>model</th><th>account</th><th>slots</th><th>ρ</th><th>median 1y</th><th>median 3y</th><th>mean 3y</th><th>P(≥$100k)</th><th>P(≥$1M)</th></tr></thead>
            <tbody>{agg.fleet.map((f: any, i: number) => (
              <tr key={i}><td className="font-sans">{f.model}</td><td className="font-sans">{f.program}</td><td>{f.slots}</td><td>{f.rho}</td>
                <td>{usd(f.by_year["1"].median)}</td><td>{usd(f.by_year["3"].median)}</td><td>{usd(f.by_year["3"].mean)}</td>
                <td>{pct(f.milestones["100000"].p_reach)}</td><td>{pct(f.milestones["1000000"].p_reach)}</td></tr>
            ))}</tbody>
          </table></div>
        </Card>
      )}
    </div>
  );
}
