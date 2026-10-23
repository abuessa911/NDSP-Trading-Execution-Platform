"""Owner-controlled application automation switch; never enables Mainnet order execution."""
from __future__ import annotations

import asyncio
import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from nex_api import hunter_live_executor as legacy
from nex_api.dependencies import Principal, failure, get_administrator, get_current_principal, get_operator, get_provisioned_user
from nex_api.models import User
from nex_api.paper_broker import PaperRejected
from nex_api.risk_guard import RiskInvalid, amount, percentage
from nex_api.routes.trading_control import monitor_key, redis_store, state, verify_mutation
from nex_api.routes.strategy_scanner import ACTIVE_PREFIX, RESULT_PREFIX, active_key, start_strategy, StrategyStart
from nex_api.strategy_signals import BY_ID

router = APIRouter(prefix="/api/v1/trading/bot", include_in_schema=False)
POWER_PREFIX = "hunter:bot:power:v1:"
SELECTED_PREFIX = "hunter:bot:selected:v1:"
PREFERENCES_PREFIX = "hunter:bot:live-preferences:v1:"


class TradingPreferenceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    venue: Literal["BINANCE_USDM_FUTURES"]
    capital_limit_usdt: str = Field(min_length=1, max_length=24)
    trade_risk_pct: str = Field(min_length=1, max_length=16)
    daily_loss_pct: str = Field(min_length=1, max_length=16)


SAVE_TRADING_PREFERENCES = """
local previous = redis.call('GET', KEYS[1])
if previous then
    local old = cjson.decode(previous)
    if (old.utc_day == ARGV[2] or redis.call('EXISTS', KEYS[2]) == 1)
       and tonumber(ARGV[1]) > tonumber(old.daily_loss_pct) then
        return 0
    end
end
redis.call('SET', KEYS[1], cjson.encode({daily_loss_pct=ARGV[1], utc_day=ARGV[2]}))
redis.call('SET', KEYS[3], ARGV[3])
return 1
"""


def account_scope(user: User) -> str:
    return f"{user.tenant_id}:{user.id}"


def power_key(user: User) -> str:
    return POWER_PREFIX + account_scope(user)


def selected_key(user: User) -> str:
    return SELECTED_PREFIX + account_scope(user)


def preferences_key(user: User) -> str:
    return PREFERENCES_PREFIX + account_scope(user)


async def current(request: Request, user: User) -> dict:
    """Report the actual server components; never infer state from a browser toggle."""
    scope = account_scope(user)
    store = redis_store(request)
    scanners = 0
    async for entry in store.scan_iter(match=f"{ACTIVE_PREFIX}{scope}:*", count=16):
        key = entry.decode("utf-8") if isinstance(entry, bytes) else entry
        if not key.endswith(":worker-lock"):
            scanners += 1
    paper_running = False
    issues: list[str] = []
    broker = getattr(request.app.state, "paper_broker", None)
    if broker is not None:
        try:
            details = await asyncio.to_thread(broker.metadata, scope)
            paper_running = details["running"] is True
        except PaperRejected as exc:
            if str(exc) != "PAPER_ACCOUNT_NOT_CONFIGURED":
                issues.append("PAPER_STATUS_UNAVAILABLE")
        except Exception:
            issues.append("PAPER_STATUS_UNAVAILABLE")
    demo_state = "UNAVAILABLE"
    demo_pending = False
    demo = getattr(request.app.state, "testnet_execution", None)
    if demo is not None:
        def read_demo():
            with demo.session(scope) as account:
                status = account.automation()["state"]
                positions = account.state()
                return status, bool(positions.get("pending_order") or positions.get("active_position"))
        try:
            demo_state, demo_pending = await asyncio.to_thread(read_demo)
        except Exception:
            # Testnet uses a nonblocking process-wide lock. A concurrent runner
            # must not make the independent bot control/status disappear.
            demo_state = "UNVERIFIED"
            issues.append("TESTNET_STATUS_UNAVAILABLE")
    monitor = await state(request, user)
    powered_raw, selected_raw = await asyncio.gather(
        store.get(power_key(user)), store.get(selected_key(user)))
    powered = powered_raw in (b"on", "on")
    selected = selected_raw.decode("utf-8") if isinstance(selected_raw, bytes) else selected_raw
    if selected not in BY_ID:
        selected = None
    scanner_ready = bool(selected and await store.exists(active_key(user, selected)))
    active = powered or monitor.state != "STOPPED" or scanners > 0 or paper_running or demo_state in {"RUNNING", "STOPPING"}
    stopping = demo_state == "STOPPING"
    return {
        "status": "STOPPING" if stopping else "RUNNING" if active else "DEGRADED" if issues else "STOPPED",
        "issues": issues,
        "powered": powered,
        "waiting_for_strategy": powered and not scanner_ready,
        "selected_strategy_id": selected,
        "monitor": monitor.state,
        "scanners": scanners,
        "paper_running": paper_running,
        "testnet_automation": demo_state,
        "testnet_position_requires_review": demo_pending,
        "live_orders_enabled": False,
        "private_ndsp_strategies_connected": False,
    }


