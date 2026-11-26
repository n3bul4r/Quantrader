"use client";

import { useEffect, useState } from "react";
import { BarsChart, DrawdownChart, EquityChart, SmallLine } from "@/components/charts";
import { Card, Empty, Stat } from "@/components/ui";
import { api, num, pct, signClass, usd } from "@/lib/api";

function Table({ rows, keyCol }: { rows: any[]; keyCol: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="data">
        <thead><tr><th>{keyCol}</th><th>n</th><th>win %</th><th>exp $</th><th>exp R</th><th>PF</th><th>total</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r[keyCol]}>
              <td className="font-sans">{r[keyCol]}</td><td>{r.n}</td><td>{pct(r.win_rate)}</td>
              <td className={signClass(r.expectancy)}>{usd(r.expectancy, 1)}</td><td>{num(r.expectancy_r)}</td>
              <td>{num(r.profit_factor)}</td><td className={signClass(r.total)}>{usd(r.total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Analytics() {
  const [a, setA] = useState<any>(null);
  useEffect(() => { api("/journal/analytics").then(setA).catch(() => setA({ empty: true })); }, []);
  if (!a) return <div className="text-sm text-muted">Loading…</div>;
  if (a.empty) return <Empty>No journal trades yet.</Empty>;
  const t = a.trades, d = a.daily;
  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold tracking-tight">Strategy analytics</h1>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
        <Stat label="Trades" value={t.n} sub={`${d.days} days`} />
        <Stat label="Win rate" value={pct(t.win_rate, 1)} sub={`payoff ${num(t.payoff_ratio)}`} />
        <Stat label="Expectancy" value={usd(t.expectancy, 1)} tone={t.expectancy > 0 ? "pos" : "neg"} sub={`${num(t.expectancy_r, 3)} R · t=${num(t.t_stat)}`} />
        <Stat label="Profit factor" value={num(t.profit_factor)} />
        <Stat label="Sharpe (ann.)" value={num(d.sharpe_annual)} sub={`PSR ${pct(d.psr_vs_0)}`} />
        <Stat label="Max drawdown" value={usd(d.max_drawdown)} tone="neg" sub={`${d.max_dd_duration_days} days · best-day share ${pct(d.best_day_share)}`} />
      </div>
      <Card title="Equity curve"><EquityChart data={a.equity} height={260} /></Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Drawdown"><DrawdownChart data={a.drawdown} /></Card>
        <Card title="Rolling 30-trade expectancy ($)"><SmallLine data={a.rolling_expectancy} x="i" y="exp" /></Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="P&L by session"><BarsChart data={a.by_session} x="session" y="total" /><Table rows={a.by_session} keyCol="session" /></Card>
        <Card title="By strategy"><Table rows={a.by_strategy} keyCol="strategy" /></Card>
      </div>
      <Card title="By automatic tag (worst first)"><Table rows={a.by_tag} keyCol="tags" /></Card>
    </div>
  );
}
