import pytest

from nex_api.hunter_execution_safety_v1 import (
    RiskSnapshot,
    SafetyHalt,
)
from nex_api import hunter_guarded_executor_v1 as adapter


def snapshot(equity="95", verified=True):
    return RiskSnapshot(
        opening_equity="100",
        current_equity=equity,
        daily_limit_pct="10",
        account_verified=verified,
        utc_day="2026-10-19",
    )


def arguments(tmp_path):
    return dict(
        config={"mode": "testnet"},
        state_path=tmp_path / "state.json",
        exchange=object(),
        risk_snapshot=snapshot(),
        ledger_path=tmp_path / "orders.db",
        order_id="test-order-001",
        quantity="1",
        price="10",
        max_notional="20",
    )


def test_valid_request_calls_existing_executor_readonly(
    tmp_path, monkeypatch
):
    calls = []

    def fake_execute(config, state_path, exchange, allow_write):
        calls.append(allow_write)
        return {"status": "DRY_RUN"}

    monkeypatch.setattr(adapter, "execute_once", fake_execute)

    result = adapter.run_guarded(**arguments(tmp_path))

    assert calls == [False]
    assert result["real_order_sent"] is False
    assert result["execution_enabled"] is False


def test_daily_loss_blocks_executor(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Executor must not run")

    monkeypatch.setattr(adapter, "execute_once", forbidden)

    args = arguments(tmp_path)
    args["risk_snapshot"] = snapshot("90")

    with pytest.raises(SafetyHalt, match="DAILY_LOSS"):
        adapter.run_guarded(**args)


def test_unverified_risk_blocks_executor(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Executor must not run")

    monkeypatch.setattr(adapter, "execute_once", forbidden)

    args = arguments(tmp_path)
    args["risk_snapshot"] = snapshot(verified=False)

    with pytest.raises(SafetyHalt, match="ACCOUNT_NOT_VERIFIED"):
        adapter.run_guarded(**args)


def test_duplicate_blocked_after_restart(tmp_path, monkeypatch):
    calls = []

    def fake_execute(*args, **kwargs):
        calls.append(1)
        return {"status": "DRY_RUN"}

    monkeypatch.setattr(adapter, "execute_once", fake_execute)

    args = arguments(tmp_path)
    adapter.run_guarded(**args)

    with pytest.raises(SafetyHalt, match="DUPLICATE_ORDER"):
        adapter.run_guarded(**args)

    assert len(calls) == 1


def test_real_writes_never_reach_executor(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Real execution must not run")

    monkeypatch.setattr(adapter, "execute_once", forbidden)

    with pytest.raises(
        SafetyHalt, match="REAL_ORDER_EXECUTION_DISABLED"
    ):
        adapter.run_guarded(
            **arguments(tmp_path),
            allow_write=True,
        )


def test_order_size_limit_blocks_executor(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Oversized request reached executor")

    monkeypatch.setattr(adapter, "execute_once", forbidden)

    args = arguments(tmp_path)
    args["max_notional"] = "5"

    with pytest.raises(
        SafetyHalt, match="ORDER_NOTIONAL_LIMIT"
    ):
        adapter.run_guarded(**args)


def test_missing_risk_blocks_executor(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Missing risk reached executor")

    monkeypatch.setattr(adapter, "execute_once", forbidden)

    args = arguments(tmp_path)
    args["risk_snapshot"] = None

    with pytest.raises(
        SafetyHalt, match="VERIFIED_RISK_SNAPSHOT_REQUIRED"
    ):
        adapter.run_guarded(**args)
