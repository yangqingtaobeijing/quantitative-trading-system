from typing import Dict

from quant_trading.core.models import PortfolioState


def target_quantity_for_weight(
    portfolio: PortfolioState,
    prices: Dict[str, float],
    symbol: str,
    target_weight: float,
) -> int:
    if target_weight < 0:
        raise ValueError("target_weight must be non-negative")
    price = prices[symbol]
    if price <= 0:
        raise ValueError("price must be positive")
    equity = portfolio.equity(prices)
    target_value = equity * target_weight
    return int(target_value // price)

