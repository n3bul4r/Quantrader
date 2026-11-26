"""Real-time risk guard: the pre-trade and in-trade checks the dashboard/execution layer
runs before every order. Deterministic and stateless (state is passed in) so it can be
unit-tested and called from the API, a webhook, or the execution bot."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import time


@dataclass
class GuardConfig:
    internal_daily_stop: float = 400.0     # personal daily stop, tighter than the firm DLL
    firm_daily_loss_limit: float | None = 1000.0
    daily_profit_target: float = 250.0     # soft: start protecting gains past this
    daily_profit_cap: float | None = 1200.0  # hard: stop trading (consistency-rule protection)
    profit_lock_giveback: float = 0.4      # after target hit, stop if 40% of peak day P&L is given back
    max_trades_per_day: int = 4
    max_consecutive_losses: int = 3
    min_minutes_between_trades_after_loss: int = 10   # anti-revenge
    mll_warning_buffer: float = 600.0      # alert when equity is within this of the MLL
    min_buffer_to_trade: float = 250.0     # do not open trades with less buffer than this
    blackout_windows: list[tuple[str, str]] = field(default_factory=lambda: [("09:30", "09:35"), ("15:58", "16:00")])
    flatten_by: str = "15:59"


@dataclass
class GuardState:
    now: str                    # "HH:MM" ET
    day_pnl: float              # realized + unrealized today
    day_peak_pnl: float
    trades_today: int
    consecutive_losses: int
    minutes_since_last_loss: float | None
    equity: float               # account balance incl. open P&L (relative or absolute, same units as mll_level)
    mll_level: float
    open_position: bool = False
    event_blackout: bool = False   # e.g. FOMC 14:00, scheduled from the economic calendar


@dataclass
class GuardDecision:
    allow_new_trade: bool
    flatten_now: bool
    max_risk_dollars: float
    reasons: list[str]
    alerts: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


def _t(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def evaluate(cfg: GuardConfig, st: GuardState) -> GuardDecision:
    reasons, alerts = [], []
    allow, flatten = True, False
    now = _t(st.now)
    buffer = st.equity - st.mll_level

    def alert(level: str, msg: str):
        alerts.append({"level": level, "message": msg})

    # hard stops
    if st.day_pnl <= -cfg.internal_daily_stop:
        allow, flatten = False, True
        reasons.append("internal daily stop reached")
        alert("critical", f"Daily stop hit ({st.day_pnl:,.0f}). Flatten and stop for the day.")
    if cfg.firm_daily_loss_limit is not None and st.day_pnl <= -0.8 * cfg.firm_daily_loss_limit:
        allow = False
        flatten = flatten or st.day_pnl <= -0.9 * cfg.firm_daily_loss_limit
        alert("critical", f"Within 20% of the firm daily loss limit ({cfg.firm_daily_loss_limit:,.0f}).")
    if cfg.daily_profit_cap is not None and st.day_pnl >= cfg.daily_profit_cap:
        allow, flatten = False, True
        reasons.append("daily profit cap reached (consistency protection)")
        alert("info", "Profit cap reached — banking the day to protect the consistency rule.")
    if st.day_peak_pnl >= cfg.daily_profit_target and st.day_pnl <= (1 - cfg.profit_lock_giveback) * st.day_peak_pnl:
        allow, flatten = False, True
        reasons.append("profit lock: gave back too much of the day's peak")
        alert("warning", "Profit lock triggered.")
    if st.trades_today >= cfg.max_trades_per_day:
        allow = False
        reasons.append("max trades per day")
    if st.consecutive_losses >= cfg.max_consecutive_losses:
        allow = False
        reasons.append("max consecutive losses")
        alert("warning", f"{st.consecutive_losses} losses in a row — done for the day.")
    if (st.minutes_since_last_loss is not None and st.minutes_since_last_loss < cfg.min_minutes_between_trades_after_loss):
        allow = False
        reasons.append("cool-down after loss (anti-revenge)")
    if buffer <= cfg.min_buffer_to_trade:
        allow = False
        reasons.append("drawdown buffer too small")
        alert("critical", f"Only ${buffer:,.0f} above the max-loss level.")
    elif buffer <= cfg.mll_warning_buffer:
        alert("warning", f"Buffer to max-loss level is ${buffer:,.0f}.")
    for a, b in cfg.blackout_windows:
        if _t(a) <= now < _t(b):
            allow = False
            reasons.append(f"blackout window {a}-{b}")
    if st.event_blackout:
        allow = False
        reasons.append("scheduled-event blackout")
    if now >= _t(cfg.flatten_by):
        allow = False
        flatten = flatten or st.open_position
        reasons.append("past flatten time")

    remaining_day = st.day_pnl + cfg.internal_daily_stop
    if cfg.firm_daily_loss_limit is not None:
        remaining_day = min(remaining_day, st.day_pnl + 0.8 * cfg.firm_daily_loss_limit)
    max_risk = max(0.0, min(remaining_day, buffer - cfg.min_buffer_to_trade)) if allow else 0.0
    if st.day_pnl >= cfg.daily_profit_target and allow:
        # past the soft target only risk house money beyond the target
        max_risk = min(max_risk, max(0.0, st.day_pnl - cfg.daily_profit_target) + 0.25 * cfg.daily_profit_target)
    return GuardDecision(allow, flatten, max_risk, reasons, alerts)
