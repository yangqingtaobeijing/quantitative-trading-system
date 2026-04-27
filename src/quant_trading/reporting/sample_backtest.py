from dataclasses import asdict, dataclass
from typing import Dict, Mapping, Optional

from quant_trading.backtest_engine.engine import DailyBacktestEngine
from quant_trading.core.models import BacktestResult, EquityPoint, Fill, Order
from quant_trading.data_hub.sample_data import generate_trending_bars
from quant_trading.risk_engine.rules import RiskConfig, RiskEngine
from quant_trading.strategies.moving_average import MovingAverageTrendStrategy


@dataclass(frozen=True)
class BacktestConfig:
    symbol: str = "SPY"
    short_window: int = 20
    long_window: int = 60
    target_weight: float = 0.20
    max_symbol_weight: float = 0.25
    max_order_notional_pct: float = 0.25
    long_only: bool = True
    initial_cash: float = 100_000.0
    commission_per_order: float = 1.0
    slippage_bps: float = 5.0
    sample_days: int = 260


def run_sample_backtest_payload(config_input: Optional[Mapping[str, object]] = None) -> Dict[str, object]:
    config = parse_backtest_config(config_input)
    bars = generate_trending_bars(symbol=config.symbol, days=config.sample_days)
    strategy = MovingAverageTrendStrategy(
        symbol=config.symbol,
        short_window=config.short_window,
        long_window=config.long_window,
        target_weight=config.target_weight,
    )
    risk_engine = RiskEngine(
        RiskConfig(
            max_symbol_weight=config.max_symbol_weight,
            max_order_notional_pct=config.max_order_notional_pct,
            long_only=config.long_only,
        )
    )
    result = DailyBacktestEngine(
        bars=bars,
        strategy=strategy,
        risk_engine=risk_engine,
        initial_cash=config.initial_cash,
        commission_per_order=config.commission_per_order,
        slippage_bps=config.slippage_bps,
    ).run()
    return serialize_backtest_result(result, config)


def parse_backtest_config(config_input: Optional[Mapping[str, object]] = None) -> BacktestConfig:
    data = dict(config_input or {})
    config = BacktestConfig(
        symbol=str(data.get("symbol", BacktestConfig.symbol)).strip().upper() or BacktestConfig.symbol,
        short_window=_to_int(data.get("short_window", BacktestConfig.short_window), "short_window"),
        long_window=_to_int(data.get("long_window", BacktestConfig.long_window), "long_window"),
        target_weight=_to_float(data.get("target_weight", BacktestConfig.target_weight), "target_weight"),
        max_symbol_weight=_to_float(
            data.get("max_symbol_weight", BacktestConfig.max_symbol_weight),
            "max_symbol_weight",
        ),
        max_order_notional_pct=_to_float(
            data.get("max_order_notional_pct", BacktestConfig.max_order_notional_pct),
            "max_order_notional_pct",
        ),
        long_only=_to_bool(data.get("long_only", BacktestConfig.long_only)),
        initial_cash=_to_float(data.get("initial_cash", BacktestConfig.initial_cash), "initial_cash"),
        commission_per_order=_to_float(
            data.get("commission_per_order", BacktestConfig.commission_per_order),
            "commission_per_order",
        ),
        slippage_bps=_to_float(data.get("slippage_bps", BacktestConfig.slippage_bps), "slippage_bps"),
        sample_days=_to_int(data.get("sample_days", BacktestConfig.sample_days), "sample_days"),
    )
    _validate_config(config)
    return config


def serialize_backtest_result(result: BacktestResult, config: BacktestConfig) -> Dict[str, object]:
    initial_equity = result.equity_curve[0].equity if result.equity_curve else 0.0
    final_equity = result.final_equity
    total_return = 0.0 if initial_equity == 0 else (final_equity / initial_equity) - 1

    return {
        "config": asdict(config),
        "summary": {
            "initial_equity": round(initial_equity, 2),
            "final_equity": round(final_equity, 2),
            "total_return_pct": round(total_return * 100, 2),
            "orders": len(result.orders),
            "fills": len(result.fills),
            "rejected_orders": len(result.rejected_orders),
        },
        "equity_curve": [_serialize_equity_point(point) for point in result.equity_curve],
        "order_suggestions": [_serialize_order_suggestion(order) for order in result.orders[-10:] if order.status.value != "rejected"],
        "orders": [_serialize_order(order) for order in result.orders[-20:]],
        "fills": [_serialize_fill(fill) for fill in result.fills[-20:]],
    }


def _to_int(value: object, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def _to_float(value: object, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number") from exc


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _validate_config(config: BacktestConfig) -> None:
    if not config.symbol.isalnum():
        raise ValueError("symbol must contain only letters and numbers")
    if config.short_window <= 0:
        raise ValueError("short_window must be greater than 0")
    if config.long_window <= 0:
        raise ValueError("long_window must be greater than 0")
    if config.short_window >= config.long_window:
        raise ValueError("short_window must be smaller than long_window")
    if config.long_window >= config.sample_days:
        raise ValueError("long_window must be smaller than sample_days")
    if not 0 <= config.target_weight <= 1:
        raise ValueError("target_weight must be between 0 and 1")
    if not 0 < config.max_symbol_weight <= 1:
        raise ValueError("max_symbol_weight must be between 0 and 1")
    if not 0 < config.max_order_notional_pct <= 1:
        raise ValueError("max_order_notional_pct must be between 0 and 1")
    if config.target_weight > config.max_symbol_weight:
        raise ValueError("target_weight cannot exceed max_symbol_weight")
    if config.initial_cash <= 0:
        raise ValueError("initial_cash must be greater than 0")
    if config.commission_per_order < 0:
        raise ValueError("commission_per_order cannot be negative")
    if config.slippage_bps < 0:
        raise ValueError("slippage_bps cannot be negative")
    if config.sample_days < 80:
        raise ValueError("sample_days must be at least 80")


def _serialize_equity_point(point: EquityPoint) -> Dict[str, object]:
    return {
        "date": point.date.isoformat(),
        "cash": round(point.cash, 2),
        "market_value": round(point.market_value, 2),
        "equity": round(point.equity, 2),
    }


def _serialize_order(order: Order) -> Dict[str, object]:
    return {
        "id": order.id[:8],
        "symbol": order.symbol,
        "side": order.side.value,
        "quantity": order.quantity,
        "estimated_price": round(order.estimated_price, 2),
        "notional": round(order.notional, 2),
        "status": order.status.value,
        "reason": order.reason,
        "rejection_reason": order.rejection_reason,
    }


def _serialize_order_suggestion(order: Order) -> Dict[str, object]:
    suggestion = _serialize_order(order)
    suggestion["status"] = "pending_confirmation"
    suggestion["suggestion_id"] = f"suggest-{order.id[:8]}"
    return suggestion


def _serialize_fill(fill: Fill) -> Dict[str, object]:
    return {
        "order_id": fill.order_id[:8],
        "date": fill.filled_at.isoformat(),
        "symbol": fill.symbol,
        "side": fill.side.value,
        "quantity": fill.quantity,
        "price": round(fill.price, 2),
        "commission": round(fill.commission, 2),
        "notional": round(fill.notional, 2),
    }
