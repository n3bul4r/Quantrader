"use client";

import clsx from "clsx";
import type { ReactNode } from "react";

export function Card({ title, right, children, className }: { title?: ReactNode; right?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={clsx("card", className)}>
      {(title || right) && (
        <header className="mb-3 flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">{title}</h2>
          {right}
        </header>
      )}
      {children}
    </section>
  );
}

const TONE: Record<string, string> = { pos: "text-pos", neg: "text-neg", warn: "text-warn" };

export function Stat({ label, value, sub, tone }: { label: string; value: ReactNode; sub?: ReactNode; tone?: "pos" | "neg" | "warn" | "" }) {
  return (
    <div className="card">
      <div className="label">{label}</div>
      <div className={clsx("mt-1 text-2xl font-semibold num", tone && TONE[tone])}>{value}</div>
      {sub && <div className="mt-0.5 text-xs text-muted">{sub}</div>}
    </div>
  );
}

/** Horizontal meter: how much of a limit is consumed. */
export function Meter({ label, used, limit, invert = false, format }: {
  label: string; used: number; limit: number; invert?: boolean; format: (x: number) => string;
}) {
  const frac = limit > 0 ? Math.min(Math.max(used / limit, 0), 1) : 0;
  const danger = invert ? frac < 0.25 : frac > 0.75;
  const warn = invert ? frac < 0.5 : frac > 0.5;
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span className="text-muted">{label}</span>
        <span className="num">{format(used)} / {format(limit)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-panel2">
        <div className={clsx("h-full rounded-full", danger ? "bg-neg" : warn ? "bg-warn" : "bg-pos")} style={{ width: `${frac * 100}%` }} />
      </div>
    </div>
  );
}

export function Badge({ children, tone = "muted" }: { children: ReactNode; tone?: "pos" | "neg" | "warn" | "muted" | "accent" }) {
  const map: Record<string, string> = {
    pos: "bg-pos/15 text-pos", neg: "bg-neg/15 text-neg", warn: "bg-warn/15 text-warn",
    muted: "bg-panel2 text-muted", accent: "bg-accent/15 text-accent",
  };
  return <span className={clsx("inline-block rounded px-1.5 py-0.5 text-[11px] font-medium", map[tone])}>{children}</span>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="rounded-lg border border-dashed border-line p-6 text-center text-sm text-muted">{children}</div>;
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="label mb-1 block">{label}</span>
      {children}
    </label>
  );
}
