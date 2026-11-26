"use client";

import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const axis = { stroke: "rgb(var(--muted))", fontSize: 11, tickLine: false, axisLine: false } as const;
const grid = <CartesianGrid stroke="rgb(var(--line))" strokeDasharray="3 3" vertical={false} />;
const tip = {
  contentStyle: { background: "rgb(var(--panel2))", border: "1px solid rgb(var(--line))", borderRadius: 8, fontSize: 12 },
  labelStyle: { color: "rgb(var(--muted))" },
};
const money = (v: number) => `${v < 0 ? "−" : ""}$${Math.abs(v).toLocaleString("en-US", { maximumFractionDigits: 0 })}`;

export function EquityChart({ data, height = 240, refLines = [] }: {
  data: { date: string; equity: number }[]; height?: number; refLines?: { y: number; label: string; color: string }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgb(var(--accent))" stopOpacity={0.35} />
            <stop offset="100%" stopColor="rgb(var(--accent))" stopOpacity={0} />
          </linearGradient>
        </defs>
        {grid}
        <XAxis dataKey="date" {...axis} minTickGap={40} />
        <YAxis {...axis} tickFormatter={money} width={64} />
        <Tooltip {...tip} formatter={(v: number) => money(v)} />
        {refLines.map((r) => (
          <ReferenceLine key={r.label} y={r.y} stroke={r.color} strokeDasharray="4 4" label={{ value: r.label, fill: r.color, fontSize: 10, position: "insideTopLeft" }} />
        ))}
        <Area type="monotone" dataKey="equity" stroke="rgb(var(--accent))" strokeWidth={2} fill="url(#eq)" dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function DrawdownChart({ data, height = 140 }: { data: { date: string; dd: number }[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        {grid}
        <XAxis dataKey="date" {...axis} minTickGap={40} />
        <YAxis {...axis} tickFormatter={money} width={64} />
        <Tooltip {...tip} formatter={(v: number) => money(v)} />
        <Area type="monotone" dataKey="dd" stroke="rgb(var(--neg))" fill="rgb(var(--neg))" fillOpacity={0.2} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function BarsChart({ data, x, y, height = 200, money: isMoney = true, positive }: {
  data: any[]; x: string; y: string; height?: number; money?: boolean; positive?: (d: any) => boolean;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        {grid}
        <XAxis dataKey={x} {...axis} />
        <YAxis {...axis} tickFormatter={isMoney ? money : undefined} width={64} />
        <Tooltip {...tip} formatter={(v: number) => (isMoney ? money(v) : v)} />
        <ReferenceLine y={0} stroke="rgb(var(--line))" />
        <Bar dataKey={y} radius={[3, 3, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={(positive ? positive(d) : d[y] >= 0) ? "rgb(var(--pos))" : "rgb(var(--neg))"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function FanChart({ data, height = 260, xKey = "day", xLabel = "trading day", currency = "$" }: {
  data: any[]; height?: number; xKey?: string; xLabel?: string; currency?: string;
}) {
  const fmt = (v: number) => money(v).replace("$", currency);
  const rows = data.map((d) => ({ ...d, outer: [d.p05, d.p95], inner: [d.p25, d.p75] }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        {grid}
        <XAxis dataKey={xKey} {...axis} label={{ value: xLabel, position: "insideBottomRight", fill: "rgb(var(--muted))", fontSize: 10 }} />
        <YAxis {...axis} tickFormatter={fmt} width={64} />
        <Tooltip {...tip} formatter={(v: any) => (Array.isArray(v) ? `${fmt(v[0])} … ${fmt(v[1])}` : fmt(v))} />
        <ReferenceLine y={0} stroke="rgb(var(--muted))" />
        <Area dataKey="outer" stroke="none" fill="rgb(var(--accent))" fillOpacity={0.12} />
        <Area dataKey="inner" stroke="none" fill="rgb(var(--accent))" fillOpacity={0.25} />
        <Area dataKey="p50" stroke="rgb(var(--accent))" strokeWidth={2} fill="none" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function SweepChart({ data, height = 220 }: { data: { risk_dollars: number; net_mean: number; net_median: number }[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        {grid}
        <XAxis dataKey="risk_dollars" {...axis} tickFormatter={money} />
        <YAxis {...axis} tickFormatter={money} width={64} />
        <Tooltip {...tip} formatter={(v: number) => money(v)} labelFormatter={(l) => `risk ${money(Number(l))}/trade`} />
        <ReferenceLine y={0} stroke="rgb(var(--muted))" />
        <Line dataKey="net_mean" name="mean net / yr" stroke="rgb(var(--accent))" strokeWidth={2} dot />
        <Line dataKey="net_median" name="median net / yr" stroke="rgb(var(--warn))" strokeWidth={2} dot />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function SmallLine({ data, x, y, height = 140 }: { data: any[]; x: string; y: string; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        {grid}
        <XAxis dataKey={x} {...axis} minTickGap={30} />
        <YAxis {...axis} tickFormatter={money} width={64} />
        <Tooltip {...tip} formatter={(v: number) => money(v)} />
        <ReferenceLine y={0} stroke="rgb(var(--muted))" />
        <Line dataKey={y} stroke="rgb(var(--accent))" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function MedianCompare({ data, height = 240 }: { data: { month: number; trading: number; etf?: number; contributed: number }[]; height?: number }) {
  const eur = (v: number) => `€${Math.round(v).toLocaleString("en-US")}`;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        {grid}
        <XAxis dataKey="month" {...axis} label={{ value: "month", position: "insideBottomRight", fill: "rgb(var(--muted))", fontSize: 10 }} />
        <YAxis {...axis} tickFormatter={eur} width={64} />
        <Tooltip {...tip} formatter={(v: number) => eur(v)} />
        <Line dataKey="trading" name="trading (median)" stroke="rgb(var(--accent))" strokeWidth={2} dot={false} />
        <Line dataKey="etf" name="index ETF (median)" stroke="rgb(var(--warn))" strokeWidth={2} dot={false} />
        <Line dataKey="contributed" name="money put in" stroke="rgb(var(--muted))" strokeDasharray="4 4" strokeWidth={1.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
