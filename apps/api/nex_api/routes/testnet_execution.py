"""Session-bound, explicitly confirmed DEMO execution; no Mainnet route."""
from __future__ import annotations

import asyncio
import json
from typing import Annotated, Literal
from uuid import UUID

from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from nex_api.dependencies import Principal, failure, get_current_principal, get_operator, get_provisioned_user
from nex_api.models import User
from nex_api import hunter_live_executor as legacy
from nex_api.testnet_execution import TestnetExecution, PRESET
from nex_api.routes.trading_control import cipher, connection_key, redis_store, verify_mutation

router = APIRouter(prefix="/api/v1/trading/testnet", include_in_schema=False)
Money = Annotated[str, Field(min_length=1, max_length=32)]


class Setup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: Literal["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT"]
    margin_mode: Literal["CROSS", "ISOLATED"]
    daily_loss_pct: Money
    trade_risk_pct: Money
    max_exposure_pct: Money
    stop_pct: Money
    confirmation: Literal["BINANCE_DEMO_ONLY"]


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    revision: UUID
    action: Literal["preflight", "dry-run", "entry", "inspect", "reconcile", "exit", "cleanup", "recover"]
    position_id: str | None = Field(default=None, max_length=32)
    confirmation: Literal["BINANCE_DEMO_ONLY"]


class Automation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: StrictBool
    revision: UUID
    confirmation: Literal["BINANCE_DEMO_ONLY"]


def scope(user):
    return f"{user.tenant_id}:{user.id}"


def service(request):
    value = getattr(request.app.state, "testnet_execution", None)
    if not isinstance(value, TestnetExecution):
        raise failure("TESTNET_EXECUTION_DISABLED", "Demo execution service unavailable.", 503)
    return value


def rejected(error):
    return failure(str(error), "Demo operation rejected.", 409)


async def threaded(function, *args, **kwargs):
    # A disconnected client must not release the exchange lock while the
    # synchronous signer/HTTP worker is still staging or submitting an order.
    task = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
    cancelled = False
    while True:
        try:
            result = await asyncio.shield(task)
            break
        except asyncio.CancelledError:
            cancelled = True
            if task.done():
                task.result()
                break
    if cancelled:
        raise asyncio.CancelledError
    return result


async def credentials(request, user):
    try:
        encrypted = await redis_store(request).get(connection_key(user))
        if encrypted is None:
            raise failure("SEPARATE_BINANCE_DEMO_CREDENTIALS_REQUIRED",
                          "Save verified Binance Demo credentials first.", 409)
        decoded = json.loads(cipher(request).decrypt(encrypted).decode("utf-8"))
        if set(decoded) != {"key", "secret"}:
            raise ValueError
        key, secret = decoded["key"], decoded["secret"]
        if (not isinstance(key, str) or not isinstance(secret, str) or
                not key or not secret or "\n" in key or "\n" in secret):
            raise ValueError
        return key, secret
    except (InvalidToken, ValueError, TypeError, UnicodeError):
        raise failure("TESTNET_CREDENTIALS_UNAVAILABLE", "Demo credentials unavailable.", 503) from None


@router.get("")
async def status(request: Request, user: Annotated[User, Depends(get_provisioned_user)]):
    try:
        with service(request).session(scope(user)) as account:
            value = await threaded(account.view)
            value["credentials_saved"] = bool(await redis_store(request).exists(connection_key(user)))
            return value
    except legacy.Halt as error:
        raise rejected(error) from None


@router.put("/configuration")
async def configure(request: Request, body: Setup,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)]):
    verify_mutation(request, principal)
    config = dict(PRESET, **body.model_dump(exclude={"confirmation"}))
    try:
        with service(request).session(scope(user)) as account:
            return await threaded(account.configure, config)
    except legacy.Halt as error:
        raise rejected(error) from None


@router.post("/actions")
async def action(request: Request, body: Action,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)]):
    verify_mutation(request, principal)
    try:
        with service(request).session(scope(user)) as account:
            if account.automation()["state"] in {"RUNNING", "STOPPING"} and body.action not in {"inspect", "preflight"}:
                raise legacy.Halt("TESTNET_STOP_AUTOMATION_BEFORE_MANUAL_ACTION")
            key, secret = await credentials(request, user)
            return await threaded(account.operate, body.action, str(body.request_id),
                str(body.revision), key, secret, position_id=body.position_id)
    except legacy.Halt as error:
        raise rejected(error) from None

@router.put("/automation")
async def automation(request: Request, body: Automation,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)]):
    verify_mutation(request, principal)
    try:
        with service(request).session(scope(user)) as account:
            if body.enabled:
                key, secret = await credentials(request, user)
                ttl = await redis_store(request).ttl(connection_key(user))
                return await threaded(account.set_automation, True, str(body.revision), key, secret,
                    credentials_ttl=ttl, authority={"issuer": user.issuer, "subject": user.subject})
            return await threaded(account.set_automation, False, str(body.revision))
    except legacy.Halt as error:
        raise rejected(error) from None
