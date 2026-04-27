import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from quant_trading.reporting.sample_backtest import run_sample_backtest_payload


def main() -> None:
    payload = run_sample_backtest_payload()
    summary = payload["summary"]

    print(f"Final equity: {summary['final_equity']:.2f}")
    print(f"Orders: {summary['orders']}")
    print(f"Fills: {summary['fills']}")
    print(f"Rejected orders: {summary['rejected_orders']}")


if __name__ == "__main__":
    main()
