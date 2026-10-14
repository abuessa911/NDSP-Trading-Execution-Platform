"""M2-A internal experimental adapter: admin/MFA only, Redis-gated, no orders.

Off by default and forbidden in production. No exchange price persistence.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from redis.exceptions import RedisError

from nex_api.binance_closed_candles import (
    INTERVAL_MS,
    ClosedCandleBatch,
    Market,
    Interval,
    MarketDataUnavailable,
    fetch_closed_candles,
)
from nex_api.dependencies import get_administrator
from nex_api.models import User

router = APIRouter(prefix="/api/v1/admin/market-data", include_in_schema=False)

# Fixed-window budgets: 6 user/tenant and 30 market-wide reads per minute.
# Each permitted read makes exactly two public Binance GETs.
TENANT_BUDGET = 6
GLOBAL_BUDGET = 30
BUDGET_WINDOW_SECONDS = 60
OBSERVATION_TTL = 900

_RATE_SCRIPT = """
local t = tonumber(redis.call('GET', KEYS[1]) or '0')
local g = tonumber(redis.call('GET', KEYS[2]) or '0')
if t >= tonumber(ARGV[1]) or g >= tonumber(ARGV[2]) then return 0 end
redis.call('INCR', KEYS[1])
redis.call('INCR', KEYS[2])
if t == 0 then redis.call('EXPIRE', KEYS[1], tonumber(ARGV[3])) end
if g == 0 then redis.call('EXPIRE', KEYS[2], tonumber(ARGV[3])) end
return 1
"""


class KlineView(BaseModel):
    open_time_ms: int
    close_time_ms: int
    open: str
    high: str
    low: str
    close: str
    volume: str


class MarketDataView(BaseModel):
    status: Literal["READ_ONLY_OK"]
    source: Literal["BINANCE_PUBLIC_REST"]
    market: Market
    interval: Literal["5m", "15m"]
    symbol: str
    tenant_id: str
    server_time_ms: int
    candles: list[KlineView]
    orders_sent: Literal[0] = 0


class MarketObservationView(BaseModel):
    status: Literal["NOT_OBSERVED", "READ_ONLY_OK", "BLOCKED"]
    reason_code: str | None = None
    market: Market
    interval: Literal["5m", "15m"]
    symbol: str
    # Age is intentionally not a proxy for Binance server-clock freshness.
    server_time_ms: int | None = None
    latest_closed_ms: int | None = None


def blocked(reason: str, *, status: int = 503) -> HTTPException:
    return HTTPException(status_code=status, detail={
        "reason_code": reason, "message": "Market-data request unavailable.",
    })


def require_enabled(request: Request) -> None:
    if not request.app.state.settings.m2a_public_market_enabled:
        raise blocked("M2A_INTERNAL_MARKET_DISABLED")


def validate(market: str, symbol: str, interval: str, limit: int) -> None:
    import re

    if (market not in ("spot", "usdm_futures")
            or interval not in INTERVAL_MS
            or not re.fullmatch(r"[A-Z0-9]{5,20}", symbol, flags=re.ASCII)
            or type(limit) is not int or not 2 <= limit <= 30):
        raise blocked("M2A_INVALID_REQUEST", status=422)


def key_prefix(user: User, market: str, symbol: str, interval: str) -> str:
    # All components come from server-verified identity or strict allowlists.
    return f"nex:m2a:market:{user.tenant_id}:{market}:{symbol}:{interval}"


async def quota(request: Request, user: User, market: str) -> object:
    redis = request.app.state.redis
    if redis is None:
        raise blocked("M2A_REDIS_UNAVAILABLE")
    tenant_key = f"nex:m2a:quota:tenant:{user.tenant_id}:{market}"
    global_key = f"nex:m2a:quota:global:{market}"
    try:
        async with asyncio.timeout(3):
            granted = await redis.eval(
                _RATE_SCRIPT, 2, tenant_key, global_key,
                TENANT_BUDGET, GLOBAL_BUDGET, BUDGET_WINDOW_SECONDS,
            )
    except (RedisError, TimeoutError, OSError, AttributeError) as exc:
        raise blocked("M2A_REDIS_UNAVAILABLE") from exc
    if granted != 1:
        raise blocked("M2A_RATE_BUDGET_EXHAUSTED", status=429)
    return redis


async def record(redis: object, key: str, value: str) -> None:
    try:
        async with asyncio.timeout(3):
            await redis.set(key, value, ex=OBSERVATION_TTL)  # type: ignore[attr-defined]
    except (RedisError, TimeoutError, OSError, AttributeError) as exc:
        raise blocked("M2A_OBSERVABILITY_UNAVAILABLE") from exc


def render(batch: ClosedCandleBatch, tenant_id: str) -> MarketDataView:
    def d(v: Decimal) -> str:
        return str(v)

    return MarketDataView(
        status="READ_ONLY_OK", source=batch.source, market=batch.market,
        interval=batch.interval, symbol=batch.symbol, tenant_id=tenant_id,
        server_time_ms=batch.server_time_ms,
        candles=[KlineView(
            open_time_ms=c.open_time_ms, close_time_ms=c.close_time_ms,
            open=d(c.open), high=d(c.high), low=d(c.low),
            close=d(c.close), volume=d(c.volume),
        ) for c in batch.candles],
    )


@router.get("/closed-candles", response_model=MarketDataView)
async def market_candles(
    request: Request,
    user: Annotated[User, Depends(get_administrator)],
    market: Market = Query(...),
    symbol: str = Query(...),
    interval: Interval = Query(...),
    limit: int = Query(default=5, ge=2, le=30),
) -> MarketDataView:
    require_enabled(request)
    validate(market, symbol, interval, limit)
    redis = await quota(request, user, market)
    key = key_prefix(user, market, symbol, interval)
    try:
        reader = getattr(request.app.state, "market_data_reader", fetch_closed_candles)
        batch = await reader(market=market, symbol=symbol, interval=interval, limit=limit)
    except MarketDataUnavailable as exc:
        # Only bounded application reason codes; no raw HTTP or exchange bodies.
        await record(redis, key, "BLOCKED:" + exc.reason_code)
        raise blocked(exc.reason_code) from exc
    except Exception as exc:
        await record(redis, key, "BLOCKED:MARKET_DATA_UNAVAILABLE")
        raise blocked("MARKET_DATA_UNAVAILABLE") from exc
    await record(redis, key, "READ_ONLY_OK:" + str(batch.server_time_ms)
                 + ":" + str(batch.candles[-1].close_time_ms))
    return render(batch, str(user.tenant_id))


@router.get("/observation", response_model=MarketObservationView)
async def market_observation(
    request: Request,
    user: Annotated[User, Depends(get_administrator)],
    market: Market = Query(...),
    symbol: str = Query(...),
    interval: Interval = Query(...),
) -> MarketObservationView:
    require_enabled(request)
    validate(market, symbol, interval, 2)
    redis = request.app.state.redis
    if redis is None:
        raise blocked("M2A_REDIS_UNAVAILABLE")
    try:
        async with asyncio.timeout(3):
            raw = await redis.get(key_prefix(user, market, symbol, interval))
    except (RedisError, TimeoutError, OSError, AttributeError) as exc:
        raise blocked("M2A_REDIS_UNAVAILABLE") from exc
    if raw is None:
        return MarketObservationView(
            status="NOT_OBSERVED", market=market, symbol=symbol, interval=interval,
        )
    value = raw.decode("ascii") if isinstance(raw, bytes) else str(raw)
    if value.startswith("BLOCKED:"):
        code = value.partition(":")[2]
        if code not in {
            "MARKET_DATA_TIMEOUT", "EXCHANGE_RATE_LIMITED", "EXCHANGE_ACCESS_UNAVAILABLE",
            "EXCHANGE_HTTP_UNAVAILABLE", "MARKET_DATA_UNAVAILABLE", "INVALID_EXCHANGE_TIME",
            "INVALID_KLINE_PAYLOAD", "INVALID_SERVER_TIME", "INVALID_KLINE_BOUNDARY",
            "INVALID_KLINE_OHLC", "KLINE_GAP_OR_DUPLICATE", "STALE_CLOSED_CANDLES",
            "NO_CLOSED_CANDLES", "EMPTY_KLINES",
        }:
            raise blocked("M2A_OBSERVATION_INVALID")
        return MarketObservationView(
            status="BLOCKED", reason_code=code,
            market=market, symbol=symbol, interval=interval,
        )
    parts = value.split(":")
    if len(parts) != 3 or parts[0] != "READ_ONLY_OK":
        raise blocked("M2A_OBSERVATION_INVALID")
    try:
        server_time = int(parts[1])
        closed_time = int(parts[2])
    except ValueError as exc:
        raise blocked("M2A_OBSERVATION_INVALID") from exc
    return MarketObservationView(
        status="READ_ONLY_OK", market=market, symbol=symbol, interval=interval,
        server_time_ms=server_time, latest_closed_ms=closed_time,
    )
