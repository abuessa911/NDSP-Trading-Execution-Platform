"""Fail-closed bridge from closed research candles to Testnet LONG-only decisions.

This module does not authorize trades, size orders, access credentials, or call
an exchange. Research candidates require separate risk and operator gates.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nex_api.binance_closed_candles import ClosedCandleBatch
from nex_api.strategy_signals import BY_ID, StrategyDataError, evaluate


class StrategyExecutionRejected(ValueError):
    """Bounded refusal code; never includes exchange payloads."""


@dataclass(frozen=True)
class ExecutionSignal:
    strategy: str
    symbol: str
    interval: str
    candle_close_ms: int
    candidate: str
    decision: str
    reference_close: Decimal | None = None


def evaluate_testnet_long_only(strategy_id: str, batch: ClosedCandleBatch) -> ExecutionSignal:
    """Convert a validated research candidate to a non-authorizing decision.

    SHORT candidates are explicitly blocked. NEUTRAL is not an entry. A LONG
    candidate is still only a candidate until risk and operator gates approve.
    """
    definition = BY_ID.get(strategy_id)
    if definition is None:
        raise StrategyExecutionRejected("STRATEGY_NOT_EXPLICITLY_SELECTED")
    if not isinstance(batch, ClosedCandleBatch):
        raise StrategyExecutionRejected("STRATEGY_CANDLES_INVALID")
    if batch.market != "usdm_futures":
        raise StrategyExecutionRejected("TESTNET_FUTURES_DATA_REQUIRED")
    if batch.symbol != definition.symbol or batch.interval != definition.interval:
        raise StrategyExecutionRejected("STRATEGY_MARKET_INTERVAL_MISMATCH")
    try:
        candidate = evaluate(strategy_id, batch)
    except StrategyDataError as exc:
        raise StrategyExecutionRejected("STRATEGY_CANDLES_REJECTED") from exc
    if not batch.candles:
        raise StrategyExecutionRejected("STRATEGY_CANDLES_INVALID")
    decision = {
        "LONG_CANDIDATE": "LONG_REQUIRES_RISK_AND_APPROVAL",
        "SHORT_CANDIDATE": "SHORT_BLOCKED",
        "NEUTRAL": "NO_SIGNAL",
    }[candidate]
    return ExecutionSignal(strategy_id, batch.symbol, batch.interval,
                           batch.candles[-1].close_time_ms, candidate, decision,
                           batch.candles[-1].close)


def evaluate_exchange_testnet(strategy_id: str, exchange) -> ExecutionSignal:
    """Read the selected strategy's CLOSED candles from the already pinned DEMO exchange.

    Never use Mainnet public candles as evidence for a Testnet order.
    """
    from nex_api.binance_closed_candles import _parse_rows, MarketDataUnavailable
    definition = BY_ID.get(strategy_id)
    if definition is None:
        raise StrategyExecutionRejected("STRATEGY_NOT_EXPLICITLY_SELECTED")
    if getattr(exchange, "mode", None) != "testnet":
        raise StrategyExecutionRejected("TESTNET_EXCHANGE_REQUIRED")
    try:
        clock = exchange.get("/fapi/v1/time")
        if not isinstance(clock, dict) or type(clock.get("serverTime")) is not int:
            raise StrategyExecutionRejected("STRATEGY_CLOCK_UNVERIFIED")
        server_ms = clock["serverTime"]
        rows = exchange.get("/fapi/v1/klines", symbol=definition.symbol,
                            interval=definition.interval, limit=120)
        candles = _parse_rows(rows, "usdm_futures", definition.symbol,
                              definition.interval, server_ms)
        batch = ClosedCandleBatch("usdm_futures", definition.symbol,
                                  definition.interval, server_ms, candles)
        return evaluate_testnet_long_only(strategy_id, batch)
    except (MarketDataUnavailable, ValueError, TypeError, KeyError) as exc:
        if isinstance(exc, StrategyExecutionRejected):
            raise
        raise StrategyExecutionRejected("STRATEGY_CANDLES_REJECTED") from exc
