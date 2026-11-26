"""Deterministic prop-account tracker for a REAL account: feed it each closed trading day
(and optionally intraday equity extremes) and it reports rule status — the 'rule
checker' panel of the dashboard."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .rules import PhaseRules, PropProgram


@dataclass
class AccountState:
    phase: str = "evaluation"
    profit: float = 0.0           # balance - starting balance
    mll: float = 0.0              # max-loss level relative to start
    hwm: float = 0.0
    best_day: float = 0.0
    trading_days: int = 0
    winning_days_since_payout: int = 0
    profit_since_payout: float = 0.0
    best_day_since_payout: float = 0.0
    payouts: list = field(default_factory=list)
    status: str = "active"        # active | passed | failed
    history: list = field(default_factory=list)


class PropAccountTracker:
    def __init__(self, program: PropProgram, phase: str = "evaluation"):
        self.program = program
        self.state = AccountState(phase=phase)
        self.state.mll = -self.rules.max_loss

    @property
    def rules(self) -> PhaseRules:
        return self.program.evaluation if self.state.phase == "evaluation" else self.program.funded

    def _trail(self, peak: float) -> None:
        r = self.rules
        if r.drawdown_type == "static":
            return
        new = peak - r.max_loss
        if r.lock_level is not None:
            new = min(new, r.lock_level)
        self.state.mll = max(self.state.mll, new)

    def apply_day(self, day_pnl: float, intraday_low: float | None = None, intraday_high: float | None = None,
                  traded: bool = True) -> dict:
        """intraday_low/high: worst / best open-equity P&L of the day relative to the day start."""
        s, r = self.state, self.rules
        if s.status != "active":
            raise RuntimeError(f"account is {s.status}")
        low = min(day_pnl, intraday_low if intraday_low is not None else day_pnl)
        high = max(day_pnl, intraday_high if intraday_high is not None else day_pnl)
        events = []
        if r.drawdown_type == "intraday_trailing":
            self._trail(s.profit + high)
        if s.profit + low <= s.mll:
            s.status = "failed"
            events.append("max loss limit breached")
        if r.daily_loss_limit is not None and low <= -r.daily_loss_limit:
            events.append("daily loss limit hit" + (" (account failed)" if r.dll_action == "fail" else " (day paused)"))
            if r.dll_action == "fail":
                s.status = "failed"
        s.profit += day_pnl
        s.trading_days += int(traded)
        s.best_day = max(s.best_day, day_pnl)
        s.hwm = max(s.hwm, s.profit)
        if r.drawdown_type == "eod_trailing":
            self._trail(s.hwm)
        if s.phase == "funded":
            s.profit_since_payout += day_pnl
            s.best_day_since_payout = max(s.best_day_since_payout, day_pnl)
            if day_pnl >= r.winning_day_threshold:
                s.winning_days_since_payout += 1
        if s.status == "active" and s.phase == "evaluation" and self.eval_passed():
            s.status = "passed"
            events.append("evaluation passed")
        s.history.append({"day_pnl": day_pnl, "profit": s.profit, "mll": s.mll, "events": events})
        return {**self.status(), "events": events}

    def eval_passed(self) -> bool:
        s, r = self.state, self.rules
        if r.profit_target is None or s.profit < r.profit_target or s.trading_days < r.min_trading_days:
            return False
        return r.consistency_pct is None or s.best_day <= r.consistency_pct * s.profit

    def max_profit_today_consistent(self) -> float | None:
        """Largest profit today that keeps the consistency rule satisfied *if today becomes the best day*:
        x <= c * (P + x)  =>  x <= c * P / (1 - c). None when no rule applies."""
        s, r = self.state, self.rules
        c = r.consistency_pct if s.phase == "evaluation" else r.payout_consistency_pct
        if c is None:
            return None
        base = s.profit if s.phase == "evaluation" else s.profit_since_payout
        return max(s.best_day if s.phase == "evaluation" else s.best_day_since_payout, c * max(base, 0) / (1 - c))

    def payout_eligible(self) -> tuple[bool, float, list[str]]:
        s, r = self.state, self.rules
        why = []
        if s.phase != "funded":
            return False, 0.0, ["not funded"]
        if s.winning_days_since_payout < r.payout_winning_days:
            why.append(f"{s.winning_days_since_payout}/{r.payout_winning_days} winning days (>= ${r.winning_day_threshold:,.0f})")
        avail = max(0.0, s.profit - r.payout_reserve)
        amount = r.payout_fraction * avail
        if r.payout_cap is not None:
            amount = min(amount, r.payout_cap)
        if amount < r.payout_min:
            why.append(f"payout amount ${amount:,.0f} below minimum ${r.payout_min:,.0f}")
        c = r.payout_consistency_pct
        if c is not None and s.profit_since_payout > 0 and s.best_day_since_payout > c * s.profit_since_payout:
            why.append("payout consistency rule not met")
        return (not why), amount, why

    def take_payout(self) -> float:
        ok, amount, why = self.payout_eligible()
        if not ok:
            raise RuntimeError("; ".join(why))
        s, r = self.state, self.rules
        s.profit -= amount
        s.payouts.append(amount)
        s.winning_days_since_payout = 0
        s.profit_since_payout = 0.0
        s.best_day_since_payout = 0.0
        if r.mll_after_payout == "lock_at_start":
            s.mll = max(s.mll, 0.0)
        return amount

    def promote_to_funded(self) -> None:
        if self.state.status != "passed":
            raise RuntimeError("evaluation not passed")
        self.state = AccountState(phase="funded")
        self.state.mll = -self.program.funded.max_loss

    def status(self) -> dict:
        s, r = self.state, self.rules
        buffer = s.profit - s.mll
        out = {
            "phase": s.phase, "status": s.status, "profit": s.profit, "balance": self.program.account_size + s.profit,
            "mll_level": self.program.account_size + s.mll, "buffer_to_mll": buffer,
            "buffer_pct_of_max_loss": buffer / r.max_loss,
            "trailing_locked": r.lock_level is not None and s.mll >= r.lock_level,
            "daily_loss_limit": r.daily_loss_limit, "trading_days": s.trading_days,
            "best_day": s.best_day, "max_profit_today_consistent": self.max_profit_today_consistent(),
        }
        if s.phase == "evaluation" and r.profit_target:
            out["target_remaining"] = max(0.0, r.profit_target - s.profit)
            out["best_day_share"] = s.best_day / s.profit if s.profit > 0 else None
        else:
            ok, amt, why = self.payout_eligible()
            out.update({"payout_eligible": ok, "payout_amount": amt, "payout_blockers": why,
                        "winning_days_since_payout": s.winning_days_since_payout, "payouts": list(s.payouts)})
        return out

    def to_dict(self) -> dict:
        return {"program": self.program.key, "state": asdict(self.state), "status": self.status()}
