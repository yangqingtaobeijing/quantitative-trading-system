from datetime import date, timedelta
from typing import List

from quant_trading.core.models import Bar


def generate_trending_bars(symbol: str = "SPY", days: int = 260) -> List[Bar]:
    start = date(2024, 1, 2)
    bars: List[Bar] = []
    price = 100.0
    calendar_day = start

    while len(bars) < days:
        if calendar_day.weekday() >= 5:
            calendar_day += timedelta(days=1)
            continue

        drift = 0.08 if len(bars) < days * 0.65 else -0.03
        price = max(1.0, price + drift)
        bars.append(
            Bar(
                symbol=symbol,
                date=calendar_day,
                open=price - 0.2,
                high=price + 0.5,
                low=price - 0.5,
                close=price,
                volume=1_000_000,
                adjusted_close=price,
            )
        )
        calendar_day += timedelta(days=1)

    return bars

