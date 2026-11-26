"""Prop-firm rule model + preset loading."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import yaml

PRESET_FILE = Path(__file__).parent / "presets" / "programs.yaml"


@dataclass
class PhaseRules:
    max_loss: float
    profit_target: float | None = None
    drawdown_type: str = "eod_trailing"       # eod_trailing | intraday_trailing | static
    lock_level: float | None = 0.0
    daily_loss_limit: float | None = None
    dll_action: str = "pause"
    consistency_pct: float | None = None
    min_trading_days: int = 0
    max_micros: int = 50
    scaling_plan: list = field(default_factory=list)  # [[profit_threshold, max_micros], ...]
    # payouts (funded phase)
    payout_winning_days: int = 0
    winning_day_threshold: float = 0.0
    payout_fraction: float = 0.5
    payout_cap: float | None = None
    payout_min: float = 0.0
    profit_split: float = 0.9
    full_split_first: float = 0.0
    payout_consistency_pct: float | None = None
    mll_after_payout: str = "unchanged"
    payout_reserve: float = 0.0               # profit that must stay in the account

    def max_micros_at(self, profit: float) -> int:
        if not self.scaling_plan:
            return self.max_micros
        allowed = self.scaling_plan[0][1]
        for thr, n in self.scaling_plan:
            if profit >= thr:
                allowed = n
        return min(allowed, self.max_micros)


@dataclass
class PropProgram:
    key: str
    firm: str
    name: str
    account_size: float
    evaluation: PhaseRules
    funded: PhaseRules
    eval_fee: float
    eval_fee_recurring_days: int | None = None
    activation_fee: float = 0.0
    max_accounts: int = 1
    automation: str = ""
    last_checked: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _phase(d: dict) -> PhaseRules:
    known = {f.name for f in fields(PhaseRules)}
    return PhaseRules(**{k: v for k, v in d.items() if k in known})


def program_from_dict(key: str, d: dict) -> PropProgram:
    d = dict(d)
    ev, fu = _phase(d.pop("evaluation")), _phase(d.pop("funded"))
    known = {f.name for f in fields(PropProgram)}
    return PropProgram(key=key, evaluation=ev, funded=fu, **{k: v for k, v in d.items() if k in known})


def load_presets(path: Path | str = PRESET_FILE) -> dict[str, PropProgram]:
    raw = yaml.safe_load(Path(path).read_text())
    return {k: program_from_dict(k, v) for k, v in raw.items()}


def get_program(key: str) -> PropProgram:
    presets = load_presets()
    if key not in presets:
        raise KeyError(f"Unknown program {key!r}; known: {sorted(presets)}")
    return presets[key]
