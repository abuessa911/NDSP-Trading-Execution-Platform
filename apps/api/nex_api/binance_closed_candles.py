"""M2-A: public Binance SPOT / USD-M Futures market data, never trading.

An isolated reader; it is deliberately not mounted on the M1 production API.
Only two hard-coded public origins and two market-data GET paths can be called.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Literal

import httpx

Market = Literal["spot", "usdm_futures"]
Interval = Literal["5m", "15m"]

# URLs are not configurable: prevent SSRF, alternate API origins and signing.
ENDPOINTS: dict[Market, tuple[str, str, str]] = {
    "spot": ("https://api.binance.com", "/api/v3/time", "/api/v3/klines"),
    "usdm_futures": ("https://fapi.binance.com", "/fapi/v1/time", "/fapi/v1/klines"),
}
INTERVAL_MS: dict[Interval, int] = {"5m": 300_000, "15m": 900_000}
_SYMBOL = re.compile(r"[A-Z0-9]{5,20}\Z", re.ASCII)
MAX_LIMIT = 200


class MarketDataUnavailable(Exception):
    """Fail closed with a bounded machine code; never log exchange response bodies."""

    def __init__(self, reason_code: str):
        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True, slots=True)
class ClosedCandle:
    symbol: str
    market: Market
    interval: Interval
    open_time_ms: int
    close_time_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True, slots=True)
class ClosedCandleBatch:
    market: Market
    symbol: str
    interval: Interval
    server_time_ms: int
    candles: tuple[ClosedCandle, ...]
    source: Literal["BINANCE_PUBLIC_REST"] = "BINANCE_PUBLIC_REST"


def _valid_ms(value: object) -> int:
    if type(value) is not int or not 1_000_000_000_000 <= value <= 9_000_000_000_000:
        raise MarketDataUnavailable("INVALID_EXCHANGE_TIME")
    return value


def _decimal(value: object, *, positive: bool) -> Decimal:
    if not isinstance(value, str):
        raise MarketDataUnavailable("INVALID_KLINE_PAYLOAD")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise MarketDataUnavailable("INVALID_KLINE_PAYLOAD") from exc
    if not number.is_finite() or number < 0 or (positive and number == 0):
        raise MarketDataUnavailable("INVALID_KLINE_PAYLOAD")
    return number


def _parse_rows(
    data: object, market: Market, symbol: str, interval: Interval, server_ms: int,
) -> tuple[ClosedCandle, ...]:
    if not isinstance(data, list) or not data:
        raise MarketDataUnavailable("EMPTY_KLINES")
    duration = INTERVAL_MS[interval]
    candles: list[ClosedCandle] = []
    previous_open: int | None = None
    for record in data:
        if not isinstance(record, list) or len(record) < 7:
            raise MarketDataUnavailable("INVALID_KLINE_PAYLOAD")
        opened, closed = _valid_ms(record[0]), _valid_ms(record[6])
        if opened % duration or closed != opened + duration - 1:
            raise MarketDataUnavailable("INVALID_KLINE_BOUNDARY")
        if previous_open is not None and opened != previous_open + duration:
            raise MarketDataUnavailable("KLINE_GAP_OR_DUPLICATE")
        previous_open = opened
        # Server clock snapshot is taken before klines: never accept a future/current bar.
        if closed >= server_ms:
            continue
        opening, high, low, closing = (
            _decimal(record[i], positive=True) for i in range(1, 5)
        )
        vol = _decimal(record[5], positive=False)
        if low > min(opening, closing) or high < max(opening, closing) or low > high:
            raise MarketDataUnavailable("INVALID_KLINE_OHLC")
        candles.append(ClosedCandle(
            symbol, market, interval, opened, closed, opening, high, low, closing, vol,
        ))
    if not candles:
        raise MarketDataUnavailable("NO_CLOSED_CANDLES")
    # If delayed or incomplete data arrive, consumers must receive no actionable prices.
    if server_ms - (candles[-1].close_time_ms + 1) > 2 * duration:
        raise MarketDataUnavailable("STALE_CLOSED_CANDLES")
    return tuple(candles)


async def fetch_closed_candles(
    *, market: Market, symbol: str, interval: Interval, limit: int = 100,
    transport: httpx.AsyncBaseTransport | None = None,
) -> ClosedCandleBatch:
    """One bounded, unsigned, no-proxy market read; no daemon, no order endpoints.

    transport is for deterministic MockTransport tests, not user-supplied origins.
    """
    if market not in ENDPOINTS:
        raise ValueError("UNSUPPORTED_BINANCE_MARKET")
    if interval not in INTERVAL_MS:
        raise ValueError("UNSUPPORTED_INTERVAL")
    if not isinstance(symbol, str) or not _SYMBOL.fullmatch(symbol):
        raise ValueError("INVALID_SYMBOL")
    if type(limit) is not int or not 2 <= limit <= MAX_LIMIT:
        raise ValueError("INVALID_KLINE_LIMIT")

    origin, time_path, candles_path = ENDPOINTS[market]
    try:
        async with httpx.AsyncClient(
            base_url=origin, transport=transport, trust_env=False,
            follow_redirects=False, timeout=httpx.Timeout(5.0),
            headers={"Accept": "application/json", "User-Agent": "NEX-M2A-public-readonly/1"},
        ) as client:
            clock_resp = await client.get(time_path)
            clock_resp.raise_for_status()
            clock = clock_resp.json()
            if not isinstance(clock, dict):
                raise MarketDataUnavailable("INVALID_SERVER_TIME")
            server_ms = _valid_ms(clock.get("serverTime"))
            candle_resp = await client.get(candles_path, params={
                "symbol": symbol, "interval": interval, "limit": limit,
            })
            candle_resp.raise_for_status()
            candles = _parse_rows(candle_resp.json(), market, symbol, interval, server_ms)
            return ClosedCandleBatch(market, symbol, interval, server_ms, candles)
    except httpx.TimeoutException as exc:
        raise MarketDataUnavailable("MARKET_DATA_TIMEOUT") from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {418, 429}:
            raise MarketDataUnavailable("EXCHANGE_RATE_LIMITED") from exc
        if exc.response.status_code in {403, 451}:
            raise MarketDataUnavailable("EXCHANGE_ACCESS_UNAVAILABLE") from exc
        raise MarketDataUnavailable("EXCHANGE_HTTP_UNAVAILABLE") from exc
    except (httpx.RequestError, ValueError) as exc:
        # Malformed JSON, transport errors and illegal redirects fail closed.
        raise MarketDataUnavailable("MARKET_DATA_UNAVAILABLE") from exc
