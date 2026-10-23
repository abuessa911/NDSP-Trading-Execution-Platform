"""Fail-closed Redis risk integration for Hunter.

Reads the existing account-scoped risk state and fresh signed
equity before invoking the guarded executor in dry-run mode.

No order-writing capability.
"""

from nex_api.hunter_execution_safety_v1 import (
    RiskSnapshot,
    SafetyHalt,
)
from nex_api.hunter_guarded_executor_v1 import run_guarded
from nex_api.risk_guard import percentage
from nex_api.routes.risk_equity import (
    baseline_key,
    decode,
    hit_key,
    policy_key,
    read_account_equity,
    redis_store,
    today,
)


async def build_verified_snapshot(request, user):
    """Read actual saved policy, daily baseline and current equity."""

    if user is None:
        raise SafetyHalt("USER_REQUIRED")

    try:
        store = redis_store(request)
        day = today()

        policy = decode(
            await store.get(policy_key(user))
        )

        if not isinstance(policy, dict):
            raise SafetyHalt("DAILY_RISK_POLICY_MISSING")

        limit = str(
            percentage(policy["daily_loss_pct"])
        )

        baseline = decode(
            await store.get(baseline_key(user, day))
        )

        if not isinstance(baseline, dict):
            raise SafetyHalt("DAILY_BASELINE_MISSING")

        if await store.exists(hit_key(user, day)):
            raise SafetyHalt("DAILY_LOSS_LIMIT_REACHED")

    except SafetyHalt:
        raise
    except Exception:
        raise SafetyHalt("RISK_STORE_UNAVAILABLE") from None

    try:
        # This performs a signed, read-only Binance account read.
        account = await read_account_equity(request, user)

        if account is None:
            raise SafetyHalt("LIVE_ACCOUNT_NOT_CONNECTED")

        equity, fingerprint = account

    except SafetyHalt:
        raise
    except Exception:
        raise SafetyHalt("LIVE_EQUITY_UNAVAILABLE") from None

    if (
        not baseline.get("fingerprint")
        or baseline["fingerprint"] != fingerprint
    ):
        raise SafetyHalt("ACCOUNT_CHANGED_REVIEW_REQUIRED")

    opening = baseline.get("equity")

    if opening is None:
        raise SafetyHalt("DAILY_BASELINE_INVALID")

    return RiskSnapshot(
        opening_equity=str(opening),
        current_equity=str(equity),
        daily_limit_pct=limit,
        account_verified=True,
        utc_day=day,
    )


async def guarded_live_risk_dryrun(
    *,
    request,
    user,
    config,
    state_path,
    exchange,
    ledger_path,
    order_id,
    quantity,
    price,
    max_notional,
):
    """Connect real Redis/equity checks to the offline executor."""

    snapshot = await build_verified_snapshot(request, user)

    # This adapter always runs without exchange order writes.
    return run_guarded(
        config=config,
        state_path=state_path,
        exchange=exchange,
        risk_snapshot=snapshot,
        ledger_path=ledger_path,
        order_id=order_id,
        quantity=quantity,
        price=price,
        max_notional=max_notional,
        allow_write=False,
    )
