"""Isolated Hunter decision-style preference, NOT execution or NDSP authority.

The NDSP-NEX-1.0 signed decision contract remains unchanged. A selected style
never permits orders; trading stays fail-closed and NDSP integration unbound.
"""
import asyncio
import hmac
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from nex_api.binance_closed_candles import MarketDataUnavailable, fetch_closed_candles
from nex_api.dependencies import Principal, failure, get_current_principal, get_provisioned_user
from nex_api.models import User
from nex_api.routes.auth import same_origin


# A private bot preference surface, outside the frozen M1 public OpenAPI.
router = APIRouter(prefix="/api/v1/trading/profile", tags=["hunter preferences"], include_in_schema=False)
DecisionProfile = Literal["INVESTMENT", "SPECULATIVE"]


class ProfileView(BaseModel):
    mode: DecisionProfile
    persisted: bool
    execution_authorized: Literal[False] = False
    ndsp_contract_bound: Literal[False] = False


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: DecisionProfile


def key(user: User) -> str:
    # Authenticated DB-owned identifiers only; never a caller-supplied tenant.
    return f"hunter:m1:decision-style:{user.tenant_id}:{user.id}"


def storage(request: Request):
    store = getattr(request.app.state, "browser_sessions", None)
    redis = getattr(store, "redis", None)
    if redis is None:
        redis = getattr(request.app.state, "redis", None)
    if redis is None:
        raise failure("SYSTEM_DEPENDENCY_UNHEALTHY", "Preference store unavailable.", 503)
    return redis


async def stop_paper_entries(request: Request, user: User) -> None:
    # A completed workspace confirmation also stops this owner's automatic
    # virtual entries. SQLite serializes a concurrent cycle before this ack.
    engine = getattr(request.app.state, "paper_broker", None)
    if engine is not None:
        from nex_api.paper_broker import PaperRejected
        try:
            await asyncio.to_thread(engine.set_running, f"{user.tenant_id}:{user.id}", False)
        except PaperRejected as error:
            if str(error) != "PAPER_ACCOUNT_NOT_CONFIGURED":
                raise failure("WORKSPACE_UNAVAILABLE", "Workspace was not confirmed.", 503) from None
        except Exception:
            raise failure("WORKSPACE_UNAVAILABLE", "Workspace was not confirmed.", 503) from None


@router.get("", response_model=ProfileView, operation_id="getHunterDecisionProfile")
async def get_profile(
    request: Request,
    user: Annotated[User, Depends(get_provisioned_user)],
) -> ProfileView:
    try:
        raw = await storage(request).get(key(user))
    except Exception:
        raise failure("SYSTEM_DEPENDENCY_UNHEALTHY", "Preference store unavailable.", 503)
    selected = raw.decode("ascii") if isinstance(raw, bytes) else raw
    if selected is None:
        return ProfileView(mode="SPECULATIVE", persisted=False)
    if selected not in ("SPECULATIVE", "INVESTMENT"):
        raise failure("PROFILE_NOT_VALID", "Stored preference rejected.", 503)
    return ProfileView(mode=selected, persisted=True)