@router.get("")
async def get_bot(request: Request, user: Annotated[User, Depends(get_provisioned_user)]):
    return await current(request, user)


async def _begin_selected_strategy(strategy_id: str, request: Request,
    user: User, principal: Principal) -> None:
    """Start only a closed-candle research scanner for the selected workspace."""
    from nex_api.routes.trading_profile import workspace_snapshot
    selected, _, _ = await workspace_snapshot(request, user)
    await start_strategy(strategy_id, StrategyStart(symbol=selected.symbol,
        interval=selected.interval, workspace_bound=True), request, user, principal)


@router.post("/start")
async def start_bot(request: Request,
    user: Annotated[User, Depends(get_administrator)],
    principal: Annotated[Principal, Depends(get_current_principal)]):
    """Start the previously selected read-only strategy, or wait for selection."""
    verify_mutation(request, principal)
    store = redis_store(request)
    if not request.app.state.settings.hunter_market_monitor_enabled:
        raise failure("STRATEGY_WORKER_DISABLED", "Research scanner unavailable.", 503)
    if await store.exists(power_key(user)):
        return await current(request, user)
    # The owner's explicit selection survives power toggles; the switch itself
    # does not create a new strategy choice or permit order execution.
    async for entry in store.scan_iter(match=f"{ACTIVE_PREFIX}{account_scope(user)}:*", count=16):
        key = entry.decode("utf-8") if isinstance(entry, bytes) else entry
        await store.delete(key, RESULT_PREFIX + key.removeprefix(ACTIVE_PREFIX))
    raw = await store.get(selected_key(user))
    chosen = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    if chosen in BY_ID:
        await _begin_selected_strategy(chosen, request, user, principal)
    try:
        await store.set(power_key(user), "on", ex=86400)
    except Exception:
        if chosen in BY_ID:
            key = active_key(user, chosen)
            await store.delete(key, RESULT_PREFIX + key.removeprefix(ACTIVE_PREFIX))
        raise failure("BOT_POWER_STORE_UNAVAILABLE", "Bot could not be started.", 503) from None
    return await current(request, user)


@router.post("/strategy/{strategy_id}/activate")
async def activate_strategy(strategy_id: str, request: Request,
    user: Annotated[User, Depends(get_administrator)],
    principal: Annotated[Principal, Depends(get_current_principal)]):
    """Compatibility endpoint: activate an owner's strategy on an already powered bot."""
    verify_mutation(request, principal)
    definition = BY_ID.get(strategy_id)
    if definition is None:
        raise failure("STRATEGY_NOT_FOUND", "Choose a listed strategy.", 404)
    store = redis_store(request)
    if not await store.exists(power_key(user)):
        raise failure("BOT_NOT_RUNNING", "Start bot before selecting a strategy.", 409)
    # Never submit broker orders. Respect the authoritative shared workspace.
    await _begin_selected_strategy(strategy_id, request, user, principal)
    try:
        for other in BY_ID:
            if other != strategy_id:
                key = active_key(user, other)
                await store.delete(key, RESULT_PREFIX + key.removeprefix(ACTIVE_PREFIX))
        await store.set(selected_key(user), strategy_id)
    except Exception:
        key = active_key(user, strategy_id)
        await store.delete(key, RESULT_PREFIX + key.removeprefix(ACTIVE_PREFIX))
        raise failure("STRATEGY_ACTIVATION_INCOMPLETE", "Strategy activation could not be confirmed.", 503) from None
    return await current(request, user)


@router.get("/preferences")
async def trading_preferences(request: Request,
    user: Annotated[User, Depends(get_provisioned_user)]):
    """Show server-stored choices; never imply financial execution is released."""
    from nex_api.routes.risk_equity import decode, policy_key
    from nex_api.routes.trading_profile import workspace_snapshot
    store = redis_store(request)
    workspace, _, _ = await workspace_snapshot(request, user)
    try:
        raw_plan, raw_risk, raw_selected = await asyncio.gather(
            store.get(preferences_key(user)), store.get(policy_key(user)),
            store.get(selected_key(user)))
        plan, risk = decode(raw_plan), decode(raw_risk)
        if plan is not None and (not isinstance(plan, dict)
                or plan.get("venue") != "BINANCE_USDM_FUTURES"):
            raise ValueError("INVALID_PLAN")
        daily = str(percentage(risk["daily_loss_pct"])) if risk else None
        capital = str(amount(plan["capital_limit_usdt"], positive=True)) if plan else None
        per_trade = str(percentage(plan["trade_risk_pct"])) if plan else None
        if plan and (amount(capital) > 1_000_000_000
                     or not daily or percentage(per_trade) > percentage(daily)):
            configured = False
        else:
            configured = bool(plan and daily)
        chosen = raw_selected.decode("utf-8") if isinstance(raw_selected, bytes) else raw_selected
    except (ValueError, TypeError, KeyError, RiskInvalid, json.JSONDecodeError):
        raise failure("TRADING_PREFERENCES_INVALID", "Stored preferences invalid.", 503) from None
    except Exception:
        raise failure("TRADING_PREFERENCES_UNAVAILABLE", "Preferences could not be read.", 503) from None
    return {
        "venue": "BINANCE_USDM_FUTURES",
        "capital_limit_usdt": capital,
        "trade_risk_pct": per_trade,
        "daily_loss_pct": daily,
        "leverage": workspace.leverage,
        "symbol": workspace.symbol,
        "interval": workspace.interval,
        "selected_strategy_id": chosen if chosen in BY_ID else None,
        "configured": configured,
        "live_orders_enabled": False,
        "execution_ready": False,
    }


