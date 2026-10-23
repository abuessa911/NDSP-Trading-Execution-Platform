"""Hunter authenticated control plane: read-only market monitor + testnet key check.

There are deliberately NO order-writing exchange calls or live credential scopes.
Redis is an external coordination store; it is not a trade ledger.
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
import hmac
import json
import logging
import secrets
import time
from typing import Annotated, Literal

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from nex_api.binance_closed_candles import MarketDataUnavailable, fetch_closed_candles
from nex_api.binance_testnet_connector import ExchangeConnectivityError, probe_testnet_account
from nex_api.binance_live_readonly_connector import LiveConnectivityError, probe_live_readonly_account
from nex_api.dependencies import Principal, failure, get_current_principal, get_operator, get_provisioned_user
from nex_api.models import User
from nex_api.routes.auth import same_origin
from nex_api.routes.trading_profile import workspace_snapshot, workspace_key, key as profile_key

router = APIRouter(prefix="/api/v1/trading/control", tags=["hunter read-only control"],
                   include_in_schema=False)
log = logging.getLogger("hunter.market_monitor")
PREFIX = "hunter:monitor:v1:"
CONNECTION_PREFIX = "hunter:exchange:testnet:v1:"
LIVE_CONNECTION_PREFIX = "hunter:exchange:live-readonly:v1:"
MONITOR_TTL_SECONDS = 900
CONNECT_TTL_SECONDS = 86400
LIVE_CONNECT_TTL_SECONDS = 3600
STALE_AFTER_SECONDS = 100
# Maximum accounts polled per cycle; no order calls, no user supplied URLs.
MAX_MONITORS = 20


class ConnectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_key: SecretStr = Field(min_length=10, max_length=256)
    api_secret: SecretStr = Field(min_length=1, max_length=512)


class ControlView(BaseModel):
    mode: Literal["BINANCE_USDM_PUBLIC_MONITOR"] = "BINANCE_USDM_PUBLIC_MONITOR"
    state: Literal["STOPPED", "MONITORING", "STALLED"] = "STOPPED"
    symbol: str = "BTCUSDT"
    interval: str = "5m"
    last_closed_price: str | None = None
    last_candle_closed_ms: int | None = None
    last_checked_ms: int | None = None
    expires_in_seconds: int = 0
    testnet_key_saved: bool = False
    live_readonly_key_saved: bool = False
    execution_enabled: Literal[False] = False
    order_submission_available: Literal[False] = False


class LiveConnectionResult(BaseModel):
    venue: Literal["BINANCE_USDM_MAINNET_READ_ONLY"] = "BINANCE_USDM_MAINNET_READ_ONLY"
    authenticated: bool
    read_only_permission_verified: bool
    ip_restricted: bool
    encrypted_server_storage: bool
    expires_in_seconds: int
    execution_enabled: Literal[False] = False


class ConnectionResult(BaseModel):
    venue: Literal["BINANCE_USDM_TESTNET"] = "BINANCE_USDM_TESTNET"
    authenticated: bool
    encrypted_server_storage: bool
    expires_in_seconds: int
    execution_enabled: Literal[False] = False


def monitor_key(user: User) -> str:
    return f"{PREFIX}{user.tenant_id}:{user.id}"


def connection_key(user: User) -> str:
    return f"{CONNECTION_PREFIX}{user.tenant_id}:{user.id}"


def live_connection_key(user: User) -> str:
    return f"{LIVE_CONNECTION_PREFIX}{user.tenant_id}:{user.id}"


def redis_store(request: Request):
    store = getattr(request.app.state, "redis", None)
    if store is None:
        raise failure("MONITOR_STORE_UNAVAILABLE", "Redis service not configured.", 503)
    return store


def verify_mutation(request: Request, principal: Principal) -> None:
    same_origin(request)
    csrf = (principal.session_data or {}).get("csrf")
    submitted = request.headers.get("x-nex-csrf", "")
    if not isinstance(csrf, str) or not csrf or not hmac.compare_digest(csrf, submitted):
        raise failure("CSRF_NOT_VALID", "A valid browser CSRF token is required.")


def cipher(request: Request) -> Fernet:
    secret = getattr(request.app.state.settings, "hunter_testnet_vault_key", None)
    if secret is None:
        raise failure("TESTNET_VAULT_UNAVAILABLE", "Testnet credential storage is not configured.", 503)
    try:
        return Fernet(secret.get_secret_value().encode("ascii"))
    except (ValueError, TypeError) as exc:
        raise failure("TESTNET_VAULT_UNAVAILABLE", "Testnet credential storage is unavailable.", 503) from None



@contextmanager
def testnet_credential_guard(request, user, api_key=None):
    service = getattr(request.app.state, "testnet_execution", None)
    if service is None:
        yield
        return
    from nex_api.hunter_live_executor import Halt
    try:
        with service.session(f"{user.tenant_id}:{user.id}") as account:
            account.credential_change(api_key)
            yield
    except Halt as error:
        raise failure(str(error), "Demo credentials cannot change during this operation.", 409) from None


def live_cipher(request: Request) -> Fernet:
    secret = getattr(request.app.state.settings, "hunter_live_vault_key", None)
    if secret is None:
        raise failure("LIVE_VAULT_UNAVAILABLE", "Mainnet read-only credential vault is not configured.", 503)
    try:
        return Fernet(secret.get_secret_value().encode("ascii"))
    except (ValueError, TypeError):
        raise failure("LIVE_VAULT_UNAVAILABLE", "Mainnet read-only credential vault is unavailable.", 503) from None


def view(raw: bytes | str | None, ttl: int, connected: bool, live_connected: bool = False) -> ControlView:
    if raw is None:
        return ControlView(testnet_key_saved=connected, live_readonly_key_saved=live_connected)
    try:
        item = json.loads(raw)
        if item["desired"] != "RUNNING":
            return ControlView(testnet_key_saved=connected, live_readonly_key_saved=live_connected)
        checked = item.get("checked_ms")
        now = int(time.time() * 1000)
        state = ("MONITORING" if type(checked) is int and ttl > 0
                 and 0 <= now - checked < STALE_AFTER_SECONDS * 1000
                 else "STALLED")
        return ControlView(
            state=state,
            symbol=item.get("symbol", "BTCUSDT"),
            interval=item.get("interval", "5m"),
            last_closed_price=item.get("close") if state == "MONITORING" else None,
            last_candle_closed_ms=item.get("closed_ms") if state == "MONITORING" else None,
            last_checked_ms=checked,
            expires_in_seconds=max(ttl, 0),
            testnet_key_saved=connected,
            live_readonly_key_saved=live_connected,
        )
    except (ValueError, KeyError, TypeError):
        raise failure("MONITOR_STATE_INVALID", "Stored monitoring state is invalid.", 503)


async def state(request: Request, user: User) -> ControlView:
    store = redis_store(request)
    try:
        raw, ttl, exists, live_exists = await asyncio.gather(
            store.get(monitor_key(user)),
            store.ttl(monitor_key(user)),
            store.exists(connection_key(user)),
            store.exists(live_connection_key(user)),
        )
        return view(raw, ttl, bool(exists), bool(live_exists))
    except Exception:
        raise failure("MONITOR_STORE_UNAVAILABLE", "Monitoring store is unavailable.", 503) from None


@router.get("", response_model=ControlView)
async def get_control(request: Request, user: Annotated[User, Depends(get_provisioned_user)]):
    return await state(request, user)


@router.post("/start", response_model=ControlView)
async def start_monitor(
    request: Request,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)],
):
    verify_mutation(request, principal)
    if not request.app.state.settings.hunter_market_monitor_enabled:
        raise failure("MONITOR_DISABLED", "Monitoring worker is not enabled.", 503)
    store = redis_store(request)
    selected, expected_style, expected_workspace = await workspace_snapshot(request, user)
    # Read the confirmed account-scoped selection, never a browser-only label.
    try:
        batch = await fetch_closed_candles(
            market="usdm_futures", symbol=selected.symbol, interval=selected.interval, limit=3
        )
    except MarketDataUnavailable:
        raise failure("MARKET_SOURCE_UNAVAILABLE", "Market data is unavailable.", 503) from None
    item = batch.candles[-1]
    now = int(time.time() * 1000)
    record = {"desired": "RUNNING", "nonce": secrets.token_hex(16),
              "symbol": selected.symbol, "interval": selected.interval,
              "close": str(item.close), "closed_ms": item.close_time_ms, "checked_ms": now}
    try:
        # Running expires automatically. Deliberately non-automatic: no strategies/orders.
        confirmed = await store.eval(CONFIRMED_MONITOR_START, 3,
            monitor_key(user), profile_key(user), workspace_key(user),
            expected_style, expected_workspace, json.dumps(record), MONITOR_TTL_SECONDS)
    except Exception:
        raise failure("MONITOR_STORE_UNAVAILABLE", "Monitoring store is unavailable.", 503) from None
    if not confirmed:
        raise failure("WORKSPACE_CHANGED_RETRY", "Selection changed; start again.", 409)
    return await state(request, user)


@router.post("/stop", response_model=ControlView)
async def stop_monitor(
    request: Request,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)],
):
    verify_mutation(request, principal)
    try:
        await redis_store(request).delete(monitor_key(user))
    except Exception:
        raise failure("MONITOR_STORE_UNAVAILABLE", "Monitoring store is unavailable.", 503) from None
    return await state(request, user)


@router.post("/testnet/connect", response_model=ConnectionResult)
async def testnet_connect(
    request: Request,
    credentials: ConnectionRequest,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)],
):
    verify_mutation(request, principal)
    encryptor = cipher(request)  # fail before external call if encryption unavailable
    api_key, api_secret = (credentials.api_key.get_secret_value(),
                           credentials.api_secret.get_secret_value())
    with testnet_credential_guard(request, user, api_key):
        try:
            result = await probe_testnet_account(api_key, api_secret)
        except ExchangeConnectivityError:
            raise failure("TESTNET_CONNECTION_FAILED", "Testnet credential verification failed.", 422) from None
        if not result.authenticated or result.can_place_orders:
            raise failure("TESTNET_CONNECTION_FAILED", "Unexpected testnet response.", 503)
        # Only encrypted credentials are persisted; 24-hour TTL and a DELETE endpoint.
        encrypted = encryptor.encrypt(
            json.dumps({"key": api_key, "secret": api_secret}).encode("utf-8")
        )
        try:
            await redis_store(request).set(connection_key(user), encrypted, ex=CONNECT_TTL_SECONDS)
        except Exception:
            raise failure("MONITOR_STORE_UNAVAILABLE", "Credential store unavailable.", 503) from None
        return ConnectionResult(authenticated=True, encrypted_server_storage=True,
                                expires_in_seconds=CONNECT_TTL_SECONDS)


@router.delete("/testnet/connect", response_model=ConnectionResult)
async def testnet_disconnect(
    request: Request,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)],
):
    verify_mutation(request, principal)
    with testnet_credential_guard(request, user):
        try:
            await redis_store(request).delete(connection_key(user))
        except Exception:
            raise failure("MONITOR_STORE_UNAVAILABLE", "Credential store unavailable.", 503) from None
        return ConnectionResult(authenticated=False, encrypted_server_storage=False,
                                expires_in_seconds=0)


@router.post("/live/connect", response_model=LiveConnectionResult)
async def live_readonly_connect(
    request: Request,
    credentials: ConnectionRequest,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)],
):
    """Bind a real, read-only, allowlisted Binance key; NO order capability."""
    verify_mutation(request, principal)
    encryptor = live_cipher(request)  # require vault BEFORE any external call
    api_key = credentials.api_key.get_secret_value()
    api_secret = credentials.api_secret.get_secret_value()
    try:
        checked = await probe_live_readonly_account(api_key, api_secret)
    except LiveConnectivityError as exc:
        # Only known, sanitized error codes; no raw HTTP data.
        allowed = {
            "INVALID_LIVE_CREDENTIAL_FORMAT", "INVALID_TIMEOUT", "INVALID_TIMESTAMP",
            "LIVE_NETWORK_UNAVAILABLE", "LIVE_AUTH_REJECTED",
            "LIVE_ACCOUNT_CHECK_FAILED", "LIVE_INVALID_RESPONSE",
            "LIVE_READ_ACCESS_REQUIRED", "LIVE_IP_ALLOWLIST_REQUIRED",
            "LIVE_PRIVILEGED_KEY_REJECTED",
        }
        code = str(exc) if str(exc) in allowed else "LIVE_CONNECTION_FAILED"
        raise failure(code, "Mainnet read-only credential verification failed.", 422) from None
    if (not checked.authenticated or not checked.read_only_permission_verified
            or not checked.ip_restricted or checked.can_place_orders):
        raise failure("LIVE_CONNECTION_FAILED", "Read-only key is not verified.", 422)
    encrypted = encryptor.encrypt(
        json.dumps({"key": api_key, "secret": api_secret}).encode("utf-8")
    )
    try:
        await redis_store(request).set(
            live_connection_key(user), encrypted, ex=LIVE_CONNECT_TTL_SECONDS
        )
    except Exception:
        raise failure("MONITOR_STORE_UNAVAILABLE", "Credential store unavailable.", 503) from None
    return LiveConnectionResult(
        authenticated=True, read_only_permission_verified=True, ip_restricted=True,
        encrypted_server_storage=True, expires_in_seconds=LIVE_CONNECT_TTL_SECONDS
    )


@router.delete("/live/connect", response_model=LiveConnectionResult)
async def live_readonly_disconnect(
    request: Request,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)],
):
    verify_mutation(request, principal)
    try:
        await redis_store(request).delete(live_connection_key(user))
    except Exception:
        raise failure("MONITOR_STORE_UNAVAILABLE", "Credential store unavailable.", 503) from None
    return LiveConnectionResult(
        authenticated=False, read_only_permission_verified=False,
        ip_restricted=False, encrypted_server_storage=False, expires_in_seconds=0
    )


CONFIRMED_MONITOR_START = """
if (redis.call('GET', KEYS[2]) or '') ~= ARGV[1]
   or (redis.call('GET', KEYS[3]) or '') ~= ARGV[2] then return 0 end
