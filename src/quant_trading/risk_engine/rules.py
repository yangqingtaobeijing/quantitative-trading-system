from dataclasses import dataclass, field
from typing import Iterable, Set

from quant_trading.core.models import Order, OrderSide, PortfolioState


@dataclass(frozen=True)
class RiskConfig:
    max_symbol_weight: float = 0.20
    max_order_notional_pct: float = 0.10
    long_only: bool = True
    blocked_symbols: Set[str] = field(default_factory=set)


class RiskEngine:
    def __init__(self, config: RiskConfig):
        self.config = config

    def validate(
        self,
        order: Order,
        portfolio: PortfolioState,
        equity: float,
        current_symbol_value: float,
    ) -> None:
        if order.symbol in self.config.blocked_symbols:
            raise ValueError(f"{order.symbol} is blocked")

        if order.quantity <= 0:
            raise ValueError("order quantity must be positive")

        if equity <= 0:
            raise ValueError("portfolio equity must be positive")

        if order.notional > equity * self.config.max_order_notional_pct:
            raise ValueError("order notional exceeds max order limit")

        if self.config.long_only and order.side == OrderSide.SELL:
            held_quantity = portfolio.quantity(order.symbol)
            if order.quantity > held_quantity:
                raise ValueError("long-only mode cannot sell more than current position")

        projected_value = current_symbol_value
        if order.side == OrderSide.BUY:
            projected_value += order.notional
        else:
            projected_value -= order.notional

        if projected_value > equity * self.config.max_symbol_weight:
            raise ValueError("projected symbol weight exceeds max symbol limit")

    def extend_blocklist(self, symbols: Iterable[str]) -> None:
        self.config.blocked_symbols.update(symbols)