@router.put("/preferences")
async def save_trading_preferences(body: TradingPreferenceUpdate, request: Request,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)]):
    """Persist owner's capital/risk preferences without enabling an exchange write."""
    from nex_api.routes.risk_equity import policy_key, baseline_key, today
    verify_mutation(request, principal)
    try:
        capital = amount(body.capital_limit_usdt, positive=True)
        per_trade = percentage(body.trade_risk_pct)
        daily = percentage(body.daily_loss_pct)
        if (capital > 1_000_000_000 or capital.as_tuple().exponent < -2
                or per_trade > daily):
            raise RiskInvalid("INVALID_RISK_POLICY")
    except RiskInvalid:
        raise failure("TRADING_PREFERENCES_INVALID",
                      "Capital and percentages must be positive; trade risk must not exceed daily loss.", 422) from None
    store = redis_store(request)
    payload = json.dumps({
        "venue": body.venue, "capital_limit_usdt": str(capital),
        "trade_risk_pct": str(per_trade),
    }, separators=(",", ":"))
    utc_day = today()
    try:
        saved = await store.eval(
            SAVE_TRADING_PREFERENCES, 3, policy_key(user),
            baseline_key(user, utc_day), preferences_key(user),
            str(daily), utc_day, payload)
    except Exception:
        raise failure("TRADING_PREFERENCES_UNAVAILABLE",
                      "Preferences were not saved.", 503) from None
    if saved != 1:
        raise failure("RISK_LIMIT_INCREASE_BLOCKED",
                      "Cannot increase the daily limit during the active UTC risk day.", 409)
    return await trading_preferences(request, user)


@router.post("/strategy/{strategy_id}/select")
async def select_strategy(strategy_id: str, request: Request,
    user: Annotated[User, Depends(get_administrator)],
    principal: Annotated[Principal, Depends(get_current_principal)]):
    """Persist one owner's choice, independently of the main power switch."""
    verify_mutation(request, principal)
    if strategy_id not in BY_ID:
        raise failure("STRATEGY_NOT_FOUND", "Choose a listed strategy.", 404)
    store = redis_store(request)
    if await store.exists(power_key(user)):
        return await activate_strategy(strategy_id, request, user, principal)
    try:
        await store.set(selected_key(user), strategy_id)
    except Exception:
        raise failure("STRATEGY_SELECTION_UNAVAILABLE", "Choice could not be saved.", 503) from None
    return await current(request, user)


@router.post("/stop")
async def stop_bot(request: Request,
    user: Annotated[User, Depends(get_administrator)],
    principal: Annotated[Principal, Depends(get_current_principal)]):
    """Best-effort stop of every per-user automation; report partial failure."""
    verify_mutation(request, principal)
    scope = account_scope(user)
    failures = []
    # Latch OFF before touching optional subsystems: no new strategy can activate.
    try:
        await redis_store(request).delete(power_key(user))
    except Exception:
        raise failure("BOT_STOP_STORE_UNAVAILABLE", "Cannot lock bot power off.", 503) from None
    broker = getattr(request.app.state, "paper_broker", None)
    if broker is not None:
        try:
            await asyncio.to_thread(broker.set_running, scope, False)
        except PaperRejected as exc:
            if str(exc) != "PAPER_ACCOUNT_NOT_CONFIGURED":
                failures.append("PAPER_STOP_FAILED")
        except Exception:
            failures.append("PAPER_STOP_FAILED")
    demo = getattr(request.app.state, "testnet_execution", None)
    if demo is not None:
        def stop_demo():
            with demo.session(scope) as account:
                data = account.automation()
                if data["state"] in {"RUNNING", "STOPPING"}:
                    account.set_automation(False, data["revision"])
        try:
            await asyncio.to_thread(stop_demo)
        except (legacy.Halt, OSError, ValueError, TypeError):
            failures.append("TESTNET_STOP_FAILED")
    try:
        store = redis_store(request)
        async for entry in store.scan_iter(match=f"{ACTIVE_PREFIX}{scope}:*", count=16):
            key = entry.decode("utf-8") if isinstance(entry, bytes) else entry
            if key.endswith(":worker-lock"):
                continue
            await store.delete(key, RESULT_PREFIX + key.removeprefix(ACTIVE_PREFIX))
        await store.delete(monitor_key(user))
    except Exception:
        failures.append("MONITOR_SCANNER_STOP_FAILED")
    if failures:
        raise failure("BOT_STOP_INCOMPLETE", "Review remaining operations and stop them individually.", 503)
    return await current(request, user)
