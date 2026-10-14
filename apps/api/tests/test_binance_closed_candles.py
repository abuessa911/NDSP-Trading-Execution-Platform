"""M2-A consumer contract: no secrets, orders, partial bars or silent stale prices."""

import asyncio
from decimal import Decimal

import httpx
import pytest

from nex_api.binance_closed_candles import MarketDataUnavailable, fetch_closed_candles

START = 1_796_000_100_000  # 5m and 15m aligned UTC sample time


def candle(start: int, duration: int = 300_000) -> list[object]:
    return [start, "100.0", "103.0", "99.0", "102.5", "1.20", start + duration - 1,
            "120.5", 12, "0.4", "40.3", "0"]


def fake_transport(
    *, market: str = "spot", interval: str = "5m", status: int = 200,
    rows: object | None = None, server: int | None = None,
    calls: list[httpx.Request] | None = None,
) -> httpx.MockTransport:
    duration = 300_000 if interval == "5m" else 900_000
    # UTC boundary, deterministic irrespective of which year the tests run.
    aligned = (START // duration) * duration
    payload = rows if rows is not None else [candle(aligned, duration),
                                               candle(aligned + duration, duration)]
    time = server if server is not None else aligned + 2 * duration + 30_000
    prefix = "/api/v3" if market == "spot" else "/fapi/v1"

    def handle(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request)
        if request.url.path == prefix + "/time":
            return httpx.Response(200, json={"serverTime": time})
        if request.url.path == prefix + "/klines":
            return httpx.Response(status, json=payload)
        return httpx.Response(500)

    return httpx.MockTransport(handle)


@pytest.mark.parametrize("market,origin,prefix", [
    ("spot", "api.binance.com", "/api/v3"),
    ("usdm_futures", "fapi.binance.com", "/fapi/v1"),
])
@pytest.mark.parametrize("interval", ["5m", "15m"])
def test_closed_spot_and_usdm_only(market: str, origin: str, prefix: str, interval: str) -> None:
    requests: list[httpx.Request] = []
    result = asyncio.run(fetch_closed_candles(
        market=market, symbol="BTCUSDT", interval=interval, limit=10,
        transport=fake_transport(market=market, interval=interval, calls=requests),
    ))
    assert len(result.candles) == 2
    assert result.candles[-1].close == Decimal("102.5")
    assert result.market == market
    assert result.source == "BINANCE_PUBLIC_REST"
    assert all(r.method == "GET" for r in requests)
    assert [r.url.path for r in requests] == [prefix + "/time", prefix + "/klines"]
    assert all(r.url.host == origin for r in requests)
    assert all("authorization" not in r.headers and "x-mbx-apikey" not in r.headers
               for r in requests)
    assert str(requests[-1].url.params["symbol"]) == "BTCUSDT"
    assert str(requests[-1].url.params["interval"]) == interval


def test_current_open_candle_is_excluded_even_when_returned() -> None:
    duration = 300_000
    aligned = (START // duration) * duration
    server = aligned + 2 * duration + 10_000
    result = asyncio.run(fetch_closed_candles(
        market="spot", symbol="ETHUSDT", interval="5m",
        transport=fake_transport(rows=[candle(aligned), candle(aligned + duration),
                                   candle(aligned + 2 * duration)], server=server),
    ))
    assert len(result.candles) == 2
    assert all(c.close_time_ms < server for c in result.candles)


def test_only_open_candle_is_blocked() -> None:
    aligned = (START // 300_000) * 300_000
    with pytest.raises(MarketDataUnavailable, match="NO_CLOSED_CANDLES"):
        asyncio.run(fetch_closed_candles(
            market="spot", symbol="BTCUSDT", interval="5m",
            transport=fake_transport(rows=[candle(aligned)], server=aligned + 10_000),
        ))


@pytest.mark.parametrize("problem,reason", [
    ([["bad"]], "INVALID_KLINE_PAYLOAD"),
    ([candle(1_796_000_100_001)], "INVALID_KLINE_BOUNDARY"),
    ([candle(1_796_000_100_000 // 300_000 * 300_000)] * 2, "KLINE_GAP_OR_DUPLICATE"),
])
def test_invalid_market_payload_is_rejected(problem: object, reason: str) -> None:
    with pytest.raises(MarketDataUnavailable, match=reason):
        asyncio.run(fetch_closed_candles(
            market="spot", symbol="BTCUSDT", interval="5m",
            transport=fake_transport(rows=problem),
        ))


def test_missing_interval_is_blocked() -> None:
    aligned = (START // 300_000) * 300_000
    with pytest.raises(MarketDataUnavailable, match="KLINE_GAP_OR_DUPLICATE"):
        asyncio.run(fetch_closed_candles(
            market="spot", symbol="BTCUSDT", interval="5m",
            transport=fake_transport(rows=[candle(aligned), candle(aligned + 600_000)]),
        ))


def test_stale_candles_fail_closed() -> None:
    aligned = (START // 300_000) * 300_000
    with pytest.raises(MarketDataUnavailable, match="STALE_CLOSED_CANDLES"):
        asyncio.run(fetch_closed_candles(
            market="spot", symbol="BTCUSDT", interval="5m",
            transport=fake_transport(rows=[candle(aligned)], server=aligned + 1_500_000),
        ))


def test_bad_ohlc_and_non_finite_number_are_rejected() -> None:
    aligned = (START // 300_000) * 300_000
    bad_ohlc = candle(aligned)
    bad_ohlc[2] = "98"
    bad_nan = candle(aligned)
    bad_nan[4] = "NaN"
    for row, code in [(bad_ohlc, "INVALID_KLINE_OHLC"),
                      (bad_nan, "INVALID_KLINE_PAYLOAD")]:
        with pytest.raises(MarketDataUnavailable, match=code):
            asyncio.run(fetch_closed_candles(
                market="spot", symbol="BTCUSDT", interval="5m",
                transport=fake_transport(rows=[row]),
            ))


@pytest.mark.parametrize("status,reason", [
    (429, "EXCHANGE_RATE_LIMITED"),
    (418, "EXCHANGE_RATE_LIMITED"),
    (451, "EXCHANGE_ACCESS_UNAVAILABLE"),
    (503, "EXCHANGE_HTTP_UNAVAILABLE"),
])
def test_http_failure_reports_bounded_code(status: int, reason: str) -> None:
    with pytest.raises(MarketDataUnavailable, match=reason):
        asyncio.run(fetch_closed_candles(
            market="spot", symbol="BTCUSDT", interval="5m",
            transport=fake_transport(status=status),
        ))


@pytest.mark.parametrize("overrides", [
    {"market": "coinm_futures"},
    {"interval": "1m"},
    {"symbol": "BTCUSDT/../orders"},
    {"symbol": "btcusdt"},
    {"limit": 1000},
    {"limit": 1},
    {"limit": True},
])
def test_unsupported_input_does_not_reach_network(overrides: dict[str, object]) -> None:
    requests: list[httpx.Request] = []
    args: dict[str, object] = {"market": "spot", "symbol": "BTCUSDT", "interval": "5m",
                               "transport": fake_transport(calls=requests)}
    args.update(overrides)
    with pytest.raises(ValueError):
        asyncio.run(fetch_closed_candles(**args))  # type: ignore[arg-type]
    assert requests == []


def test_server_time_corruption_blocks_data() -> None:
    requests: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        requests.append(req)
        return httpx.Response(200, json={"serverTime": True})

    with pytest.raises(MarketDataUnavailable, match="INVALID_EXCHANGE_TIME"):
        asyncio.run(fetch_closed_candles(
            market="spot", symbol="BTCUSDT", interval="5m",
            transport=httpx.MockTransport(handler),
        ))
    assert len(requests) == 1


def test_response_schema_uses_open_closed_boundary_not_host_clock() -> None:
    aligned = (START // 300_000) * 300_000
    batch = asyncio.run(fetch_closed_candles(
        market="spot", symbol="BTCUSDT", interval="5m",
        transport=fake_transport(rows=[candle(aligned)], server=aligned + 300_000),
    ))
    assert batch.candles[0].close_time_ms == aligned + 299_999
