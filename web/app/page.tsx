"use client";

import { AlertTriangle, Database, Radio } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { EquityChart } from "@/components/charts";
import { Badge, Card, Empty, Meter, Stat } from "@/components/ui";
import { api, pct, signClass, usd } from "@/lib/api";

type Status = any;

function LiveWidget() {
  const [msg, setMsg] = useState<any>(null);
  const [state, setState] = useState<"connecting" | "open" | "closed">("connecting");
  const ref = useRef<WebSocket | null>(null);
  useEffect(() => {
    const url = process.env.NEXT_PUBLIC_QT_WS || `ws://${window.location.hostname}:8000/ws/live`;
    const ws = new WebSocket(url);
    ref.current = ws;
    ws.onopen = () => setState("open");
    ws.onclose = () => setState("closed");
    ws.onmessage = (e) => setMsg(JSON.parse(e.data));
    return () => ws.close();
  }, []);
  return (
    <Card title={<span className="flex items-center gap-2"><Radio className="h-4 w-4 text-accent" />Live session</span>}
      right={<Badge tone={state === "open" ? "pos" : "muted"}>{state}{msg?.demo ? " · demo feed" : ""}</Badge>}>
      {!msg ? <div className="text-sm text-muted">Waiting for stream…</div> : (
        <div className="space-y-3">
          <div className="flex items-baseline gap-3">
            <span className={`text-3xl font-semibold num ${signClass(msg.day_pnl)}`}>{usd(msg.day_pnl, 0)}</span>
            <span className="text-xs text-muted">peak {usd(msg.peak)} · {msg.trades} trades</span>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge tone={msg.guard.allow_new_trade ? "pos" : "neg"}>{msg.guard.allow_new_trade ? "new trades allowed" : "no new trades"}</Badge>
            {msg.guard.flatten_now && <Badge tone="neg">FLATTEN</Badge>}
            <Badge tone="muted">max risk {usd(msg.guard.max_risk_dollars)}</Badge>
          </div>
          {msg.guard.alerts.map((a: any, i: number) => (
            <div key={i} className="text-xs text-warn">• {a.message}</div>
          ))}
        </div>
      )}
    </Card>
  );
}

