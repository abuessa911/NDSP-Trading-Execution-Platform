"""Authenticated, isolated virtual-money execution. No broker credentials."""
from __future__ import annotations
import asyncio
import logging
from types import SimpleNamespace
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from nex_api.binance_closed_candles import MarketDataUnavailable, fetch_closed_candles
from nex_api.dependencies import Principal, failure, get_current_principal, get_operator, get_provisioned_user
from nex_api.models import User
from nex_api.paper_broker import PaperBroker, PaperRejected, PROFILE_FIELDS
from nex_api.routes.trading_control import verify_mutation
from nex_api.routes.trading_profile import workspace
from nex_api.strategy_signals import evaluate, StrategyDataError

router = APIRouter(prefix="/api/v1/trading/paper", include_in_schema=False)
log = logging.getLogger("hunter.paper")
Money = Annotated[str, Field(min_length=1, max_length=32)]

class PaperPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    daily_loss_pct: Money
    trade_risk_pct: Money
    max_margin_pct: Money
    stop_distance_pct: Money
    take_profit_distance_pct: Money
    fee_pct: Money
    slippage_pct: Money

class PaperSetup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    initial_equity: Money
    policy: PaperPolicy
    strategy_id: Literal["trend-ladder", "range-fade", "breakout-scout", "mean-return"]

class PaperOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    action: Literal["OPEN", "CLOSE"]
    side: Literal["LONG", "SHORT"]
    quantity: Money | None = None
    position_id: UUID | None = None

def scope(user):
    return f"{user.tenant_id}:{user.id}"

def broker(request):
    value = getattr(request.app.state, "paper_broker", None)
    if not isinstance(value, PaperBroker):
        raise failure("PAPER_SERVICE_DISABLED", "Virtual account service unavailable.", 503)
    return value

def rejected(error):
    return failure(str(error), "Virtual account operation rejected.", 409)

async def selected_profile(request, user):
    selected = await workspace(request, user)
    if not selected.persisted:
        raise failure("PAPER_WORKSPACE_CONFIRM_REQUIRED", "Confirm shared settings first.", 409)
    return {field: getattr(selected, field) for field in PROFILE_FIELDS}

async def market(metadata):
    # An existing virtual position retains its original symbol and timeframe.
    target = metadata["position"] or metadata["profile"]
    return await fetch_closed_candles(market="usdm_futures",
        symbol=target["symbol"], interval=target["interval"], limit=80)

async def tick(request, user):
    engine = broker(request)
    identifier = scope(user)
    metadata = await asyncio.to_thread(engine.metadata, identifier)
    if not metadata["running"] and not metadata["position"]:
        return await asyncio.to_thread(engine.view, identifier)
    batch = await market(metadata)
    try:
        current = await selected_profile(request, user)
    except Exception:
        # Loss of profile/Redis proof cannot create a new automatic entry.
        await asyncio.to_thread(engine.set_running, identifier, False)
        current = None
    signal = None
    if metadata["running"] and current is not None and current == metadata["profile"]:
        signal = evaluate(metadata["strategy_id"], batch)
    return await asyncio.to_thread(engine.cycle, identifier, batch,
                                  current_profile=current, signal=signal,
                                  expected_revision=metadata["configuration_revision"])

@router.get("")
async def get_paper(request: Request,
    user: Annotated[User, Depends(get_provisioned_user)]):
    engine = broker(request)
    try:
        return await tick(request, user)
    except PaperRejected as error:
        if str(error) == "PAPER_ACCOUNT_NOT_CONFIGURED":
            return {"mode": "PAPER", "configured": False, "real_orders_enabled": False,
                    "position": None, "orders": [], "total_orders": 0}
        raise rejected(error) from None
    except (MarketDataUnavailable, StrategyDataError):
        await asyncio.to_thread(engine.set_running, scope(user), False)
        result = await asyncio.to_thread(engine.view, scope(user))
        result.update(quote_available=False, market_error="PAPER_MARKET_UNAVAILABLE")
        return result

@router.put("/account")
async def setup_paper(request: Request, body: PaperSetup,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)]):
    verify_mutation(request, principal)
    selected = await selected_profile(request, user)
    try:
        return await asyncio.to_thread(broker(request).configure, scope(user),
            initial_equity=body.initial_equity, policy=body.policy.model_dump(),
            profile=selected, strategy_id=body.strategy_id)
    except PaperRejected as error:
        raise rejected(error) from None

@router.post("/orders")
async def submit_paper(request: Request, body: PaperOrder,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)]):
    verify_mutation(request, principal)
    engine = broker(request)
    try:
        metadata = await asyncio.to_thread(engine.metadata, scope(user))
        # New entries need current server settings. Exits need the existing
        # position market even if settings/Redis have changed.
        selected = await selected_profile(request, user) if body.action == "OPEN" else metadata["profile"]
        if body.action == "OPEN" and body.quantity is None:
            raise PaperRejected("PAPER_QUANTITY_REQUIRED")
        if body.action == "CLOSE" and body.position_id is None:
            raise PaperRejected("PAPER_POSITION_CONFIRM_REQUIRED")
        batch = await market(metadata)
        return await asyncio.to_thread(engine.submit, scope(user), batch,
            action=body.action, side=body.side, quantity=body.quantity,
            request_id=str(body.request_id), current_profile=selected,
            expected_revision=metadata["configuration_revision"],
            expected_position_id=str(body.position_id) if body.position_id is not None else None)
    except PaperRejected as error:
        raise rejected(error) from None
    except MarketDataUnavailable:
        raise failure("PAPER_MARKET_UNAVAILABLE", "Verified candle feed unavailable.", 503) from None

@router.post("/start")
async def start_paper(request: Request,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)]):
    verify_mutation(request, principal)
    try:
        engine = broker(request)
        metadata = await asyncio.to_thread(engine.metadata, scope(user))
        selected = await selected_profile(request, user)
        batch = await market(metadata)
        evaluate(metadata["strategy_id"], batch)
        # Advance daily valuation and protective exits before authorizing virtual entries.
        await asyncio.to_thread(engine.cycle, scope(user), batch, current_profile=selected,
                                expected_revision=metadata["configuration_revision"])
        return await asyncio.to_thread(engine.set_running, scope(user), True, selected,
                                       expected_revision=metadata["configuration_revision"])
    except PaperRejected as error:
        raise rejected(error) from None
    except (MarketDataUnavailable, StrategyDataError):
        raise failure("PAPER_MARKET_UNAVAILABLE", "Verified candle feed unavailable.", 503) from None

@router.post("/stop")
async def stop_paper(request: Request,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)]):
    verify_mutation(request, principal)
    try:
        return await asyncio.to_thread(broker(request).set_running, scope(user), False)
    except PaperRejected as error:
        raise rejected(error) from None

async def paper_worker(app):
    """Only virtual accounts explicitly started by an operator can open positions."""
    while True:
        try:
            scopes = await asyncio.to_thread(app.state.paper_broker.active_scopes)
            for identifier in scopes:
                try:
                    tenant, subject = identifier.split(":")
                    user = SimpleNamespace(tenant_id=UUID(tenant), id=UUID(subject))
                    await tick(SimpleNamespace(app=app), user)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    log.warning("paper_cycle_unavailable")
                    try:
                        await asyncio.to_thread(app.state.paper_broker.set_running, identifier, False)
                    except Exception:
                        log.warning("paper_stop_unavailable")
        except asyncio.CancelledError:
            raise
        except Exception:
            log.warning("paper_worker_unavailable")
        await asyncio.sleep(30)
