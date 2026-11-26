"""Execution layer contracts (design + paper implementation).

The engine never talks to a broker directly; it talks to a ``BrokerAdapter``.
Planned adapters (not implemented here — they need credentials and each vendor's SDK):

* ProjectXAdapter  — TopstepX Gateway API (REST + SignalR). Topstep permits API bots on
  Combine / Express Funded accounts (not Live Funded; no HFT). ~$29/mo API add-on (reported).
* TradovateAdapter — Tradovate REST/WebSocket API (many prop firms run on Tradovate).
* RithmicAdapter   — R|Protocol (e.g. the `async_rithmic` Python package) for Rithmic-based firms.
* Apex: fully automated bots are reportedly NOT allowed on Performance Accounts — use the
  'confirm' execution mode (engine proposes a bracket, human clicks) there.

Every order goes through risk.guard.evaluate() first; the adapter only ever receives
*bracket* orders (entry + hard stop attached server-side) so a disconnect can never leave
an unprotected position.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class BracketOrder:
    symbol: str
    side: int
    contracts: int
    stop_price: float
    target_price: float | None = None
    tag: str = ""


@dataclass
class Fill:
    ts: str
    symbol: str
    side: int
    contracts: int
    price: float
    tag: str = ""


class BrokerAdapter(ABC):
    mode: str = "auto"   # auto | confirm (human approves each bracket)

    @abstractmethod
    def place_bracket(self, order: BracketOrder) -> str: ...

    @abstractmethod
    def modify_stop(self, order_id: str, new_stop: float) -> None: ...

    @abstractmethod
    def flatten_all(self, reason: str) -> None: ...

    @abstractmethod
    def positions(self) -> dict[str, int]: ...


@dataclass
class PaperBroker(BrokerAdapter):
    """Fills brackets against incoming 1-minute bars (stop-first, gap-through at open),
    used by the forward-testing tracker. Same conventions as the backtester so live-vs-
    backtest drift is attributable to the market, not to simulator differences."""
    slippage_ticks: float = 1.0
    tick: float = 0.25
    fills: list[Fill] = field(default_factory=list)
    _open: dict = field(default_factory=dict)
    _n: int = 0

    def place_bracket(self, order: BracketOrder, price: float | None = None, ts: str = "") -> str:
        self._n += 1
        oid = f"paper-{self._n}"
        px = (price or 0.0) + order.side * self.slippage_ticks * self.tick
        self._open[oid] = {"order": order, "entry": px}
        self.fills.append(Fill(ts, order.symbol, order.side, order.contracts, px, order.tag))
        return oid

    def modify_stop(self, order_id: str, new_stop: float) -> None:
        self._open[order_id]["order"].stop_price = new_stop

    def on_bar(self, ts: str, o: float, h: float, l: float, c: float) -> list[Fill]:
        out = []
        for oid, st in list(self._open.items()):
            od: BracketOrder = st["order"]
            px = None
            if od.side > 0 and l <= od.stop_price:
                px = min(od.stop_price, o) - self.slippage_ticks * self.tick
            elif od.side < 0 and h >= od.stop_price:
                px = max(od.stop_price, o) + self.slippage_ticks * self.tick
            elif od.target_price is not None and ((od.side > 0 and h >= od.target_price) or (od.side < 0 and l <= od.target_price)):
                px = od.target_price
            if px is not None:
                f = Fill(ts, od.symbol, -od.side, od.contracts, px, od.tag)
                out.append(f)
                self.fills.append(f)
                del self._open[oid]
        return out

    def flatten_all(self, reason: str, price: float | None = None, ts: str = "") -> None:
        for oid, st in list(self._open.items()):
            od = st["order"]
            px = (price or st["entry"]) - od.side * self.slippage_ticks * self.tick
            self.fills.append(Fill(ts, od.symbol, -od.side, od.contracts, px, reason))
            del self._open[oid]

    def positions(self) -> dict[str, int]:
        pos: dict[str, int] = {}
        for st in self._open.values():
            od = st["order"]
            pos[od.symbol] = pos.get(od.symbol, 0) + od.side * od.contracts
        return pos
