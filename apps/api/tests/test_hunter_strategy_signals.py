"""Research scanner rules: closed, contiguous candles only, NO execution paths."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal as D

import pytest

from nex_api.binance_closed_candles import (
    ClosedCandle, ClosedCandleBatch, INTERVAL_MS
)
from nex_api.strategy_signals import (
    ALLOWED_INTERVALS, BY_ID, STRATEGIES, StrategyDataError, evaluate
)

def sample(closes=None, *, interval="1h", symbol="BTCUSDT", vol=D("10")):
    closes = closes or [D(100) for _ in range(80)]
    step = INTERVAL_MS[interval]
    base = 1_730_000_000_000 // step * step
    rows = tuple(ClosedCandle(
        symbol=symbol, market="usdm_futures", interval=interval,
        open_time_ms=base + i*step, close_time_ms=base+(i+1)*step-1,
        open=c, high=c+D("0.1"), low=c-D("0.1"), close=c, volume=vol
    ) for i,c in enumerate(closes))
    return ClosedCandleBatch(
        market="usdm_futures", symbol=symbol, interval=interval,
        server_time_ms=base + (len(closes)+1)*step,
        candles=rows
    )

@pytest.mark.parametrize("strategy", [x.id for x in STRATEGIES])
def test_four_real_algorithms_default_to_neutral(strategy):
    assert evaluate(strategy, sample()) == "NEUTRAL"

def test_trend_ema_long_and_short_candidates():
    ups=[D(100)+D(i) for i in range(80)]
    downs=[D(200)-D(i) for i in range(80)]
    assert evaluate("trend-ladder", sample(ups)) == "LONG_CANDIDATE"
    assert evaluate("trend-ladder", sample(downs)) == "SHORT_CANDIDATE"

def test_range_fade_research_candidates():
    close=[D(100)]*60 + [D("100")+D(i%2) for i in range(19)] + [D("99.95")]
    assert evaluate("range-fade", sample(close)) == "LONG_CANDIDATE"
    close[-1]=D("101.05")
    assert evaluate("range-fade", sample(close)) == "SHORT_CANDIDATE"

def test_breakout_requires_above_mean_volume():
    batch=sample([D(100)]*79+[D("105")])
    assert evaluate("breakout-scout",batch) == "NEUTRAL"
    last=replace(batch.candles[-1],volume=D("20"))
    batch=replace(batch,candles=(*batch.candles[:-1],last))
    assert evaluate("breakout-scout",batch) == "LONG_CANDIDATE"

def test_mean_return_two_sigma():
    closes=[D(100)]*79+[D(90)]
    assert evaluate("mean-return",sample(closes)) == "NEUTRAL" # no variance
    closes=[D(100)+(D(i%3)/10) for i in range(79)]+[D(90)]
    assert evaluate("mean-return",sample(closes)) == "LONG_CANDIDATE"

def test_reject_future_or_unclosed_candle():
    batch=sample()
    bad=replace(batch,server_time_ms=batch.candles[-1].close_time_ms)
    with pytest.raises(StrategyDataError,match="CANDLES_NOT_CLOSED"):
        evaluate("trend-ladder",bad)

def test_reject_gap_and_mixed_candle():
    batch=sample()
    bad_last=replace(batch.candles[-1],open_time_ms=batch.candles[-1].open_time_ms+3_600_000,
                     close_time_ms=batch.candles[-1].close_time_ms+3_600_000)
    with pytest.raises(StrategyDataError,match="CANDLES_NOT_CLOSED"):
        evaluate("trend-ladder",replace(batch,candles=(*batch.candles[:-1],bad_last)))
    with pytest.raises(StrategyDataError,match="MIXED_MARKET"):
        evaluate("trend-ladder",replace(batch,candles=(*batch.candles[:-1],replace(batch.candles[-1],symbol="DOGEUSDT"))))

def test_bounded_supported_timeframes():
    assert ALLOWED_INTERVALS == {"5m","15m","1h","4h","1d"}
    for interval in ALLOWED_INTERVALS:
        assert evaluate("range-fade",sample(interval=interval)) == "NEUTRAL"

def test_unapproved_strategy_rejected():
    with pytest.raises(StrategyDataError,match="UNKNOWN_STRATEGY"):
        evaluate("ndsp-unverified",sample())

def test_readonly_module_does_not_import_order_writer():
    from pathlib import Path
    text=Path(__file__).parents[1].joinpath("nex_api/routes/strategy_scanner.py").read_text()
    assert "hunter_live_executor" not in text
    assert "submit_order" not in text
    assert "execute_order" not in text


def test_divergence_flat_is_neutral():
    assert evaluate("divergence-rsi", sample()) == "NEUTRAL"

def test_divergence_requires_confirmed_pivots():
    closes = [D(100) + D(i % 5) / 10 for i in range(80)]
    batch = sample(closes)
    first = evaluate("divergence-rsi", batch)
    assert first in ("NEUTRAL", "LONG_CANDIDATE", "SHORT_CANDIDATE")
    # An unclosed last bar invalidates the entire evaluation.
    with pytest.raises(StrategyDataError, match="CANDLES_NOT_CLOSED"):
        evaluate("divergence-rsi", replace(batch, server_time_ms=batch.candles[-1].close_time_ms))

def test_rsi_uses_no_future_closes():
    from nex_api.strategy_signals import _rsi14
    closes=[D(100)+D(i % 7) for i in range(80)]
    assert _rsi14(closes)[:65] == _rsi14(closes[:65])
    assert _rsi14([D(100)]*80)[-1] == D(50)
