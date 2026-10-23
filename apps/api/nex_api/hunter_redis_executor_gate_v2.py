"""Account-scoped Redis risk gate for Hunter executor.

Read-only staging integration.
Never authorizes Binance order writes.
"""

from dataclasses import replace
from hashlib import sha256
from hmac import compare_digest
from pathlib import Path

from nex_api.hunter_execution_safety_v1 import (
    SafetyHalt,
    number,
    verify_risk,
)
from nex_api.hunter_live_risk_bridge_v1 import (
    build_verified_snapshot,
)
from nex_api.hunter_live_executor import (
    execute_once,
    require_config,
)
from nex_api.routes.risk_equity import (
    read_account_equity,
    today,
)


EMERGENCY_STOP = Path(
    "/run/hunter-ksa1-emergency-stop"
)


async def execute_with_redis_risk(
    *,
    request,
    user,
    config,
    state_path,
    exchange,
    allow_write=False,
):
    # Fail closed: this integration cannot place orders.
    if allow_write is not False:
        raise SafetyHalt(
            "REAL_ORDER_EXECUTION_DISABLED"
        )

    if EMERGENCY_STOP.exists():
        raise SafetyHalt("EMERGENCY_STOP_ACTIVE")

    if user is None or request is None:
        raise SafetyHalt("ACCOUNT_CONTEXT_REQUIRED")

    if not isinstance(config, dict):
        raise SafetyHalt("CONFIG_REQUIRED")

    if config.get("mode") not in (
        "testnet", "mainnet"
    ):
        raise SafetyHalt("INVALID_MODE")

    if exchange is None:
        raise SafetyHalt("EXCHANGE_REQUIRED")

    if getattr(exchange, "mode", None) != config["mode"]:
        raise SafetyHalt("EXCHANGE_MODE_MISMATCH")

    exchange_key = getattr(exchange, "key", None)
    if not isinstance(exchange_key, str) or not exchange_key:
        raise SafetyHalt("EXCHANGE_IDENTITY_REQUIRED")

    # Check the original executor configuration.
    require_config(config)

    # Read the real user-scoped policy and UTC baseline
    # from Redis, plus signed account equity.
    snapshot = await build_verified_snapshot(
        request, user
    )

    if snapshot.utc_day != today():
        raise SafetyHalt("RISK_DAY_CHANGED")

    stored_limit = number(
        snapshot.daily_limit_pct
    )
    configured_limit = number(
        config.get("daily_loss_pct")
    )

    if stored_limit <= 0 or stored_limit > 10:
        raise SafetyHalt(
            "DAILY_LIMIT_ABOVE_APPROVED_MAXIMUM"
        )

    if stored_limit != configured_limit:
        raise SafetyHalt(
            "REDIS_EXECUTOR_RISK_POLICY_MISMATCH"
        )

    # Verify the execution API identity matches the
    # account whose equity was checked.
    try:
        account = await read_account_equity(
            request, user
        )
    except Exception:
        raise SafetyHalt(
            "ACCOUNT_RECHECK_UNAVAILABLE"
        ) from None

    if not account:
        raise SafetyHalt(
            "ACCOUNT_RECHECK_UNAVAILABLE"
        )

    latest_equity, fingerprint = account

    expected = sha256(
        exchange_key.encode("utf-8")
    ).hexdigest()

    if not isinstance(fingerprint, str):
        raise SafetyHalt("ACCOUNT_IDENTITY_INVALID")

    if not compare_digest(expected, fingerprint):
        raise SafetyHalt(
            "EXECUTOR_ACCOUNT_MISMATCH"
        )

    # Re-evaluate with the second signed equity read.
    # A reduced equity cannot bypass the daily gate.
    snapshot = replace(
        snapshot,
        current_equity=str(latest_equity),
    )

    verify_risk(snapshot)

    if EMERGENCY_STOP.exists():
        raise SafetyHalt("EMERGENCY_STOP_ACTIVE")

    # Never authorize writes from this adapter.
    result = execute_once(
        config,
        Path(state_path),
        exchange,
        allow_write=False,
    )

    return {
        "status": "REDIS_GUARDED_DRY_RUN",
        "risk_gate": "PASS",
        "execution_enabled": False,
        "real_order_sent": False,
        "executor_result": result,
    }
