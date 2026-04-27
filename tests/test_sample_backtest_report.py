import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from quant_trading.reporting.sample_backtest import parse_backtest_config, run_sample_backtest_payload


class SampleBacktestReportTest(unittest.TestCase):
    def test_payload_contains_dashboard_fields(self):
        payload = run_sample_backtest_payload()

        self.assertIn("summary", payload)
        self.assertIn("equity_curve", payload)
        self.assertIn("order_suggestions", payload)
        self.assertIn("orders", payload)
        self.assertGreater(payload["summary"]["final_equity"], 0)
        self.assertGreater(len(payload["equity_curve"]), 0)

    def test_payload_uses_custom_config(self):
        payload = run_sample_backtest_payload(
            {
                "symbol": "QQQ",
                "short_window": 10,
                "long_window": 40,
                "target_weight": 0.15,
                "max_symbol_weight": 0.20,
                "max_order_notional_pct": 0.20,
                "initial_cash": 50_000,
            }
        )

        self.assertEqual(payload["config"]["symbol"], "QQQ")
        self.assertEqual(payload["config"]["short_window"], 10)
        self.assertEqual(payload["summary"]["initial_equity"], 50_000)

    def test_order_suggestions_are_pending_confirmation(self):
        payload = run_sample_backtest_payload()

        self.assertGreater(len(payload["order_suggestions"]), 0)
        self.assertEqual(payload["order_suggestions"][0]["status"], "pending_confirmation")
        self.assertTrue(payload["order_suggestions"][0]["suggestion_id"].startswith("suggest-"))

    def test_invalid_config_rejects_target_above_risk_limit(self):
        with self.assertRaises(ValueError):
            parse_backtest_config({"target_weight": 0.30, "max_symbol_weight": 0.20})


if __name__ == "__main__":
    unittest.main()