@router.put("", response_model=ProfileView, operation_id="putHunterDecisionProfile")
async def put_profile(
    request: Request,
    update: ProfileUpdate,
    user: Annotated[User, Depends(get_provisioned_user)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ProfileView:
    # Server-side CSRF and same-origin validation, never read from browser localStorage.
    same_origin(request)
    proof = (principal.session_data or {}).get("csrf")
    candidate = request.headers.get("x-nex-csrf", "")
    if not isinstance(proof, str) or not proof or not hmac.compare_digest(candidate, proof):
        raise failure("CSRF_NOT_VALID", "Valid server-issued CSRF proof is required.")
    try:
        await storage(request).set(key(user), update.mode)
    except Exception:
        raise failure("SYSTEM_DEPENDENCY_UNHEALTHY", "Preference store unavailable.", 503)
    await stop_paper_entries(request, user)
    return ProfileView(mode=update.mode, persisted=True)


# Shared, authenticated operator workspace. Selecting execution preferences never
# submits an exchange order or changes the runtime's execution permissions.

WorkspaceSymbol = Literal["BTCUSDT", "ETHUSDT", "SOLUSDT", "LINKUSDT",
                          "XRPUSDT", "DOGEUSDT", "BNBUSDT"]
WorkspaceInterval = Literal["5m", "15m", "1h", "4h", "1d"]


class WorkspaceSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: DecisionProfile = "SPECULATIVE"
    symbol: WorkspaceSymbol = "BTCUSDT"
    interval: WorkspaceInterval = "5m"
    execution_method: Literal["MANUAL", "AUTOMATIC"] = "MANUAL"
    leverage: int = Field(default=1, strict=True, ge=1, le=125)
    margin_mode: Literal["ISOLATED", "CROSS"] = "ISOLATED"


class WorkspaceView(WorkspaceSettings):
    persisted: bool
    execution_authorized: Literal[False] = False
    ndsp_contract_bound: Literal[False] = False


def workspace_key(user: User) -> str:
    return f"hunter:workspace:v1:{user.tenant_id}:{user.id}"


async def workspace_snapshot(request: Request, user: User):
    try:
        # Both keys are read in one Redis operation, matching the atomic write.
        style, raw = await storage(request).mget(key(user), workspace_key(user))
        style = style.decode("ascii") if isinstance(style, bytes) else style
        values = WorkspaceSettings.model_validate_json(raw) if raw else WorkspaceSettings()
        if style is not None:
            if style not in ("INVESTMENT", "SPECULATIVE"):
                raise ValueError("INVALID_STYLE")
            values.mode = style
        return WorkspaceView(**values.model_dump(), persisted=raw is not None), style or "", raw or ""
    except (ValueError, TypeError, UnicodeError, ValidationError):
        raise failure("WORKSPACE_NOT_VALID", "Stored workspace rejected.", 503) from None
    except Exception:
        raise failure("WORKSPACE_UNAVAILABLE", "Workspace store unavailable.", 503) from None


async def workspace(request: Request, user: User) -> WorkspaceView:
    selected, _, _ = await workspace_snapshot(request, user)
    return selected


@router.get("/workspace", response_model=WorkspaceView)
async def get_workspace(
    request: Request,
    user: Annotated[User, Depends(get_provisioned_user)],
) -> WorkspaceView:
    return await workspace(request, user)


@router.put("/workspace", response_model=WorkspaceView)
async def put_workspace(
    request: Request,
    update: WorkspaceSettings,
    user: Annotated[User, Depends(get_provisioned_user)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> WorkspaceView:
    same_origin(request)
    proof = (principal.session_data or {}).get("csrf")
    candidate = request.headers.get("x-nex-csrf", "")
    if not isinstance(proof, str) or not proof or not hmac.compare_digest(candidate, proof):
        raise failure("CSRF_NOT_VALID", "Valid server-issued CSRF proof is required.")
    # A saved selection must not relabel an older running scanner's output.
    # Stop only this account's monitor/scanners atomically with its settings.
    from nex_api.routes.trading_control import monitor_key
    from nex_api.routes.strategy_scanner import active_key, result_key
    from nex_api.strategy_signals import STRATEGIES
    obsolete = [monitor_key(user)]
    for strategy in STRATEGIES:
        active = active_key(user, strategy.id)
        obsolete.extend([active, result_key(active)])
    try:
        async with storage(request).pipeline(transaction=True) as transaction:
            transaction.set(key(user), update.mode)
            transaction.set(workspace_key(user), update.model_dump_json())
            transaction.delete(*obsolete)
            await transaction.execute()
    except Exception:
        raise failure("WORKSPACE_UNAVAILABLE", "Workspace was not confirmed.", 503) from None
    await stop_paper_entries(request, user)
    return WorkspaceView(**update.model_dump(), persisted=True)


@router.get("/workspace/candles")
async def workspace_candles(
    request: Request,
    user: Annotated[User, Depends(get_provisioned_user)],
):
    selected = await workspace(request, user)
    try:
        batch = await fetch_closed_candles(
            market="usdm_futures", symbol=selected.symbol, interval=selected.interval, limit=5
        )
    except MarketDataUnavailable:
        raise failure("MARKET_SOURCE_UNAVAILABLE", "Verified closed candles unavailable.", 503) from None
    return {
        "status": "READ_ONLY_OK", "contract": "HUNTER_CLOSED_CANDLES_PREVIEW_V1",
        "source": batch.source, "market": batch.market, "symbol": batch.symbol,
        "interval": batch.interval, "serverTimeMs": batch.server_time_ms,
        "execution_authorized": False, "orders_sent": 0,
        "candles": [
            {"openTimeMs": row.open_time_ms, "closeTimeMs": row.close_time_ms,
             "open": str(row.open), "high": str(row.high), "low": str(row.low),
             "close": str(row.close), "volume": str(row.volume)}
            for row in batch.candles
        ],
    }
