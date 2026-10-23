"""Authenticated multi-strategy RESEARCH scanner; zero order-writing imports.

Five explicit strategies are evaluated against real exchange-closed candles.
Enabling a scanner NEVER enables trade execution, NDSP authority, or orders.
Active scans expire after 15 minutes unless restarted by an operator.
"""
from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from nex_api.binance_closed_candles import MarketDataUnavailable, fetch_closed_candles
from nex_api.dependencies import Principal, failure, get_current_principal, get_operator, get_provisioned_user
from nex_api.models import User
from nex_api.routes.trading_control import verify_mutation, redis_store
from nex_api.strategy_signals import (ALLOWED_INTERVALS, ALLOWED_SYMBOLS, BY_ID,
                                       STRATEGIES, StrategyDataError, evaluate)

log = logging.getLogger("hunter.strategy_scanner")
router = APIRouter(prefix="/api/v1/trading/strategies", tags=["hunter research scanner"],
                   include_in_schema=False)
ACTIVE_PREFIX = "hunter:strategy:enabled:v1:"
RESULT_PREFIX = "hunter:strategy:result:v1:"
ACTIVE_TTL = 900
SCAN_INTERVAL_SECONDS = 60
SCAN_CAP_PER_CYCLE = 24

class StrategyStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_bound: bool = Field(default=False, strict=True)
    symbol: Literal["BTCUSDT", "ETHUSDT", "SOLUSDT", "LINKUSDT",
                    "XRPUSDT", "DOGEUSDT", "BNBUSDT"]
    interval: Literal["5m", "15m", "1h", "4h", "1d"]

class StrategyStatus(BaseModel):
    id: str
    name: str
    rule: str
    symbol: str
    interval: str
    status: Literal["STOPPED", "SCANNING", "STALLED"]
    signal: Literal["LONG_CANDIDATE", "SHORT_CANDIDATE", "NEUTRAL"] | None
    last_closed_price: str | None
    last_candle_closed_ms: int | None
    last_checked_ms: int | None
    expires_in_seconds: int
    market_source: Literal["BINANCE_USDM_PUBLIC_CLOSED_CANDLES"] = "BINANCE_USDM_PUBLIC_CLOSED_CANDLES"
    ndsp_verified: Literal[False] = False
    execution_enabled: Literal[False] = False

class StrategyList(BaseModel):
    strategies: list[StrategyStatus]
    order_submission_available: Literal[False] = False

def active_key(user: User, strategy_id: str) -> str:
    return f"{ACTIVE_PREFIX}{user.tenant_id}:{user.id}:{strategy_id}"

def result_key(key: str) -> str:
    if not key.startswith(ACTIVE_PREFIX):
        raise ValueError("INVALID_STRATEGY_KEY")
    return RESULT_PREFIX + key.removeprefix(ACTIVE_PREFIX)

def definition(strategy_id: str):
    found = BY_ID.get(strategy_id)
    if found is None:
        raise failure("STRATEGY_NOT_FOUND", "Unknown strategy.", 404)
    return found

def _decode(raw):
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw) if raw is not None else None

async def status(store, user: User, item) -> StrategyStatus:
    key = active_key(user, item.id)
    try:
        raw, raw_result, ttl = await asyncio.gather(
            store.get(key), store.get(result_key(key)), store.ttl(key)
        )
        conf = _decode(raw)
        last = _decode(raw_result)
    except (ValueError, TypeError, UnicodeError, KeyError, AttributeError):
        raise failure("STRATEGY_STATE_INVALID", "Scanner state cannot be trusted.", 503) from None
    except Exception:
        raise failure("STRATEGY_STORE_UNAVAILABLE", "Scanner store unavailable.", 503) from None
    if conf is None:
        return StrategyStatus(id=item.id, name=item.name, rule=item.rule,
                              symbol=item.symbol, interval=item.interval,
                              status="STOPPED", signal=None, last_closed_price=None,
                              last_candle_closed_ms=None, last_checked_ms=None,
                              expires_in_seconds=0)
    if (not isinstance(conf, dict) or conf.get("symbol") not in ALLOWED_SYMBOLS
            or conf.get("interval") not in ALLOWED_INTERVALS
            or not isinstance(conf.get("nonce"), str)):
        raise failure("STRATEGY_STATE_INVALID", "Invalid scanner state.", 503)
    valid_last = last if (isinstance(last, dict)
                          and last.get("nonce") == conf["nonce"]) else None
    checked = valid_last.get("checked_ms") if valid_last else None
    fresh = (type(checked) is int and checked <= int(time.time() * 1000)
             and int(time.time() * 1000) - checked < 180_000)
    return StrategyStatus(
        id=item.id, name=item.name, rule=item.rule,
        symbol=conf["symbol"], interval=conf["interval"],
        status="SCANNING" if fresh else "STALLED",
        signal=valid_last.get("signal") if fresh else None,
        last_closed_price=valid_last.get("close") if fresh else None,
        last_candle_closed_ms=valid_last.get("closed_ms") if fresh else None,
        last_checked_ms=checked if fresh else None,
        expires_in_seconds=max(ttl, 0),
    )

