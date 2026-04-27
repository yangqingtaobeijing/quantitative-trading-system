from collections import defaultdict
from datetime import date
from typing import Dict, Iterable, List

from quant_trading.core.models import Bar


class InMemoryBarStore:
    def __init__(self, bars: Iterable[Bar]):
        self._bars = sorted(bars, key=lambda bar: (bar.date, bar.symbol))

    def dates(self) -> List[date]:
        return sorted({bar.date for bar in self._bars})

    def bars_by_date(self) -> Dict[date, Dict[str, Bar]]:
        grouped: Dict[date, Dict[str, Bar]] = defaultdict(dict)
        for bar in self._bars:
            grouped[bar.date][bar.symbol] = bar
        return dict(grouped)

    def symbols(self) -> List[str]:
        return sorted({bar.symbol for bar in self._bars})

