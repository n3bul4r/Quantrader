"use client";

import { Play, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { BarsChart, DrawdownChart, EquityChart } from "@/components/charts";
import { Badge, Card, Empty, Field, Stat } from "@/components/ui";
import { api, num, pct, usd } from "@/lib/api";

const STRATS = [
  { id: "S1", label: "S1 · Noise-area momentum (core)" },
  { id: "S2", label: "S2 · Late-session momentum (satellite)" },
  { id: "S3", label: "S3 · VWAP reversion (research candidate)" },
];

export default function Backtest() {
  const [cfg, setCfg] = useState({ strategies: ["S1"], symbol: "MES", days: 500, momentum: 0, seed: 0, risk_dollars: 200 });
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [fwd, setFwd] = useState<any>(null);
  useEffect(() => { api("/journal/analytics").then(setFwd).catch(() => {}); }, []);

  const run = async () => {
    setBusy(true);
    try {
      if (file) {
        const fd = new FormData();
        fd.append("file", file);
        const q = new URLSearchParams({ strategies: cfg.strategies.join(","), symbol: cfg.symbol, risk_dollars: String(cfg.risk_dollars) });
        const r = await fetch(`/api/backtest/upload?${q}`, { method: "POST", body: fd });
        setRes(await r.json());
      } else {
        setRes(await api("/backtest/synthetic", { method: "POST", json: cfg }));
      }
    } finally { setBusy(false); }
  };
  const toggle = (id: string) => setCfg((c) => ({ ...c, strategies: c.strategies.includes(id) ? c.strategies.filter((s) => s !== id) : [...c.strategies, id] }));
  const t = res?.summary?.trades, d = res?.summary?.daily;
  const hist = res?.r_hist?.map((v: number, i: number) => ({ r: (-2 + i * 0.25).toFixed(2), n: v })) ?? [];

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold tracking-tight">Backtest &amp; forward test</h1>
      <Card title="Configuration">
        <div className="grid gap-4 md:grid-cols-[1.4fr_1fr]">
          <div className="space-y-2">
            {STRATS.map((s) => (
              <label key={s.id} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={cfg.strategies.includes(s.id)} onChange={() => toggle(s.id)} />{s.label}
              </label>
            ))}
            <div className="pt-2">
              <span className="label mb-1 block">Real data (CSV/Parquet: ts, open, high, low, close, volume — UTC, 1-minute)</span>
              <label className="btn-ghost cursor-pointer"><Upload className="h-4 w-4" />{file ? file.name : "Choose file"}
                <input type="file" className="hidden" accept=".csv,.parquet" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></label>
              {file && <button className="ml-2 text-xs text-muted underline" onClick={() => setFile(null)}>use synthetic instead</button>}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Symbol"><select className="input" value={cfg.symbol} onChange={(e) => setCfg({ ...cfg, symbol: e.target.value })}>{["MES", "MNQ", "ES", "NQ"].map((s) => <option key={s}>{s}</option>)}</select></Field>
            <Field label="Risk $ / trade"><input className="input" type="number" value={cfg.risk_dollars} onChange={(e) => setCfg({ ...cfg, risk_dollars: Number(e.target.value) })} /></Field>
            {!file && <>
              <Field label="Synthetic days"><input className="input" type="number" value={cfg.days} onChange={(e) => setCfg({ ...cfg, days: Number(e.target.value) })} /></Field>
              <Field label="Injected momentum κ"><input className="input" type="number" step="0.01" value={cfg.momentum} onChange={(e) => setCfg({ ...cfg, momentum: Number(e.target.value) })} /></Field>
              <Field label="Seed"><input className="input" type="number" value={cfg.seed} onChange={(e) => setCfg({ ...cfg, seed: Number(e.target.value) })} /></Field>
            </>}
            <div className="flex items-end"><button className="btn w-full justify-center" onClick={run} disabled={busy || !cfg.strategies.length}><Play className="h-4 w-4" />{busy ? "Running…" : "Run"}</button></div>
          </div>
        </div>
        {!file && <p className="mt-3 text-xs text-muted">Synthetic data with κ = 0 is a martingale: any profit you see is noise — use it to see what luck looks like. Real validation needs ≥ 3 years of real 1-minute data and the walk-forward gate (engine/qtengine/validation.py).</p>}
      </Card>

      {res && (
        <>
          <div className="flex flex-wrap items-center gap-2"><Badge tone={res.data_source?.startsWith("SYNTH") ? "warn" : "accent"}>{res.data_source}</Badge></div>
          {t?.n ? (
            <>
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
                <Stat label="Trades" value={t.n} sub={`${d.days} sessions`} />
                <Stat label="Win rate" value={pct(t.win_rate, 1)} sub={`avg W ${num(t.avg_win_r)}R / L ${num(t.avg_loss_r)}R`} />
                <Stat label="Expectancy (net)" value={`${num(t.expectancy_r, 3)} R`} tone={t.expectancy_r > 0 ? "pos" : "neg"} sub={`${usd(t.expectancy, 1)} · t=${num(t.t_stat)}`} />
                <Stat label="Profit factor" value={num(t.profit_factor)} sub={`cost ${usd(res.summary.cost_per_contract_rt, 2)}/ct RT`} />
                <Stat label="Sharpe (ann.)" value={num(d.sharpe_annual)} sub={`PSR ${pct(d.psr_vs_0)}`} />
                <Stat label="Max DD" value={usd(d.max_drawdown)} tone="neg" sub={`best-day share ${pct(d.best_day_share)}`} />
              </div>
              <Card title="Equity ($, sized)"><EquityChart data={res.equity} /></Card>
              <div className="grid gap-4 lg:grid-cols-2">
                <Card title="Drawdown"><DrawdownChart data={res.drawdown} /></Card>
                <Card title="Net R distribution (clipped −2…6)"><BarsChart data={hist} x="r" y="n" money={false} positive={(d) => Number(d.r) >= 0} /></Card>
                <Card title="P&L by entry hour"><BarsChart data={res.by_hour} x="hour" y="total" /></Card>
                <Card title="P&L by exit reason"><BarsChart data={res.by_exit} x="exit_reason" y="total" /></Card>
              </div>
            </>
          ) : <Empty>No trades generated.</Empty>}
        </>
      )}

      <Card title="Forward test vs backtest">
        {fwd && !fwd.empty && t ? (
          <div className="grid gap-3 text-sm md:grid-cols-3">
            <div><div className="label">Backtest expectancy</div><div className="num text-lg">{num(t.expectancy_r, 3)} R</div></div>
            <div><div className="label">Forward/live expectancy (journal)</div><div className="num text-lg">{num(fwd.trades.expectancy_r, 3)} R</div><div className="text-xs text-muted">n = {fwd.trades.n}</div></div>
            <div><div className="label">Drift z-score</div><div className="num text-lg">
              {num((fwd.trades.expectancy_r - t.expectancy_r) / ((fwd.trades.std_r || 1) / Math.sqrt(fwd.trades.n)))}</div>
              <div className="text-xs text-muted">below −2 ⇒ the live edge is significantly worse than tested: stop and investigate</div></div>
          </div>
        ) : <div className="text-sm text-muted">Run a backtest and log forward trades in the journal to compare.</div>}
      </Card>
    </div>
  );
}
