from collections import defaultdict
from typing import Dict, Iterable, List

from quant_trading.broker_gateway.paper import PaperBroker
from quant_trading.core.models import (
    BacktestResult,
    Bar,
    EquityPoint,
    Order,
    OrderSide,
    OrderStatus,
    PortfolioState,
    Signal,
)
from quant_trading.data_hub.in_memory import InMemoryBarStore
from quant_trading.portfolio.accounting import target_quantity_for_weight
from quant_trading.risk_engine.rules import RiskEngine
from quant_trading.strategies.base import Strategy


class DailyBacktestEngine:
    def __init__(
        self,
        bars: Iterable[Bar],
        strategy: Strategy,
        risk_engine: RiskEngine,
        initial_cash: float = 100_000.0,
        commission_per_order: float = 1.0,
        slippage_bps: float = 5.0,
    ):
        self.store = InMemoryBarStore(bars)
        self.strategy = strategy
        self.risk_engine = risk_engine
        self.initial_cash = initial_cash
        self.broker = PaperBroker(
            commission_per_order=commission_per_order,
            slippage_bps=slippage_bps,
        )

    def run(self) -> BacktestResult:
        by_date = self.store.bars_by_date()
        history: Dict[str, List[Bar]] = defaultdict(list)
        portfolio = PortfolioState(cash=self.initial_cash)
        pending_signals: List[Signal] = []
        equity_curve: List[EquityPoint] = []
        orders: List[Order] = []
        rejected_orders: List[Order] = []

        for current_date in self.store.dates():
            day_bars = by_date[current_date]
            prices = {symbol: bar.price for symbol, bar in day_bars.items()}

            for signal in pending_signals:
                if signal.symbol not in prices:
                    continue
                order = self._order_from_signal(signal, portfolio, prices)
                if order is None:
                    continue

                current_value = portfolio.quantity(order.symbol) * prices[order.symbol]
                try:
                    self.risk_engine.validate(
                        order=order,
                        portfolio=portfolio,
                        equity=portfolio.equity(prices),
                        current_symbol_value=current_value,
                    )
                except ValueError as exc:
                    order.status = OrderStatus.REJECTED
                    order.rejection_reason = str(exc)
                    rejected_orders.append(order)
                    orders.append(order)
                    continue

                fill = self.broker.submit_market_order(
                    order=order,
                    trade_date=current_date,
                    market_price=prices[order.symbol],
                )
                portfolio.apply_fill(fill)
                orders.append(order)

            for bar in day_bars.values():
                history[bar.symbol].append(bar)

            equity_curve.append(
                EquityPoint(
                    date=current_date,
                    cash=portfolio.cash,
                    market_value=portfolio.market_value(prices),
                    equity=portfolio.equity(prices),
                )
            )

            pending_signals = self.strategy.generate_signals(
                current_date=current_date,
                history=history,
                portfolio=portfolio,
                prices=prices,
            )

        return BacktestResult(
            equity_curve=equity_curve,
            orders=orders,
            fills=list(self.broker.fills),
            rejected_orders=rejected_orders,
        )

    def _order_from_signal(
        self,
        signal: Signal,
        portfolio: PortfolioState,
        prices: Dict[str, float],
    ) -> Order:
        target_quantity = target_quantity_for_weight(
            portfolio=portfolio,
            prices=prices,
            symbol=signal.symbol,
            target_weight=signal.target_weight,
        )
        current_quantity = portfolio.quantity(signal.symbol)
        delta = target_quantity - current_quantity
        if delta == 0:
            return None

        side = OrderSide.BUY if delta > 0 else OrderSide.SELL
        return Order(
            symbol=signal.symbol,
            side=side,
            quantity=abs(delta),
            estimated_price=prices[signal.symbol],
            strategy_id=signal.strategy_id,
            reason=signal.reason,
        )

