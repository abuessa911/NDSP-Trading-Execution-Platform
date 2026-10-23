"""Synthetic, read-only tests for the unified five-strategy DEMO adapter."""
from decimal import Decimal

import pytest

from nex_api.binance_closed_candles import INTERVAL_MS
from nex_api.strategy_execution_adapter import (
    StrategyExecutionRejected, evaluate_exchange_testnet,
)
from nex_api.strategy_signals import BY_ID
from nex_api.testnet_execution import PRESET, valid_config
from nex_api.hunter_live_executor import Halt


class SyntheticExchange:
    mode = "testnet"

    def __init__(self, sid, *, stale=False, interval=None):
        self.definition = BY_ID[sid]
        self.span = INTERVAL_MS[self.definition.interval]
        self.end = 1_800_000_000_000 // self.span * self.span
        self.stale = stale
        self.interval = interval
        self.calls = []

    def get(self, path, **kwargs):
        self.calls.append((path, kwargs))
        if path == "/fapi/v1/time":
            return {"serverTime": self.end + (self.span * 4 if self.stale else 10)}
        assert path == "/fapi/v1/klines"
        assert kwargs == {"symbol": self.definition.symbol,
                          "interval": self.definition.interval, "limit": 120}
        rows = []
        for i in range(120):
            start = self.end - (120 - i) * self.span
            price = Decimal("100") + Decimal(i) / 10
            rows.append([start, str(price), str(price + 1), str(price - 1),
                         str(price), "10", start + self.span - 1])
        return rows


@pytest.mark.parametrize("sid", list(BY_ID))
def test_all_five_use_selected_testnet_symbol_interval_and_closed_candles(sid):
    ex = SyntheticExchange(sid)
    signal = evaluate_exchange_testnet(sid, ex)
    assert signal.strategy == sid
    assert signal.symbol == BY_ID[sid].symbol
    assert signal.interval == BY_ID[sid].interval
    assert signal.candidate in {"LONG_CANDIDATE", "SHORT_CANDIDATE", "NEUTRAL"}
    assert signal.decision in {"LONG_REQUIRES_RISK_AND_APPROVAL", "SHORT_BLOCKED", "NO_SIGNAL"}
    assert len(ex.calls) == 2


@pytest.mark.parametrize("sid", list(BY_ID))
def test_testnet_config_enforces_strategy_market(sid):
    definition = BY_ID[sid]
    assert valid_config(dict(PRESET, strategy=sid, symbol=definition.symbol))["strategy"] == sid
    with pytest.raises(Halt, match="STRATEGY_MARKET_INTERVAL_MISMATCH"):
        valid_config(dict(PRESET, strategy=sid, symbol="XRPUSDT"))


def test_stale_candles_fail_closed():
    with pytest.raises(StrategyExecutionRejected, match="STRATEGY_CANDLES_REJECTED"):
        evaluate_exchange_testnet("trend-ladder", SyntheticExchange("trend-ladder", stale=True))


def test_mainnet_and_unknown_strategy_fail_before_market_reads():
    ex = SyntheticExchange("trend-ladder")
    ex.mode = "mainnet"
    with pytest.raises(StrategyExecutionRejected, match="TESTNET_EXCHANGE_REQUIRED"):
        evaluate_exchange_testnet("trend-ladder", ex)
    assert ex.calls == []
    with pytest.raises(StrategyExecutionRejected, match="STRATEGY_NOT_EXPLICITLY_SELECTED"):
        evaluate_exchange_testnet("unknown", ex)
    assert ex.calls == []
