import asyncio
from types import SimpleNamespace

import pytest

from nex_api import hunter_live_risk_bridge_v1 as bridge
from nex_api.hunter_execution_safety_v1 import (
    SafetyHalt,
    verify_risk,
)


USER = SimpleNamespace(tenant_id="tenant-test", id="user-test")


class FakeRedis:
    def __init__(self, entries, hit=False):
        self.entries = entries
        self.hit = hit

    async def get(self, key):
        return self.entries.get(key)

    async def exists(self, key):
        return int(self.hit)


def configure(
    monkeypatch,
    *,
    current="95",
    opening="100",
    pct="10",
    fingerprint="test-account",
    baseline_fingerprint="test-account",
    hit=False,
    missing_policy=False,
    missing_baseline=False,
):
    day = "2026-10-19"

    monkeypatch.setattr(bridge, "today", lambda: day)

    records = {}

    if not missing_policy:
        records[bridge.policy_key(USER)] = (
            '{"daily_loss_pct":"' + pct + '"}'
        )

    if not missing_baseline:
        records[bridge.baseline_key(USER, day)] = (
            '{"equity":"' + opening +
            '","fingerprint":"' + baseline_fingerprint + '"}'
        )

    store = FakeRedis(records, hit=hit)

    monkeypatch.setattr(
        bridge,
        "redis_store",
        lambda request: store,
    )

    async def account_reader(request, user):
        return current, fingerprint

    monkeypatch.setattr(
        bridge,
        "read_account_equity",
        account_reader,
    )


def read_snapshot():
    return asyncio.run(
        bridge.build_verified_snapshot(object(), USER)
    )


def test_saved_limit_is_used(monkeypatch):
    configure(monkeypatch, pct="10")
    snapshot = read_snapshot()

    assert snapshot.daily_limit_pct == "10"
    assert snapshot.current_equity == "95"
    assert verify_risk(snapshot)["remaining"] == "5"


def test_limit_reached_blocks(monkeypatch):
    configure(monkeypatch, current="90")

    snapshot = read_snapshot()

    with pytest.raises(
        SafetyHalt, match="DAILY_LOSS_LIMIT_REACHED"
    ):
        verify_risk(snapshot)


def test_sticky_daily_hit_blocks(monkeypatch):
    configure(monkeypatch, hit=True)

    with pytest.raises(
        SafetyHalt, match="DAILY_LOSS_LIMIT_REACHED"
    ):
        read_snapshot()


def test_changed_account_blocks(monkeypatch):
    configure(
        monkeypatch,
        fingerprint="another-account",
    )

    with pytest.raises(
        SafetyHalt, match="ACCOUNT_CHANGED"
    ):
        read_snapshot()


def test_missing_policy_blocks(monkeypatch):
    configure(monkeypatch, missing_policy=True)

    with pytest.raises(
        SafetyHalt, match="DAILY_RISK_POLICY_MISSING"
    ):
        read_snapshot()


def test_missing_baseline_blocks(monkeypatch):
    configure(monkeypatch, missing_baseline=True)

    with pytest.raises(
        SafetyHalt, match="DAILY_BASELINE_MISSING"
    ):
        read_snapshot()


def test_executor_called_with_writes_disabled(
    monkeypatch,
):
    configure(monkeypatch)

    observed = {}

    def fake_guarded(**kwargs):
        observed.update(kwargs)
        return {
            "execution_enabled": False,
            "real_order_sent": False,
        }

    monkeypatch.setattr(
        bridge,
        "run_guarded",
        fake_guarded,
    )

    result = asyncio.run(
        bridge.guarded_live_risk_dryrun(
            request=object(),
            user=USER,
            config={"mode": "testnet"},
            state_path="unused-state",
            exchange=object(),
            ledger_path="unused-ledger",
            order_id="integration-test-1",
            quantity="1",
            price="10",
            max_notional="20",
        )
    )

    assert observed["allow_write"] is False
    assert observed["risk_snapshot"].daily_limit_pct == "10"
    assert result["real_order_sent"] is False


def test_failed_risk_never_calls_executor(
    monkeypatch,
):
    configure(monkeypatch, hit=True)

    def forbidden(**kwargs):
        pytest.fail("Executor must not be reached")

    monkeypatch.setattr(
        bridge,
        "run_guarded",
        forbidden,
    )

    with pytest.raises(
        SafetyHalt, match="DAILY_LOSS_LIMIT_REACHED"
    ):
        asyncio.run(
            bridge.guarded_live_risk_dryrun(
                request=object(),
                user=USER,
                config={"mode": "testnet"},
                state_path="unused-state",
                exchange=object(),
                ledger_path="unused-ledger",
                order_id="blocked-test",
                quantity="1",
                price="10",
                max_notional="20",
            )
        )
