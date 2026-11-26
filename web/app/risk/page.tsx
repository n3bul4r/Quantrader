"use client";

import { Calculator, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Badge, Card, Field, Stat } from "@/components/ui";
import { api, num, pct, usd } from "@/lib/api";

export default function Risk() {
  const [r, setR] = useState({ daily_mean: 20, daily_sd: 250, target: 3000, max_loss: 2000 });
  const [out, setOut] = useState<any>(null);
  const [g, setG] = useState<any>({ now: "10:30", day_pnl: -150, day_peak_pnl: 60, trades_today: 2, consecutive_losses: 1, minutes_since_last_loss: 4, equity: 600, mll_level: -1400 });
  const [gd, setGd] = useState<any>(null);

  const calc = async () => setOut(await api("/risk/ruin", { method: "POST", json: r }));
  const check = async () => setGd(await api("/risk/guard", { method: "POST", json: { state: Object.fromEntries(Object.entries(g).map(([k, v]) => [k, k === "now" ? v : Number(v)])) } }));

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold tracking-tight">Risk engine</h1>
      <Card title={<span className="flex items-center gap-2"><Calculator className="h-4 w-4 text-accent" />Risk of ruin (diffusion approximation)</span>}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          {(["daily_mean", "daily_sd", "target", "max_loss"] as const).map((k) => (
            <Field key={k} label={k.replace("_", " ")}><input className="input" type="number" value={r[k]} onChange={(e) => setR({ ...r, [k]: Number(e.target.value) })} /></Field>
          ))}
          <div className="flex items-end"><button className="btn w-full justify-center" onClick={calc}>Compute</button></div>
        </div>
        <p className="mt-2 text-xs text-muted">Daily Sharpe = {num(r.daily_mean / r.daily_sd, 3)} (annualised {num((r.daily_mean / r.daily_sd) * Math.sqrt(252))}). The ratio max_loss / daily_sd is your survival budget in “bad days”.</p>
        {out && (
          <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-5">
            <Stat label="P(target before static ruin)" value={pct(out.p_target_before_static_ruin, 1)} />
            <Stat label="P(reach MLL lock before trailing breach)" value={pct(out.p_reach_lock_before_trailing_breach, 1)} sub="Lehoczky 1977" />
            <Stat label="P(ever ruined, static, no target)" value={pct(out.p_ruin_infinite_static, 1)} />
            <Stat label="E[days to a max-loss drawdown]" value={num(out.expected_days_to_drawdown, 0)} sub="Taylor 1975" />
            <Stat label="Days to target from drift alone" value={out.expected_days_to_target_drift_only ? num(out.expected_days_to_target_drift_only, 0) : "∞"} />
          </div>
        )}
      </Card>

      <Card title={<span className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-accent" />Pre-trade guard check</span>}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {Object.keys(g).map((k) => (
            <Field key={k} label={k.replaceAll("_", " ")}><input className="input" value={g[k]} onChange={(e) => setG({ ...g, [k]: e.target.value })} /></Field>
          ))}
        </div>
        <button className="btn mt-3" onClick={check}>Evaluate</button>
        {gd && (
          <div className="mt-4 space-y-2 text-sm">
            <div className="flex flex-wrap gap-2">
              <Badge tone={gd.allow_new_trade ? "pos" : "neg"}>{gd.allow_new_trade ? "ALLOW" : "BLOCK"}</Badge>
              {gd.flatten_now && <Badge tone="neg">FLATTEN NOW</Badge>}
              <Badge>max risk {usd(gd.max_risk_dollars)}</Badge>
            </div>
            <ul className="text-xs text-muted">{gd.reasons.map((x: string) => <li key={x}>• {x}</li>)}</ul>
            <ul className="text-xs">{gd.alerts.map((a: any, i: number) => <li key={i} className={a.level === "critical" ? "text-neg" : "text-warn"}>• {a.message}</li>)}</ul>
          </div>
        )}
      </Card>

      <Card title="Sizing rules in force">
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
          <li>Size off the <b className="text-fg">drawdown buffer</b> (equity − MLL), never the nominal account size.</li>
          <li>Risk per trade 10–20% of the buffer in evaluations (option regime), 5–10% once funded (cash-flow regime); halve when the buffer is below 50% of the max loss.</li>
          <li>Daily stop = 2R; stop after 3 consecutive losses; 10-minute cool-down after any loss.</li>
          <li>Daily profit cap at 45% of the profit target when a 50% consistency rule applies.</li>
          <li>Scale up one tier only when buffer ≥ next tier AND the rolling 60-trade expectancy LCB90 &gt; 0 AND no live-vs-backtest drift.</li>
        </ul>
      </Card>
    </div>
  );
}