redis.call('SET', KEYS[1], ARGV[3], 'EX', ARGV[4])
return 1
"""

MONITOR_REFRESH_SCRIPT = """
if redis.call('GET', KEYS[1]) ~= ARGV[1] then return 0 end
local ttl = redis.call('TTL', KEYS[1])
if ttl <= 0 then return 0 end
redis.call('SET', KEYS[1], ARGV[2], 'EX', ttl, 'XX')
return 1
"""

RELEASE_MONITOR_LOCK = """
if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end
return 0
"""


async def refresh_monitor(redis, key, raw) -> bool:
    """Compare the generation after the market read; stop/apply always wins."""
    record = json.loads(raw)
    if not isinstance(record, dict) or record.get("desired") != "RUNNING":
        return False
    from nex_api.strategy_signals import ALLOWED_SYMBOLS, ALLOWED_INTERVALS
    symbol = record.get("symbol", "BTCUSDT")
    interval = record.get("interval", "5m")
    if symbol not in ALLOWED_SYMBOLS or interval not in ALLOWED_INTERVALS:
        return False
    candles = await fetch_closed_candles(
        market="usdm_futures", symbol=symbol, interval=interval, limit=3
    )
    item = candles.candles[-1]
    record.update(close=str(item.close), closed_ms=item.close_time_ms,
                  checked_ms=int(time.time() * 1000))
    return bool(await redis.eval(MONITOR_REFRESH_SCRIPT, 1, key, raw, json.dumps(record)))


async def monitor_worker(redis) -> None:
    """Bounded market reads only; no order writes or automatic TTL extension."""
    while True:
        try:
            processed = 0
            async for key in redis.scan_iter(match=PREFIX + "*", count=50):
                key = key.decode("ascii") if isinstance(key, bytes) else key
                if key.endswith(":lock"):
                    continue
                if processed >= MAX_MONITORS:
                    break
                processed += 1
                lock = key + ":lock"
                token = secrets.token_hex(16)
                if not await redis.set(lock, token, nx=True, ex=20):
                    continue
                try:
                    raw = await redis.get(key)
                    if raw is not None:
                        await refresh_monitor(redis, key, raw)
                except (MarketDataUnavailable, ValueError, TypeError, KeyError):
                    log.warning("hunter_monitor_market_unavailable")
                finally:
                    await redis.eval(RELEASE_MONITOR_LOCK, 1, lock, token)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.warning("hunter_monitor_store_unavailable")
        await asyncio.sleep(30)
