"""Authenticated read-only USD-M account-equity loss budget.

This is NOT a live execution gate. No order writes; all figures are for
operator risk review. A future executor must enforce its OWN fail-closed,
durable risk ledger before authorizing a write.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from hashlib import sha256
import json
import time
from typing import Annotated, Literal

import httpx
from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from nex_api.binance_live_readonly_connector import (
    FUTURES_ORIGIN, LiveConnectivityError, _get_json, _signed_url,
)
from nex_api.dependencies import (
    Principal, failure, get_current_principal, get_operator, get_provisioned_user,
)
from nex_api.models import User
from nex_api.risk_guard import RiskInvalid, amount, daily_loss, percentage
from nex_api.routes.trading_control import (
    live_cipher, live_connection_key, redis_store, verify_mutation,
)

router = APIRouter(prefix="/api/v1/trading/risk", tags=["hunter account risk"],
                   include_in_schema=False)
POLICY_PREFIX = "hunter:risk:limit:v1:"
BASELINE_PREFIX = "hunter:risk:baseline:v1:"
HIT_PREFIX = "hunter:risk:hit:v1:"
TWO_DAYS_SECONDS = 172800

# Never increase a daily limit after the first same-day policy or equity baseline.
# A higher user-chosen percentage is permitted at the next UTC day only BEFORE
# that day's baseline is recorded. Redis changes are atomic.
SAVE_POLICY_SCRIPT = """
local previous = redis.call('GET', KEYS[1])
if previous then
    local old = cjson.decode(previous)
    if (old.utc_day == ARGV[2] or redis.call('EXISTS', KEYS[2]) == 1)
       and tonumber(ARGV[1]) > tonumber(old.daily_loss_pct) then
        return 0
    end
