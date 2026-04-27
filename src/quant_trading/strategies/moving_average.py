from datetime import date
from typing import Dict, List

from quant_trading.core.models import Bar, PortfolioState, Signal
from quant_trading.strategies.base import Strategy


class MovingAverageTrendStrategy(Strategy):
    def __init__(
        self,
        symbol: str,
        short_window: int = 50,
        long_window: int = 200,
        target_weight: float = 1.0,
        strategy_id: str = "ma_trend",
    ):
        if short_window <= 0 or long_window <= 0:
            raise ValueError("Moving average windows must be positive")
        if short_window >= long_window:
            raise ValueError("short_window must be smaller than long_window")
        if target_weight < 0:
            raise ValueError("target_weight must be non-negative")

        self.symbol = symbol
        self.short_window = short_window
        self.long_window = long_window
        self.target_weight = target_weight
        self.strategy_id = strategy_id

    def generate_signals(
        self,
        current_date: date,
        history: Dict[str, List[Bar]],
        portfolio: PortfolioState,
        prices: Dict[str, float],
    ) -> List[Signal]:
        bars = history.get(self.symbol, [])
        if len(bars) < self.long_window:
            return [
                Signal(
                    strategy_id=self.strategy_id,
                    symbol=self.symbol,
                    target_weight=0.0,
                    reason=f"{current_date}: insufficient history",
                )
            ]

        closes = [bar.price for bar in bars]
        short_ma = sum(closes[-self.short_window :]) / self.short_window
        long_ma = sum(closes[-self.long_window :]) / self.long_window
        target = self.target_weight if short_ma > long_ma else 0.0
        reason = f"{current_date}: short_ma={short_ma:.2f}, long_ma={long_ma:.2f}"

        return [
            Signal(
                strategy_id=self.strategy_id,
                symbol=self.symbol,
                target_weight=target,
                reason=reason,
            )
        ]

