"use client";

import { Plus } from "lucide-react";
import { useEffect, useState } from "react";
import { Badge, Card, Empty, Field } from "@/components/ui";
import { api, num, signClass, usd } from "@/lib/api";

const blank = { date: new Date().toISOString().slice(0, 10), entry_time: "10:00", exit_time: "11:00", side: 1, pnl: 0,
  symbol: "MES", strategy: "S1", contracts: 1, risk_dollars: 200, exit_reason: "", notes: "" };

function tone(tag: string): "neg" | "warn" | "pos" | "muted" | "accent" {
  if (tag.startsWith("violation")) return "neg";
  if (tag.startsWith("behaviour") || tag.startsWith("news")) return "warn";
  if (tag.startsWith("outcome:big_win")) return "pos";
  if (tag.startsWith("strategy")) return "accent";
  return "muted";
}

export default function Journal() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [f, setF] = useState<any>(blank);
  const load = () => api("/journal/analytics").then((a) => setRows(a.empty ? [] : a.recent.slice().reverse()));
  useEffect(() => { load(); }, []);
  const add = async () => {
    await api("/journal/trades", { method: "POST", json: [{ ...f, side: Number(f.side), pnl: Number(f.pnl), contracts: Number(f.contracts),
      risk_dollars: Number(f.risk_dollars), r_net: Number(f.risk_dollars) ? Number(f.pnl) / Number(f.risk_dollars) : null }] });
    setF(blank); load();
  };
  const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.value });
  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold tracking-tight">Trade journal</h1>
      <Card title="Log a trade" right={<span className="text-xs text-muted">tags are assigned automatically</span>}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
          <Field label="Date"><input className="input" type="date" value={f.date} onChange={set("date")} /></Field>
          <Field label="Entry (ET)"><input className="input" value={f.entry_time} onChange={set("entry_time")} /></Field>
          <Field label="Exit (ET)"><input className="input" value={f.exit_time} onChange={set("exit_time")} /></Field>
          <Field label="Side"><select className="input" value={f.side} onChange={set("side")}><option value={1}>Long</option><option value={-1}>Short</option></select></Field>
          <Field label="Symbol"><select className="input" value={f.symbol} onChange={set("symbol")}>{["MES", "MNQ", "ES", "NQ", "MGC", "MCL"].map((s) => <option key={s}>{s}</option>)}</select></Field>
          <Field label="Strategy"><select className="input" value={f.strategy} onChange={set("strategy")}>{["S1", "S2", "S3", "discretionary"].map((s) => <option key={s}>{s}</option>)}</select></Field>
          <Field label="Contracts"><input className="input" type="number" value={f.contracts} onChange={set("contracts")} /></Field>
          <Field label="Risk $ (stop)"><input className="input" type="number" value={f.risk_dollars} onChange={set("risk_dollars")} /></Field>
          <Field label="Net P&L $"><input className="input" type="number" value={f.pnl} onChange={set("pnl")} /></Field>
          <Field label="Exit reason"><input className="input" value={f.exit_reason} onChange={set("exit_reason")} placeholder="stop / time / target" /></Field>
          <div className="col-span-2"><Field label="Notes"><input className="input" value={f.notes} onChange={set("notes")} /></Field></div>
        </div>
        <button className="btn mt-3" onClick={add}><Plus className="h-4 w-4" />Add trade</button>
      </Card>
      <Card title="Recent trades (last 50)">
        {!rows ? <div className="text-sm text-muted">Loading…</div> : !rows.length ? <Empty>No trades.</Empty> : (
          <div className="overflow-x-auto">
            <table className="data">
              <thead><tr><th>date</th><th>time</th><th>sym</th><th>side</th><th>ct</th><th>P&L</th><th>R</th><th>exit</th><th>tags</th></tr></thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i}>
                    <td>{r.date}</td><td>{r.entry_time}→{r.exit_time}</td><td>{r.symbol}</td><td>{r.side > 0 ? "L" : "S"}</td><td>{r.contracts}</td>
                    <td className={signClass(r.pnl)}>{usd(r.pnl)}</td><td>{num(r.r_net)}</td><td className="font-sans">{r.exit_reason}</td>
                    <td className="font-sans"><div className="flex flex-wrap gap-1">{(r.tags || []).filter((t: string) => !t.startsWith("side")).map((t: string) => <Badge key={t} tone={tone(t)}>{t}</Badge>)}</div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
