"""Automatic trade tagging for the journal.

Tags are deterministic rules so that analytics can slice performance by them, and —
more importantly — so that *behavioural* errors (oversizing, revenge trades, trading
after the daily stop) are surfaced automatically instead of relying on self-report.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class TagConfig:
    planned_risk: float = 200.0           # $ per trade per plan
    oversize_tolerance: float = 1.25
    revenge_minutes: int = 10
    internal_daily_stop: float = 400.0
    max_trades_per_day: int = 4
    news_window_min: int = 15
    events: list[tuple[str, str, str]] = field(default_factory=list)  # (YYYY-MM-DD, HH:MM, name) ET


def _minutes(hhmm: str) -> int:
    h, m = str(hhmm).split(":")[:2]
    return int(h) * 60 + int(m)


def session_bucket(hhmm: str) -> str:
    m = _minutes(hhmm)
    if m < 9 * 60 + 30:
        return "session:pre_market"
    if m < 10 * 60 + 30:
        return "session:open_drive"      # 09:30-10:30
    if m < 12 * 60:
        return "session:morning"
    if m < 14 * 60:
        return "session:midday"
    if m < 15 * 60:
        return "session:afternoon"
    return "session:power_hour"


def tag_trades(trades: pd.DataFrame, cfg: TagConfig | None = None, context: pd.DataFrame | None = None) -> pd.DataFrame:
    """trades: columns date, entry_time, exit_time, side, pnl, risk_dollars (optional), strategy,
    exit_reason (optional), r_net (optional). context (optional, indexed by date): regime, day_type."""
    cfg = cfg or TagConfig()
    df = trades.copy().sort_values(["date", "entry_time"]).reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    events = [(pd.Timestamp(d), _minutes(t), n) for d, t, n in cfg.events]
    tags_all = []
    day_state: dict = {}
    for i, row in df.iterrows():
        tags = [session_bucket(row["entry_time"]), "side:long" if row.get("side", 1) > 0 else "side:short"]
        if "strategy" in row and pd.notna(row["strategy"]):
            tags.append(f"strategy:{row['strategy']}")
        er = row.get("exit_reason")
        if isinstance(er, str):
            tags.append(f"exit:{er}")
        hold = _minutes(row["exit_time"]) - _minutes(row["entry_time"]) if "exit_time" in row else None
        if hold is not None:
            tags.append("hold:<15m" if hold < 15 else "hold:15-60m" if hold < 60 else "hold:1-3h" if hold < 180 else "hold:>3h")
        r = row.get("r_net")
        if r is not None and pd.notna(r):
            tags.append("outcome:big_win" if r >= 2 else "outcome:win" if r > 0 else "outcome:scratch" if r > -0.25 else "outcome:loss")
        # behavioural checks (need per-day running state)
        st = day_state.setdefault(row["date"], {"pnl": 0.0, "n": 0, "last_loss_exit": None})
        entry_m = _minutes(row["entry_time"])
        rd = row.get("risk_dollars")
        if rd is not None and pd.notna(rd) and rd > cfg.oversize_tolerance * cfg.planned_risk:
            tags.append("violation:oversized")
        if st["pnl"] <= -cfg.internal_daily_stop:
            tags.append("violation:after_daily_stop")
        if st["n"] >= cfg.max_trades_per_day:
            tags.append("violation:overtrading")
        if st["last_loss_exit"] is not None and entry_m - st["last_loss_exit"] < cfg.revenge_minutes:
            tags.append("behaviour:possible_revenge")
        for d, t, name in events:
            if d.normalize() == row["date"].normalize() and abs(entry_m - t) <= cfg.news_window_min:
                tags.append(f"news:{name}")
        if context is not None and row["date"] in context.index:
            c = context.loc[row["date"]]
            if "regime" in c:
                tags.append({1: "regime:high_vol", -1: "regime:low_vol"}.get(int(c["regime"]), "regime:unknown"))
            if "day_type" in c:
                tags.append(f"day:{c['day_type']}")
        st["pnl"] += float(row.get("pnl", 0.0))
        st["n"] += 1
        if row.get("pnl", 0.0) < 0:
            st["last_loss_exit"] = _minutes(row["exit_time"]) if "exit_time" in row else entry_m
        tags_all.append(tags)
    df["tags"] = tags_all
    return df


def tag_summary(tagged: pd.DataFrame) -> pd.DataFrame:
    """Performance by tag (one trade counts toward each of its tags)."""
    ex = tagged.explode("tags")
    g = ex.groupby("tags")
    out = pd.DataFrame({
        "n": g.size(),
        "win_rate": g["pnl"].apply(lambda x: (x > 0).mean()),
        "expectancy": g["pnl"].mean(),
        "total": g["pnl"].sum(),
    })
    return out.sort_values("total")
