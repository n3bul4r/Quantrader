"use client";

import clsx from "clsx";
import { Activity, BarChart3, BookOpen, FlaskConical, Gauge, Moon, ShieldAlert, Sun, Trophy } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

const NAV = [
  { href: "/", label: "Overview", icon: Gauge },
  { href: "/risk", label: "Risk", icon: ShieldAlert },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/journal", label: "Journal", icon: BookOpen },
  { href: "/backtest", label: "Backtest", icon: FlaskConical },
  { href: "/prop", label: "Prop simulator", icon: Trophy },
];

export default function Shell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  useEffect(() => {
    try {
      const t = (localStorage.getItem("qt-theme") as "dark" | "light") || "dark";
      setTheme(t);
      document.documentElement.dataset.theme = t;
    } catch {}
  }, []);
  const toggle = () => {
    const t = theme === "dark" ? "light" : "dark";
    setTheme(t);
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem("qt-theme", t); } catch {}
  };
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="flex shrink-0 items-center gap-1 overflow-x-auto border-b border-line bg-panel px-3 py-2 md:w-56 md:flex-col md:items-stretch md:border-b-0 md:border-r md:px-3 md:py-4">
        <div className="mr-3 flex items-center gap-2 px-2 md:mb-4 md:mr-0">
          <Activity className="h-5 w-5 text-accent" />
          <span className="font-semibold tracking-tight">Quantrader</span>
        </div>
        {NAV.map(({ href, label, icon: Icon }) => (
          <Link key={href} href={href}
            className={clsx("flex items-center gap-2 whitespace-nowrap rounded-md px-2 py-1.5 text-sm",
              path === href ? "bg-accent/15 text-accent" : "text-muted hover:bg-panel2 hover:text-fg")}>
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        ))}
        <button onClick={toggle} className="ml-auto flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted hover:bg-panel2 md:ml-0 md:mt-auto" aria-label="Toggle theme">
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          <span className="hidden md:inline">{theme === "dark" ? "Light" : "Dark"} mode</span>
        </button>
      </aside>
      <main className="min-w-0 flex-1 px-4 py-5 md:px-8">{children}</main>
    </div>
  );
}
