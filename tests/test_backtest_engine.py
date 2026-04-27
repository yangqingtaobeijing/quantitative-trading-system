import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from quant_trading.backtest_engine.engine import DailyBacktestEngine
from quant_trading.data_hub.sample_data import generate_trending_bars
from quant_trading.risk_engine.rules import RiskConfig, RiskEngine
from quant_trading.strategies.moving_average import MovingAverageTrendStrategy


class DailyBacktestEngineTest(unittest.TestCase):
    def test_moving_average_strategy_generates_fills(self):
        bars = generate_trending_bars(symbol="SPY", days=260)
        strategy = MovingAverageTrendStrategy(
            symbol="SPY",
            short_window=20,
            long_window=60,
            target_weight=0.20,
        )
        risk_engine = RiskEngine(
            RiskConfig(
                max_symbol_weight=0.25,
                max_order_notional_pct=0.25,
                long_only=True,
            )
        )

        result = DailyBacktestEngine(
            bars=bars,
            strategy=strategy,
            risk_engine=risk_engine,
            initial_cash=100_000.0,
        ).run()

        self.assertGreater(len(result.equity_curve), 0)
        self.assertGreater(len(result.fills), 0)
        self.assertGreater(result.final_equity, 0)

    def test_risk_engine_rejects_oversized_target(self):
        bars = generate_trending_bars(symbol="SPY", days=260)
        strategy = MovingAverageTrendStrategy(
            symbol="SPY",
            short_window=20,
            long_window=60,
            target_weight=1.0,
        )
        risk_engine = RiskEngine(
            RiskConfig(
                max_symbol_weight=0.20,
                max_order_notional_pct=1.0,
                long_only=True,
            )
        )

        result = DailyBacktestEngine(
            bars=bars,
            strategy=strategy,
            risk_engine=risk_engine,
            initial_cash=100_000.0,
        ).run()

        self.assertGreater(len(result.rejected_orders), 0)
        self.assertEqual(len(result.fills), 0)


if __name__ == "__main__":
    unittest.main()
