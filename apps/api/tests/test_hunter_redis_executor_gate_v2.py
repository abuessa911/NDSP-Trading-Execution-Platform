import asyncio
from hashlib import sha256

import pytest

from nex_api import (
    hunter_redis_executor_gate_v2 as gate,
)
from nex_api.hunter_execution_safety_v1 import (
    RiskSnapshot,
    SafetyHalt,
)


KEY = "mock-exchange-key"


class Exchange:
    mode = "testnet"
    key = KEY


def snapshot(current="95"):
    return RiskSnapshot(
        opening_equity="100",
        current_equity=current,
        daily_limit_pct="10",
        account_verified=True,
        utc_day="2026-10-19",
    )


def prepare(
    monkeypatch,
    *,
    current="95",
    identity=KEY,
    limit="10",
):
    monkeypatch.setattr(
        gate.EMERGENCY_STOP.__class__,
        "exists",
        lambda self: False,
    )

    monkeypatch.setattr(
        gate, "today",
        lambda: "2026-10-19",
    )

    monkeypatch.setattr(
        gate, "require_config",
        lambda cfg: cfg,
    )

    async def saved_risk(request, user):
        s = snapshot(current)
        return s.__class__(
            opening_equity=s.opening_equity,
            current_equity=s.current_equity,
            daily_limit_pct=limit,
            account_verified=True,
            utc_day=s.utc_day,
        )

    async def signed_equity(request, user):
        return (
            current,
            sha256(identity.encode()).hexdigest(),
        )

    monkeypatch.setattr(
        gate, "build_verified_snapshot",
        saved_risk,
    )

    monkeypatch.setattr(
        gate, "read_account_equity",
        signed_equity,
    )


def run(tmp_path, **overrides):
    args = dict(
        request=object(),
        user=object(),
        config={
            "mode": "testnet",
            "daily_loss_pct": "10",
        },
        state_path=tmp_path / "state.json",
        exchange=Exchange(),
    )
    args.update(overrides)
    return asyncio.run(
        gate.execute_with_redis_risk(**args)
    )


def test_valid_risk_calls_executor_readonly(
    tmp_path, monkeypatch
):
    prepare(monkeypatch)
    calls = []

    def fake_executor(*args, **kwargs):
        calls.append(kwargs["allow_write"])
        return {"status": "DRY_RUN"}

    monkeypatch.setattr(
        gate, "execute_once",
        fake_executor,
    )

    result = run(tmp_path)

    assert calls == [False]
    assert result["risk_gate"] == "PASS"
    assert result["real_order_sent"] is False


def test_daily_loss_blocks_before_executor(
    tmp_path, monkeypatch
):
    prepare(monkeypatch, current="90")

    def forbidden(*args, **kwargs):
        pytest.fail("EXECUTOR_REACHED")

    monkeypatch.setattr(
        gate, "execute_once", forbidden
    )

    with pytest.raises(
        SafetyHalt, match="DAILY_LOSS"
    ):
        run(tmp_path)


def test_other_account_blocks(
    tmp_path, monkeypatch
):
    prepare(
        monkeypatch,
        identity="different-account",
    )

    with pytest.raises(
        SafetyHalt, match="ACCOUNT_MISMATCH"
    ):
        run(tmp_path)


def test_risk_policy_mismatch_blocks(
    tmp_path, monkeypatch
):
    prepare(monkeypatch, limit="8")

    with pytest.raises(
        SafetyHalt, match="POLICY_MISMATCH"
    ):
        run(tmp_path)


def test_real_writes_blocked(
    tmp_path, monkeypatch
):
    prepare(monkeypatch)

    with pytest.raises(
        SafetyHalt,
        match="REAL_ORDER_EXECUTION_DISABLED",
    ):
        run(tmp_path, allow_write=True)


def test_emergency_stop_blocks(
    tmp_path, monkeypatch
):
    prepare(monkeypatch)

    monkeypatch.setattr(
        gate.EMERGENCY_STOP.__class__,
        "exists",
        lambda self: True,
    )

    with pytest.raises(
        SafetyHalt,
        match="EMERGENCY_STOP_ACTIVE",
    ):
        run(tmp_path)
