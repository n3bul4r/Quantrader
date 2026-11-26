"""Contract specifications and an all-in transaction cost model.

Cost figures are *planning defaults* compiled in Nov 2026 from broker / prop-firm fee
pages (see docs/RESEARCH.md). Prop firms bundle exchange + clearing + NFA + commission;
quoted micro round-turns range ~$0.60 (cheap direct broker) to ~$1.90 (prop bundles).
Always override with your actual statement figures.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Instrument:
    symbol: str
    name: str
    tick_size: float          # price increment
    point_value: float        # $ per 1.0 price point per contract
    commission_rt: float      # all-in $ per contract round turn (fees + commission)
    slippage_ticks_entry: float = 1.0   # market / stop entry
    slippage_ticks_exit: float = 1.0    # stop or market exit
    is_micro: bool = True
    micro_equivalent: float = 1.0       # how many micros one contract counts as (prop limits)

    @property
    def tick_value(self) -> float:
        return self.tick_size * self.point_value

    def slippage_rt(self) -> float:
        """Expected slippage $ per contract per round turn."""
        return (self.slippage_ticks_entry + self.slippage_ticks_exit) * self.tick_value

    def cost_rt(self) -> float:
        """All-in expected cost $ per contract per round turn (commission + slippage)."""
        return self.commission_rt + self.slippage_rt()

    def cost_in_points(self) -> float:
        return self.cost_rt() / self.point_value

    def round_price(self, price: float) -> float:
        return round(price / self.tick_size) * self.tick_size


INSTRUMENTS: dict[str, Instrument] = {
    # Equity index micros — primary instruments
    "MES": Instrument("MES", "Micro E-mini S&P 500", 0.25, 5.0, 1.40),
    "MNQ": Instrument("MNQ", "Micro E-mini Nasdaq-100", 0.25, 2.0, 1.40),
    # Full-size (only once the account comfortably supports 10+ micros)
    "ES": Instrument("ES", "E-mini S&P 500", 0.25, 50.0, 4.20, is_micro=False, micro_equivalent=10),
    "NQ": Instrument("NQ", "E-mini Nasdaq-100", 0.25, 20.0, 4.20, is_micro=False, micro_equivalent=10),
    "M2K": Instrument("M2K", "Micro E-mini Russell 2000", 0.10, 5.0, 1.40),
    "M6E": Instrument("M6E", "Micro EUR/USD", 0.0001, 12500.0, 1.20),
    # Commodities
    "MGC": Instrument("MGC", "Micro Gold", 0.10, 10.0, 1.70),
    "MCL": Instrument("MCL", "Micro WTI Crude", 0.01, 100.0, 1.70, slippage_ticks_entry=1.5, slippage_ticks_exit=1.5),
}


def get_instrument(symbol: str) -> Instrument:
    try:
        return INSTRUMENTS[symbol.upper()]
    except KeyError as exc:  # pragma: no cover - trivial
        raise KeyError(f"Unknown instrument {symbol!r}; known: {sorted(INSTRUMENTS)}") from exc


@dataclass
class CostReport:
    """How much of a trade's risk is eaten by costs — the single most important
    viability number for intraday micro strategies."""
    symbol: str
    stop_points: float
    target_points: float
    risk_per_contract: float
    cost_per_contract: float
    cost_as_frac_of_risk: float
    cost_as_frac_of_target: float
    breakeven_winrate_gross: float
    breakeven_winrate_net: float
    notes: list[str] = field(default_factory=list)


def cost_report(symbol: str, stop_points: float, target_points: float) -> CostReport:
    ins = get_instrument(symbol)
    risk = stop_points * ins.point_value
    reward = target_points * ins.point_value
    cost = ins.cost_rt()
    be_gross = risk / (risk + reward)
    # net: p*(reward - c) = (1-p)*(risk + c)  ->  p = (risk + c) / (risk + reward)
    be_net = (risk + cost) / (risk + reward)
    notes = []
    if cost / risk > 0.10:
        notes.append("Costs exceed 10% of risk: scalping regime, edge very unlikely to survive.")
    elif cost / risk > 0.05:
        notes.append("Costs 5-10% of risk: requires a strong gross edge.")
    return CostReport(symbol, stop_points, target_points, risk, cost, cost / risk,
                      cost / reward if reward else float("inf"), be_gross, be_net, notes)