async def _scan_once(strategy_id: str, symbol: str, interval: str, nonce: str):
    if strategy_id not in BY_ID or symbol not in ALLOWED_SYMBOLS or interval not in ALLOWED_INTERVALS:
        raise StrategyDataError("SCAN_CONFIGURATION_INVALID")
    batch = await fetch_closed_candles(
        market="usdm_futures", symbol=symbol, interval=interval, limit=80
    )
    signal = evaluate(strategy_id, batch)
    last = batch.candles[-1]
    return json.dumps({
        "nonce": nonce, "signal": signal,
        "close": str(last.close), "closed_ms": last.close_time_ms,
        "checked_ms": int(time.time() * 1000),
    }, separators=(",", ":"))

@router.get("", response_model=StrategyList)
async def get_strategies(
    request: Request,
    user: Annotated[User, Depends(get_provisioned_user)],
) -> StrategyList:
    store = redis_store(request)
    return StrategyList(strategies=[await status(store, user, s) for s in STRATEGIES])

@router.post("/{strategy_id}/start", response_model=StrategyStatus)
async def start_strategy(
    strategy_id: str, body: StrategyStart, request: Request,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> StrategyStatus:
    verify_mutation(request, principal)
    item = definition(strategy_id)
    if not request.app.state.settings.hunter_market_monitor_enabled:
        raise failure("STRATEGY_WORKER_DISABLED", "Scanner worker disabled.", 503)
    store = redis_store(request)
    snapshot = None
    if body.workspace_bound:
        from nex_api.routes.trading_profile import workspace_snapshot
        snapshot = await workspace_snapshot(request, user)
        selected = snapshot[0]
        if body.symbol != selected.symbol or body.interval != selected.interval:
            raise failure("WORKSPACE_CHANGED_RETRY", "Selection changed; start again.", 409)
    nonce = secrets.token_hex(16)
    # Real verified market read BEFORE reporting a running scanner.
    try:
        raw = await _scan_once(strategy_id, body.symbol, body.interval, nonce)
    except (MarketDataUnavailable, StrategyDataError):
        raise failure("STRATEGY_MARKET_UNAVAILABLE", "Closed market candles unavailable.", 503) from None
    key = active_key(user, item.id)
    record = json.dumps({"nonce": nonce, "symbol": body.symbol,
                         "interval": body.interval}, separators=(",", ":"))
    try:
        if snapshot is not None:
            from nex_api.routes.trading_profile import key as profile_key, workspace_key
            confirmed = await store.eval(CONFIRMED_SCANNER_START, 4,
                key, result_key(key), profile_key(user), workspace_key(user),
                snapshot[1], snapshot[2], record, raw, ACTIVE_TTL)
        else:
            # Compatibility for explicitly configured per-strategy API clients.
            await store.delete(key)
            await store.set(result_key(key), raw, ex=ACTIVE_TTL)
            await store.set(key, record, ex=ACTIVE_TTL)
            confirmed = True
    except Exception:
        raise failure("STRATEGY_STORE_UNAVAILABLE", "Scanner store unavailable.", 503) from None
    if not confirmed:
        raise failure("WORKSPACE_CHANGED_RETRY", "Selection changed; start again.", 409)
    return await status(store, user, item)

@router.post("/{strategy_id}/stop", response_model=StrategyStatus)
async def stop_strategy(
    strategy_id: str, request: Request,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> StrategyStatus:
    verify_mutation(request, principal)
    item = definition(strategy_id)
    key = active_key(user, item.id)
    try:
        # Active key removed first; stale worker results are ignored by nonce checking.
        await redis_store(request).delete(key)
        await redis_store(request).delete(result_key(key))
    except Exception:
        raise failure("STRATEGY_STORE_UNAVAILABLE", "Scanner store unavailable.", 503) from None
    return await status(redis_store(request), user, item)

CONFIRMED_SCANNER_START = """
if (redis.call('GET', KEYS[3]) or '') ~= ARGV[1]
   or (redis.call('GET', KEYS[4]) or '') ~= ARGV[2] then return 0 end
redis.call('SET', KEYS[2], ARGV[4], 'EX', ARGV[5])
redis.call('SET', KEYS[1], ARGV[3], 'EX', ARGV[5])
return 1
"""


async def strategy_scan_worker(redis) -> None:
    """Bounded multi-user scanner. It has NO broker/NDSP/order capability."""
    while True:
        try:
            checked = 0
            async for key in redis.scan_iter(match=ACTIVE_PREFIX + "*", count=32):
                if checked >= SCAN_CAP_PER_CYCLE:
                    break
                checked += 1
                key = key.decode("ascii") if isinstance(key, bytes) else key
                strategy_id = key.rsplit(":", 1)[-1]
                if strategy_id not in BY_ID:
                    continue
                lock = key + ":worker-lock"
                if not await redis.set(lock, "1", nx=True, ex=35):
                    continue
                try:
                    raw = await redis.get(key)
                    if raw is None:
                        continue
                    conf = _decode(raw)
                    if (not isinstance(conf, dict)
                            or conf.get("symbol") not in ALLOWED_SYMBOLS
                            or conf.get("interval") not in ALLOWED_INTERVALS
                            or not isinstance(conf.get("nonce"), str)):
                        continue
                    raw_result = await _scan_once(
                        strategy_id, conf["symbol"], conf["interval"], conf["nonce"]
                    )
                    # Results are separate from activation: stop never gets undone.
                    ttl = await redis.ttl(key)
                    if ttl > 0:
                        await redis.set(result_key(key), raw_result, ex=min(ttl, ACTIVE_TTL))
                except (MarketDataUnavailable, StrategyDataError):
                    log.warning("strategy_candle_scan_failed")
                finally:
                    await redis.delete(lock)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.warning("strategy_scanner_unavailable")
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)
