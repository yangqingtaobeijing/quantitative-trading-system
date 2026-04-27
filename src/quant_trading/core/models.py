from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    CREATED = "created"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FILLED = "filled"


@dataclass(frozen=True)
class Bar:
    symbol: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float] = None

    @property
    def price(self) -> float:
        return self.adjusted_close if self.adjusted_close is not None else self.close


@dataclass(frozen=True)
class Signal:
    strategy_id: str
    symbol: str
    target_weight: float
    reason: str


@dataclass
class Order:
    symbol: str
    side: OrderSide
    quantity: int
    estimated_price: float
    strategy_id: str
    reason: str
    id: str = field(default_factory=lambda: str(uuid4()))
    status: OrderStatus = OrderStatus.CREATED
    rejection_reason: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def notional(self) -> float:
        return self.quantity * self.estimated_price


@dataclass(frozen=True)
class Fill:
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    commission: float
    filled_at: date

    @property
    def notional(self) -> float:
        return self.quantity * self.price


@dataclass
class Position:
    symbol: str
    quantity: int = 0


@dataclass
class PortfolioState:
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)

    def quantity(self, symbol: str) -> int:
        position = self.positions.get(symbol)
        return 0 if position is None else position.quantity

    def apply_fill(self, fill: Fill) -> None:
        signed_quantity = fill.quantity if fill.side == OrderSide.BUY else -fill.quantity
        position = self.positions.setdefault(fill.symbol, Position(symbol=fill.symbol))
        position.quantity += signed_quantity
        if position.quantity == 0:
            self.positions.pop(fill.symbol, None)

        cash_delta = fill.notional + fill.commission
        if fill.side == OrderSide.BUY:
            self.cash -= cash_delta
        else:
            self.cash += fill.notional - fill.commission

    def market_value(self, prices: Dict[str, float]) -> float:
        return sum(position.quantity * prices.get(symbol, 0.0) for symbol, position in self.positions.items())

    def equity(self, prices: Dict[str, float]) -> float:
        return self.cash + self.market_value(prices)


@dataclass(frozen=True)
class EquityPoint:
    date: date
    cash: float
    market_value: float
    equity: float


@dataclass
class BacktestResult:
    equity_curve: List[EquityPoint]
    orders: List[Order]
    fills: List[Fill]
    rejected_orders: List[Order]

    @property
    def final_equity(self) -> float:
        if not self.equity_curve:
            return 0.0
        return self.equity_curve[-1].equity