export default function Overview() {
  const [st, setSt] = useState<Status | null>(null);
  const [an, setAn] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setErr(null);
      const [s, a] = await Promise.all([api("/account/status"), api("/journal/analytics")]);
      setSt(s); setAn(a);
    } catch (e: any) { setErr(String(e.message || e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const seed = async () => { setBusy(true); try { await api("/demo/seed", { method: "POST" }); await load(); } finally { setBusy(false); } };

  if (err) return <Empty>API not reachable ({err}). Start it with <code>uvicorn qtengine.api.main:app --port 8000</code>.</Empty>;
  if (!st || !an) return <div className="text-sm text-muted">Loading…</div>;

  const s = st.status, prog = st.program, rules = s.phase === "evaluation" ? prog.evaluation : prog.funded;
  const demo = an.recent?.some((t: any) => t.source === "demo-synthetic");
  const ror = st.risk_of_ruin;
  const lastPnl = st.last_day_pnl ?? 0;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-semibold tracking-tight">{prog.name}</h1>
        <Badge tone="accent">{s.phase}</Badge>
        <Badge tone={s.status === "failed" ? "neg" : s.status === "passed" ? "pos" : "muted"}>{s.status}</Badge>
        {demo && <Badge tone="warn">DEMO · synthetic trades</Badge>}
        <div className="ml-auto flex gap-2">
          <button className="btn-ghost" onClick={seed} disabled={busy}><Database className="h-4 w-4" />{busy ? "Seeding…" : "Load demo data"}</button>
        </div>
      </div>

      {an.empty && <Empty>No trades yet. Add trades in the Journal, connect an execution adapter, or load demo data.</Empty>}

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label={`Last session P&L (${st.last_day ?? "—"})`} value={usd(lastPnl)} tone={lastPnl > 0 ? "pos" : lastPnl < 0 ? "neg" : ""}
          sub={`target ${usd(st.daily_target)} · ${pct(lastPnl / st.daily_target)}`} />
        <Stat label="Buffer to max-loss level" value={usd(s.buffer_to_mll)} tone={s.buffer_pct_of_max_loss < 0.35 ? "neg" : s.buffer_pct_of_max_loss < 0.6 ? "warn" : "pos"}
          sub={`MLL ${usd(s.mll_level)}${s.trailing_locked ? " · locked" : " · trailing"}`} />
        {s.phase === "evaluation" ? (
          <Stat label="Profit target remaining" value={usd(s.target_remaining)}
            tone={s.target_remaining === 0 && s.status === "active" ? "warn" : ""}
            sub={s.target_remaining === 0 && s.status === "active"
              ? `target hit but blocked by the ${pct(rules.consistency_pct)} consistency rule — keep trading small`
              : `profit ${usd(s.profit)} of ${usd(rules.profit_target)}`} />
        ) : (
          <Stat label="Payout" value={s.payout_eligible ? usd(s.payout_amount) : "not yet"} tone={s.payout_eligible ? "pos" : ""}
            sub={s.payout_blockers?.join(" · ") || `${s.winning_days_since_payout} winning days`} />
        )}
        <Stat label="P(breach MLL) next 20 / 60 days" value={ror ? `${pct(ror.p_breach_20d, 1)} / ${pct(ror.p_breach_60d, 1)}` : "—"}
          tone={ror && ror.p_breach_60d > 0.3 ? "neg" : ror && ror.p_breach_60d > 0.15 ? "warn" : "pos"}
          sub={ror ? `bootstrap of ${an.daily?.days ?? 0} days · Lundberg bound ${pct(ror.lundberg_bound, 0)}` : "needs ≥ 15 trading days"} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Account equity (journal)" className="lg:col-span-2">
          {an.equity?.length ? <EquityChart data={an.equity} height={260} /> : <Empty>No data</Empty>}
        </Card>
        <div className="space-y-4">
          <Card title="Limits">
            <div className="space-y-3">
              <Meter label="Drawdown buffer remaining" used={Math.max(s.buffer_to_mll, 0)} limit={Math.max(rules.max_loss, s.buffer_to_mll)} invert format={(x) => usd(x)} />
              {s.phase === "evaluation" && rules.profit_target && (
                <Meter label="Progress to target" used={Math.max(s.profit, 0)} limit={rules.profit_target} invert format={(x) => usd(x)} />
              )}
              <Meter label="Today vs internal daily stop" used={Math.max(-lastPnl, 0)} limit={st.config.guard?.internal_daily_stop ?? 400} format={(x) => usd(x)} />
              {s.max_profit_today_consistent != null && (
                <div className="flex justify-between text-xs"><span className="text-muted">Max profit today (consistency-safe)</span><span className="num">{usd(s.max_profit_today_consistent)}</span></div>
              )}
              {s.best_day_share != null && (
                <div className="flex justify-between text-xs"><span className="text-muted">Best-day share of profit</span>
                  <span className={`num ${s.best_day_share > (rules.consistency_pct ?? 1) ? "text-neg" : ""}`}>{pct(s.best_day_share)} (limit {pct(rules.consistency_pct)})</span></div>
              )}
              {ror?.p_pass_before_fail != null && (
                <div className="flex justify-between text-xs"><span className="text-muted">P(pass before fail), empirical</span><span className="num">{pct(ror.p_pass_before_fail)}</span></div>
              )}
            </div>
          </Card>
          <Card title={<span className="flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-warn" />Risk guard</span>}>
            <div className="mb-2 flex flex-wrap gap-2">
              <Badge tone={st.guard.allow_new_trade ? "pos" : "neg"}>{st.guard.allow_new_trade ? "trading allowed" : "trading blocked"}</Badge>
              <Badge tone="muted">max risk now {usd(st.guard.max_risk_dollars)}</Badge>
            </div>
            <ul className="space-y-1 text-xs text-muted">
              {st.guard.reasons.map((r: string) => <li key={r}>• {r}</li>)}
              {st.guard.alerts.map((a: any, i: number) => <li key={i} className={a.level === "critical" ? "text-neg" : "text-warn"}>• {a.message}</li>)}
              {!st.guard.reasons.length && !st.guard.alerts.length && <li>No active restrictions.</li>}
            </ul>
          </Card>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <LiveWidget />
        <Card title="Rule events" className="lg:col-span-2">
          {st.events.length ? (
            <ul className="space-y-1 text-sm">{st.events.slice(-8).map((e: any) => <li key={e.date} className="num"><span className="text-muted">{e.date}</span> — {e.events.join(", ")}</li>)}</ul>
          ) : <div className="text-sm text-muted">No rule events.</div>}
          <div className="mt-3 text-xs text-muted">Rules: {prog.firm} · {prog.last_checked}. Verify against the firm&apos;s current rulebook.</div>
        </Card>
      </div>
    </div>
  );
}
