from abc import ABC, abstractmethod
from datetime import date
from typing import Dict, List

from quant_trading.core.models import Bar, PortfolioState, Signal


class Strategy(ABC):
    strategy_id: str

    @abstractmethod
    def generate_signals(
        self,
        current_date: date,
        history: Dict[str, List[Bar]],
        portfolio: PortfolioState,
        prices: Dict[str, float],
    ) -> List[Signal]:
        raise NotImplementedError

