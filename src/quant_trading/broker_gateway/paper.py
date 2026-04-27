from datetime import date
from typing import List

from quant_trading.core.models import Fill, Order, OrderSide, OrderStatus


class PaperBroker:
    def __init__(self, commission_per_order: float = 0.0, slippage_bps: float = 0.0):
        self.commission_per_order = commission_per_order
        self.slippage_bps = slippage_bps
        self.orders: List[Order] = []
        self.fills: List[Fill] = []

    def submit_market_order(self, order: Order, trade_date: date, market_price: float) -> Fill:
        order.status = OrderStatus.ACCEPTED
        self.orders.append(order)

        slippage_multiplier = self.slippage_bps / 10_000
        if order.side == OrderSide.BUY:
            fill_price = market_price * (1 + slippage_multiplier)
        else:
            fill_price = market_price * (1 - slippage_multiplier)

        fill = Fill(
            order_id=order.id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            commission=self.commission_per_order,
            filled_at=trade_date,
        )
        order.status = OrderStatus.FILLED
        self.fills.append(fill)
        return fill

