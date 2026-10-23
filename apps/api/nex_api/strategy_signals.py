"""Closed-candle research signals for Hunter KSA1.

These are explicitly defined experimental rules, NOT the older demo P&L
and NOT approved strategies for executing orders. No network or broker API.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from nex_api.binance_closed_candles import ClosedCandleBatch, INTERVAL_MS

Signal = Literal["LONG_CANDIDATE", "SHORT_CANDIDATE", "NEUTRAL"]

@dataclass(frozen=True)
class StrategyDefinition:
    id: str
    name: str
    symbol: str
    interval: str
    rule: str

STRATEGIES: tuple[StrategyDefinition, ...] = (
    StrategyDefinition("trend-ladder", "Trend Ladder", "BTCUSDT", "1h",
                       "EMA20 vs EMA50 and last two completed closes (research only)"),
    StrategyDefinition("range-fade", "Range Fade", "ETHUSDT", "15m",
                       "20-candle channel, <=8% width; 15% near either extreme (research only)"),
    StrategyDefinition("breakout-scout", "Breakout Scout", "SOLUSDT", "4h",
                       "20-candle high/low breakout with above-average volume (research only)"),
    StrategyDefinition("mean-return", "Mean Return", "LINKUSDT", "1h",
                       "20-candle closing-price z-score beyond +/-2 (research only)"),
    StrategyDefinition("divergence-rsi", "RSI Divergence", "BTCUSDT", "1h",
                       "RSI14 regular/hidden divergence on confirmed 3x3 price pivots; research only"),
)
BY_ID = {s.id: s for s in STRATEGIES}
ALLOWED_SYMBOLS = frozenset({
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "LINKUSDT", "XRPUSDT",
    "DOGEUSDT", "BNBUSDT",
})
ALLOWED_INTERVALS = frozenset({"5m", "15m", "1h", "4h", "1d"})

class StrategyDataError(ValueError):
    pass

def _ema(values: list[Decimal], window: int) -> Decimal:
    if len(values) < window:
        raise StrategyDataError("INSUFFICIENT_CANDLES")
    result = sum(values[:window], Decimal(0)) / Decimal(window)
    alpha = Decimal(2) / Decimal(window + 1)
    for price in values[window:]:
        result += alpha * (price - result)
    return result

def _validated_candles(batch: ClosedCandleBatch):
    if len(batch.candles) < 55 or batch.interval not in INTERVAL_MS:
        raise StrategyDataError("INSUFFICIENT_CANDLES")
    step = INTERVAL_MS[batch.interval]
    prior = None
    for candle in batch.candles:
        if candle.interval != batch.interval or candle.symbol != batch.symbol:
            raise StrategyDataError("MIXED_MARKET_DATA")
        if (candle.close_time_ms != candle.open_time_ms + step - 1
                or candle.close_time_ms >= batch.server_time_ms
                or (prior is not None and candle.open_time_ms != prior + step)):
            raise StrategyDataError("CANDLES_NOT_CLOSED_OR_CONTIGUOUS")
        prior = candle.open_time_ms
        for number in (candle.open, candle.high, candle.low, candle.close):
            if not number.is_finite() or number <= 0:
                raise StrategyDataError("INVALID_PRICE")
        if (candle.volume < 0 or not candle.volume.is_finite()
                or candle.low > min(candle.open, candle.close)
                or candle.high < max(candle.open, candle.close)):
            raise StrategyDataError("INVALID_CANDLE")
    return batch.candles

def _rsi14(closes: list[Decimal]) -> list[Decimal | None]:
    """Wilder RSI(14), no look-ahead: value at bar i uses closes <= i."""
    period = 14
    values: list[Decimal | None] = [None] * len(closes)
    if len(closes) <= period:
        return values
    gains = [max(closes[i] - closes[i-1], Decimal(0)) for i in range(1, len(closes))]
    losses = [max(closes[i-1] - closes[i], Decimal(0)) for i in range(1, len(closes))]
    avg_gain = sum(gains[:period], Decimal(0)) / period
    avg_loss = sum(losses[:period], Decimal(0)) / period
    def value(g: Decimal, l: Decimal) -> Decimal:
        if l == 0:
            return Decimal(100) if g > 0 else Decimal(50)
        return Decimal(100) - Decimal(100) / (Decimal(1) + g/l)
    values[period] = value(avg_gain, avg_loss)
    for i in range(period+1, len(closes)):
        avg_gain = (avg_gain * (period-1) + gains[i-1]) / period
        avg_loss = (avg_loss * (period-1) + losses[i-1]) / period
        values[i] = value(avg_gain, avg_loss)
    return values


def _divergence_rsi(candles, closing: list[Decimal]) -> Signal:
    """Research candidate only; strict pivots become known after 3 right-hand CLOSED bars.

    Different types share the same price-pivot timestamps. No live-bar pivot,
    forward RSI value, broker action, or unconfirmed current candle is used.
    """
    rsi = _rsi14(closing)
    left = right = 3
    highs: list[int] = []
    lows: list[int] = []
    for i in range(14+left, len(candles)-right):
        if rsi[i] is None:
            continue
        if all(candles[i].low < candles[j].low for j in range(i-left,i+right+1) if j != i):
            lows.append(i)
        if all(candles[i].high > candles[j].high for j in range(i-left,i+right+1) if j != i):
            highs.append(i)
    candidates: list[tuple[int, Signal]] = []
    for pivots, bullish in ((lows, True), (highs, False)):
        if len(pivots) < 2:
            continue
        old, new = pivots[-2:]
        if not 4 <= new-old <= 35 or len(candles)-1-new > 12:
            continue
        price_a = candles[old].low if bullish else candles[old].high
        price_b = candles[new].low if bullish else candles[new].high
        # Avoid near-equal pivots generating spurious signals.
        if abs(price_b-price_a) / price_a < Decimal('0.001'):
            continue
        osc_a, osc_b = rsi[old], rsi[new]
        if osc_a is None or osc_b is None or abs(osc_b-osc_a) < Decimal(2):
            continue
        regular = (price_b < price_a and osc_b > osc_a) if bullish else (price_b > price_a and osc_b < osc_a)
        hidden = (price_b > price_a and osc_b < osc_a) if bullish else (price_b < price_a and osc_b > osc_a)
        if regular or hidden:
            # The second pivot must be confirmed; do not infer authorization to trade.
            candidates.append((new, 'LONG_CANDIDATE' if bullish else 'SHORT_CANDIDATE'))
    if not candidates:
        return 'NEUTRAL'
    candidates.sort(key=lambda x: x[0], reverse=True)
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0] and candidates[0][1] != candidates[1][1]:
        return 'NEUTRAL'
    return candidates[0][1]


def evaluate(strategy_id: str, batch: ClosedCandleBatch) -> Signal:
    """No trade authorization; every candidate requires separate risk/manual approval."""
    if strategy_id not in BY_ID:
        raise StrategyDataError("UNKNOWN_STRATEGY")
    candles = _validated_candles(batch)
    closing = [c.close for c in candles]
    last = closing[-1]
    if strategy_id == "trend-ladder":
        fast = _ema(closing, 20)
        slow = _ema(closing, 50)
        if fast > slow and last > closing[-2]:
            return "LONG_CANDIDATE"
        if fast < slow and last < closing[-2]:
            return "SHORT_CANDIDATE"
    elif strategy_id == "range-fade":
        recent = candles[-21:-1]
        high = max(c.high for c in recent)
        low = min(c.low for c in recent)
        width = high - low
        if width > 0 and width / last <= Decimal("0.08"):
            if last <= low + width * Decimal("0.15"):
                return "LONG_CANDIDATE"
            if last >= high - width * Decimal("0.15"):
                return "SHORT_CANDIDATE"
    elif strategy_id == "breakout-scout":
        recent = candles[-21:-1]
        mean_volume = sum((c.volume for c in recent), Decimal(0)) / 20
        if candles[-1].volume > mean_volume and mean_volume > 0:
            if last > max(c.high for c in recent):
                return "LONG_CANDIDATE"
            if last < min(c.low for c in recent):
                return "SHORT_CANDIDATE"
    elif strategy_id == "divergence-rsi":
        return _divergence_rsi(candles, closing)
    elif strategy_id == "mean-return":
        recent = closing[-21:-1]
        mean = sum(recent, Decimal(0)) / 20
        variance = sum(((v - mean) ** 2 for v in recent), Decimal(0)) / 20
        if variance > 0:
            sigma = variance.sqrt()
            if last < mean - 2 * sigma:
                return "LONG_CANDIDATE"
            if last > mean + 2 * sigma:
                return "SHORT_CANDIDATE"
    return "NEUTRAL"
