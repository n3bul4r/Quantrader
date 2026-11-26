"use client";

import { Play } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { FanChart, MedianCompare } from "@/components/charts";
import { Badge, Card, Field, Stat } from "@/components/ui";
import { api, pct } from "@/lib/api";

const eur = (x: number | null | undefined) => (x == null ? "—" : `€${Math.round(x).toLocaleString("en-US")}`);

export default function Growth() {
  const [scenarios, setScenarios] = useState<Record<string, any>>({});
  const [req, setReq] = useState({ scenario: "s1_plan_cfd_1pct", start_eur: 500, monthly_eur: 100, years: 10, risk_pct: "", tax_rate: 0 });
  const [res, setRes] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api("/growth/scenarios").then(setScenarios); }, []);

  const run = async () => {
    setBusy(true);
    try {
      setRes(await api("/growth/simulate", { method: "POST", json: {
        scenario: req.scenario, start_eur: Number(req.start_eur), monthly_eur: Number(req.monthly_eur), years: Number(req.years),
        risk_fraction: req.risk_pct === "" ? null : Number(req.risk_pct) / 100, tax_rate: Number(req.tax_rate), n_paths: 2000 } }));
    } finally { setBusy(false); }
  };
  const set = (k: string) => (e: any) => setReq({ ...req, [k]: e.target.value });

  const compare = useMemo(() => {
    if (!res) return [];
    return res.fan.map((f: any, i: number) => ({
      month: f.month, trading: f.p50, etf: res.etf?.fan?.[i]?.p50,
      contributed: Number(req.start_eur) + Number(req.monthly_eur) * f.month,
    }));
  }, [res, req.start_eur, req.monthly_eur]);

  const last = res?.checkpoints?.[res.checkpoints.length - 1];
  const etfLast = res?.etf?.checkpoints?.[res.etf.checkpoints.length - 1];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Own-capital growth planner</h1>
        <p className="mt-1 max-w-3xl text-sm text-muted">Start balance plus a monthly contribution, traded with an assumed edge — compared with putting the same
          money into an index ETF. Small accounts are limited by position-size granularity (one MES contract ≈ $110 risk) and costs, both modelled.</p>
      </div>
      <Card title="Inputs">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
          <div className="col-span-2"><Field label="Scenario"><select className="input" value={req.scenario} onChange={set("scenario")}>
            {Object.entries(scenarios).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}</select></Field></div>
          <Field label="Start (€)"><input className="input" type="number" value={req.start_eur} onChange={set("start_eur")} /></Field>
          <Field label="Monthly (€)"><input className="input" type="number" value={req.monthly_eur} onChange={set("monthly_eur")} /></Field>
          <Field label="Years"><input className="input" type="number" min={1} max={30} value={req.years} onChange={set("years")} /></Field>
          <Field label="Risk % / trade (override)"><input className="input" placeholder={scenarios[req.scenario] ? String(scenarios[req.scenario].risk_fraction * 100) : ""} value={req.risk_pct} onChange={set("risk_pct")} /></Field>
          <Field label="Tax on gains"><select className="input" value={req.tax_rate} onChange={set("tax_rate")}>
            <option value={0}>pre-tax</option><option value={0.3}>30 % flat</option><option value={0.25}>25 %</option></select></Field>
        </div>
        <button className="btn mt-3" onClick={run} disabled={busy}><Play className="h-4 w-4" />{busy ? "Simulating…" : "Simulate"}</button>
      </Card>

      {res && last && (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <Stat label={`Put in after ${last.years} y`} value={eur(last.contributed_eur)} />
            <Stat label="Median outcome" value={eur(last.median)} tone={last.median >= last.contributed_eur ? "pos" : "neg"} sub={`mean ${eur(last.mean)}`} />
            <Stat label="Bad case (5th pct)" value={eur(last.p05)} tone="neg" sub={`good case (95th) ${eur(last.p95)}`} />
            <Stat label="P(end below money put in)" value={pct(last.p_below_contributed)} sub={`median worst drawdown ${pct(last.median_max_drawdown)}`} />
            <Stat label="Index ETF median (same money)" value={eur(etfLast?.median)} sub={etfLast ? `P(below put in) ${pct(etfLast.p_below_contributed)}` : ""} />
          </div>
          <Card title="Median path: trading vs ETF vs money put in"><MedianCompare data={compare} /></Card>
          <Card title="Trading account value — 5/25/50/75/95th percentiles"><FanChart data={res.fan} xKey="month" xLabel="month" currency="€" /></Card>
          <Card title="Checkpoints">
            <div className="overflow-x-auto">
              <table className="data">
                <thead><tr><th>years</th><th>put in</th><th>p05</th><th>median</th><th>mean</th><th>p95</th><th>P(below put in)</th><th>ETF median</th></tr></thead>
                <tbody>
                  {res.checkpoints.map((c: any, i: number) => (
                    <tr key={c.years}>
                      <td>{c.years}</td><td>{eur(c.contributed_eur)}</td><td>{eur(c.p05)}</td><td className="font-semibold">{eur(c.median)}</td>
                      <td>{eur(c.mean)}</td><td>{eur(c.p95)}</td><td>{pct(c.p_below_contributed)}</td><td>{eur(res.etf?.checkpoints?.[i]?.median)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              {res.model && <Badge tone="accent">edge {res.model.expected_net_r?.toFixed(3)} R/trade (MES costs) · Sharpe {res.model.annual_sharpe?.toFixed(2)}</Badge>}
              {res.vehicle && <Badge>{res.vehicle.name}</Badge>}
              <Badge tone="warn">assumed edge — not validated on real data</Badge>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