end
redis.call('SET', KEYS[1], cjson.encode({daily_loss_pct=ARGV[1], utc_day=ARGV[2]}))
return 1
"""


class RiskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    daily_loss_pct: str = Field(min_length=1, max_length=16)


class RiskView(BaseModel):
    daily_loss_pct: str | None
    configured: bool
    account_connected: bool
    state: Literal[
        "NOT_CONFIGURED", "READONLY_ACCOUNT_MISSING", "ACCOUNT_CHANGED_REVIEW_REQUIRED",
        "ACCOUNT_UNAVAILABLE", "MONITORING", "DAILY_LOSS_LIMIT_REACHED",
    ]
    opening_equity: str | None = None
    current_equity: str | None = None
    daily_loss_amount: str | None = None
    loss_budget: str | None = None
    loss_pct_of_opening_equity: str | None = None
    new_entries_blocked: bool = True
    # Never imply that viewing this screen authorizes or blocks actual orders.
    execution_enabled: Literal[False] = False
    order_gate_attached: Literal[False] = False


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def scope(user: User) -> str:
    return f"{user.tenant_id}:{user.id}"


def policy_key(user: User) -> str:
    return POLICY_PREFIX + scope(user)


def baseline_key(user: User, day: str) -> str:
    return f"{BASELINE_PREFIX}{scope(user)}:{day}"


def hit_key(user: User, day: str) -> str:
    return f"{HIT_PREFIX}{scope(user)}:{day}"


def decode(raw):
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw) if raw else None


async def read_account_equity(
    request: Request, user: User
) -> tuple[str, str] | None:
    """Read account equity only; never authorize order submission."""
    store = redis_store(request)
    encrypted = await store.get(live_connection_key(user))
    if not encrypted:
        return None

    try:
        credentials = json.loads(live_cipher(request).decrypt(encrypted))
        key = credentials["key"]
        if not isinstance(key, str) or not key:
            raise ValueError("INVALID_KEY")
    except (InvalidToken, KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise failure(
            "RISK_CREDENTIAL_INVALID",
            "Stored credential invalid.",
            503,
        ) from None

    if credentials.get("scheme") == "ed25519":
        try:
            from nex_api.binance_ed25519_readonly import (
                BinanceEd25519ReadOnly, BinanceReadError,
            )
            from nex_api.routes.ed25519_connection import credential_path

            def read_futures():
                connector = BinanceEd25519ReadOnly(
                    key, credential_path()
                )
                return connector.read("futures")

            payload = await asyncio.to_thread(read_futures)
        except (BinanceReadError, OSError, RuntimeError, ValueError):
            raise failure(
                "RISK_EQUITY_UNAVAILABLE",
                "Signed Ed25519 equity unavailable.",
                503,
            ) from None

    elif credentials.get("scheme") is None:
        try:
            secret = credentials["secret"]
            if not isinstance(secret, str) or not secret:
                raise ValueError("INVALID_SECRET")
        except (KeyError, TypeError, ValueError):
            raise failure(
                "RISK_CREDENTIAL_INVALID",
                "Stored credential invalid.",
                503,
            ) from None

        url = _signed_url(
            FUTURES_ORIGIN,
            "/fapi/v3/account",
            secret,
            int(time.time() * 1000),
        )
        async with httpx.AsyncClient(
            timeout=8.0,
            trust_env=False,
            follow_redirects=False,
        ) as client:
            try:
                payload = await _get_json(client, url, key)
            except LiveConnectivityError:
                raise failure(
                    "RISK_EQUITY_UNAVAILABLE",
                    "Signed read-only equity unavailable.",
                    503,
                ) from None
    else:
        raise failure(
            "RISK_CREDENTIAL_INVALID",
            "Unknown credential scheme.",
            503,
        ) from None

    try:
        equity = str(amount(payload["totalMarginBalance"], positive=True))
    except (KeyError, TypeError, RiskInvalid):
        raise failure(
            "RISK_EQUITY_UNAVAILABLE",
            "Invalid exchange equity.",
            503,
        ) from None

    return equity, sha256(key.encode("utf-8")).hexdigest()


async def get_risk_view(request: Request, user: User) -> RiskView:
    store = redis_store(request)
    utc_day = today()
    try:
        policy = decode(await store.get(policy_key(user)))
        if policy is None:
            return RiskView(daily_loss_pct=None, configured=False, account_connected=False,
                            state="NOT_CONFIGURED")
        percent = str(percentage(policy["daily_loss_pct"]))
        connected = bool(await store.exists(live_connection_key(user)))
        if not connected:
            return RiskView(daily_loss_pct=percent, configured=True,
                            account_connected=False, state="READONLY_ACCOUNT_MISSING")
    except (RiskInvalid, ValueError, TypeError, KeyError):
        raise failure("RISK_POLICY_INVALID", "Invalid server policy.", 503) from None
    except Exception:
        raise failure("RISK_STORE_UNAVAILABLE", "Risk store unavailable.", 503) from None

    equity_account = await read_account_equity(request, user)
    if equity_account is None:
        return RiskView(daily_loss_pct=percent, configured=True, account_connected=False,
                        state="READONLY_ACCOUNT_MISSING")
    equity, fingerprint = equity_account
    b_key = baseline_key(user, utc_day)
    try:
        record = json.dumps({"equity": equity, "fingerprint": fingerprint})
        await store.set(b_key, record, nx=True, ex=TWO_DAYS_SECONDS)
        baseline = decode(await store.get(b_key))
        if not isinstance(baseline, dict) or not baseline.get("equity") or not baseline.get("fingerprint"):
            raise ValueError("INVALID_BASELINE")
        if baseline["fingerprint"] != fingerprint:
            return RiskView(daily_loss_pct=percent, configured=True,
                            account_connected=True, state="ACCOUNT_CHANGED_REVIEW_REQUIRED")
        evaluation = daily_loss(baseline["equity"], equity, percent)
        if evaluation["new_entries_blocked"]:
            await store.set(hit_key(user, utc_day), "1", nx=True, ex=TWO_DAYS_SECONDS)
        hit = bool(await store.exists(hit_key(user, utc_day)))
        return RiskView(
            daily_loss_pct=percent, configured=True, account_connected=True,
            state="DAILY_LOSS_LIMIT_REACHED" if hit else "MONITORING",
            **{k: v for k, v in evaluation.items() if k != "new_entries_blocked"},
            new_entries_blocked=hit,
        )
    except (RiskInvalid, ValueError, TypeError, KeyError):
        raise failure("RISK_BASELINE_INVALID", "Daily equity baseline unavailable.", 503) from None
    except Exception:
        raise failure("RISK_STORE_UNAVAILABLE", "Risk store unavailable.", 503) from None


@router.get("", response_model=RiskView)
async def view(
    request: Request,
    user: Annotated[User, Depends(get_provisioned_user)],
) -> RiskView:
    return await get_risk_view(request, user)


@router.put("", response_model=RiskView)
async def set_daily_limit(
    request: Request,
    body: RiskUpdate,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> RiskView:
    verify_mutation(request, principal)
    try:
        daily_pct = str(percentage(body.daily_loss_pct))
    except RiskInvalid:
        raise failure("RISK_PERCENT_INVALID", "Daily loss percentage must be positive and <=100.", 422) from None
    store = redis_store(request)
    try:
        saved = await store.eval(
            SAVE_POLICY_SCRIPT, 2, policy_key(user), baseline_key(user, today()),
            daily_pct, today(),
        )
    except Exception:
        raise failure("RISK_STORE_UNAVAILABLE", "Cannot persist risk policy.", 503) from None
    if saved != 1:
        raise failure("RISK_LIMIT_INCREASE_BLOCKED",
                      "Cannot increase the daily risk budget during the active UTC risk day.", 409)
    return await get_risk_view(request, user)
