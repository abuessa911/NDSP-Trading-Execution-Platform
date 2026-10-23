"""Fail-closed adapter for the existing Hunter executor.

Offline/dry-run integration only.
No production credential loading or mainnet order submission.
"""

from pathlib import Path

from nex_api.hunter_execution_safety_v1 import (
    DurableOrderLedger,
    RiskSnapshot,
    SafetyHalt,
    simulate_order,
)
from nex_api.hunter_live_executor import execute_once


def run_guarded(
    *,
    config,
    state_path,
    exchange,
    risk_snapshot,
    ledger_path,
    order_id,
    quantity,
    price,
    max_notional,
    allow_write=False,
):
    # Never turn this prototype into an order-writing shortcut.
    if allow_write is not False:
        raise SafetyHalt("REAL_ORDER_EXECUTION_DISABLED")

    if not isinstance(config, dict):
        raise SafetyHalt("CONFIG_REQUIRED")

    if config.get("mode") not in ("testnet", "mainnet"):
        raise SafetyHalt("INVALID_EXCHANGE_MODE")

    if not isinstance(risk_snapshot, RiskSnapshot):
        raise SafetyHalt("VERIFIED_RISK_SNAPSHOT_REQUIRED")

    if exchange is None:
        raise SafetyHalt("EXCHANGE_REQUIRED")

    # Validate risk, notional, and durable duplicate ID
    # before invoking any executor logic.
    simulation = simulate_order(
        mode="dry-run",
        order_id=order_id,
        snapshot=risk_snapshot,
        ledger=DurableOrderLedger(ledger_path),
        quantity=quantity,
        price=price,
        max_notional=max_notional,
    )

    # Existing executor is invoked with writes forcibly disabled.
    execution = execute_once(
        config,
        Path(state_path),
        exchange,
        allow_write=False,
    )

    return {
        "simulation": simulation,
        "executor_result": execution,
        "real_order_sent": False,
        "execution_enabled": False,
    }
