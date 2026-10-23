import base64
import tempfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from nex_api.hunter_execution_safety_v1 import (
    DurableOrderLedger,
    RiskSnapshot,
    SafetyHalt,
    ed25519_signature,
    simulate_order,
    verify_risk,
)


def snapshot(current="95", verified=True):
    return RiskSnapshot(
        opening_equity="100",
        current_equity=current,
        daily_limit_pct="10",
        account_verified=verified,
        utc_day="2026-10-19",
    )


def test_risk_allows_loss_below_limit():
    assert verify_risk(snapshot())["remaining"] == "5"


def test_risk_blocks_limit():
    with pytest.raises(SafetyHalt, match="DAILY_LOSS"):
        verify_risk(snapshot("90"))


def test_risk_blocks_missing_verification():
    with pytest.raises(SafetyHalt, match="ACCOUNT_NOT_VERIFIED"):
        verify_risk(snapshot(verified=False))


def test_risk_blocks_invalid_equity():
    with pytest.raises(SafetyHalt):
        verify_risk(snapshot("NaN"))


def test_ed25519_sign_and_verify():
    key = Ed25519PrivateKey.generate()
    query, signature = ed25519_signature(
        key,
        {"timestamp": 123456789, "recvWindow": 5000},
    )
    key.public_key().verify(
        base64.b64decode(signature),
        query.encode("ascii"),
    )


def test_real_execution_is_blocked():
    with tempfile.TemporaryDirectory() as folder:
        ledger = DurableOrderLedger(Path(folder) / "ledger.db")
        with pytest.raises(
            SafetyHalt, match="REAL_ORDER_EXECUTION_DISABLED"
        ):
            simulate_order(
                mode="mainnet",
                order_id="mainnet-block",
                snapshot=snapshot(),
                ledger=ledger,
                quantity="1",
                price="10",
                max_notional="50",
            )


def test_excessive_order_blocked():
    with tempfile.TemporaryDirectory() as folder:
        ledger = DurableOrderLedger(Path(folder) / "ledger.db")
        with pytest.raises(
            SafetyHalt, match="ORDER_NOTIONAL_LIMIT_REACHED"
        ):
            simulate_order(
                mode="dry-run",
                order_id="too-large",
                snapshot=snapshot(),
                ledger=ledger,
                quantity="100",
                price="10",
                max_notional="50",
            )


def test_duplicate_blocked_after_restart():
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "ledger.db"

        args = {
            "mode": "dry-run",
            "order_id": "same-order",
            "snapshot": snapshot(),
            "quantity": "1",
            "price": "10",
            "max_notional": "50",
        }

        result = simulate_order(
            **args, ledger=DurableOrderLedger(path)
        )
        assert result["real_order_sent"] is False

        with pytest.raises(
            SafetyHalt, match="DUPLICATE_ORDER_BLOCKED"
        ):
            simulate_order(
                **args, ledger=DurableOrderLedger(path)
            )


def test_risk_failure_does_not_reserve_order():
    with tempfile.TemporaryDirectory() as folder:
        ledger = DurableOrderLedger(Path(folder) / "ledger.db")

        with pytest.raises(SafetyHalt):
            simulate_order(
                mode="dry-run",
                order_id="blocked",
                snapshot=snapshot("80"),
                ledger=ledger,
                quantity="1",
                price="10",
                max_notional="50",
            )

        result = simulate_order(
            mode="dry-run",
            order_id="blocked",
            snapshot=snapshot("95"),
            ledger=ledger,
            quantity="1",
            price="10",
            max_notional="50",
        )
        assert result["status"] == "SIMULATED_ONLY"
