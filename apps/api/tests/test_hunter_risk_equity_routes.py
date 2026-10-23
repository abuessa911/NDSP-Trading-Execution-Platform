"""Authenticated risk readout and persistence; mock external account reads."""
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from starlette.requests import Request

from nex_api.dependencies import Principal
from nex_api.routes import risk_equity as r


class MemoryRedis:
    def __init__(self):
        self.data = {}

    async def get(self, key):
        return self.data.get(key)

    async def exists(self, key):
        return int(key in self.data)

    async def set(self, key, value, *, nx=False, ex=None):
        if nx and key in self.data:
            return False
        self.data[key] = value
        return True

    async def eval(self, script, numkeys, policy_key, baseline_key, percent, day):
        assert numkeys == 2 and script == r.SAVE_POLICY_SCRIPT
        previous = json.loads(self.data[policy_key]) if policy_key in self.data else None
        if previous and (previous["utc_day"] == day or baseline_key in self.data):
            if float(percent) > float(previous["daily_loss_pct"]):
                return 0
        self.data[policy_key] = json.dumps({"daily_loss_pct": percent, "utc_day": day})
        return 1


def context(*, csrf="csrf-key"):
    app = FastAPI()
    app.state.redis = MemoryRedis()
    app.state.settings = SimpleNamespace(
        oidc_redirect_uri="https://bot.ndsp.app/api/v1/auth/callback"
    )
    req = Request({
        "type": "http", "method": "PUT", "path": "/api/v1/trading/risk",
        "headers": [
            (b"origin", b"https://bot.ndsp.app"),
            (b"x-nex-csrf", csrf.encode()),
        ], "app": app,
    })
    user = SimpleNamespace(tenant_id=uuid4(), id=uuid4())
    principal = Principal("issuer", "subject", {"csrf": "csrf-key"})
    return req, user, principal


@pytest.mark.asyncio
async def test_no_limit_by_default():
    req, user, _ = context()
    result = await r.get_risk_view(req, user)
    assert result.configured is False and result.new_entries_blocked
    assert result.execution_enabled is False and result.order_gate_attached is False


@pytest.mark.asyncio
async def test_policy_saved_without_default_and_no_network():
    req, user, principal = context()
    result = await r.set_daily_limit(req, r.RiskUpdate(daily_loss_pct="0.25"), user, principal)
    assert result.daily_loss_pct == "0.25"
    assert result.state == "READONLY_ACCOUNT_MISSING"
    assert result.new_entries_blocked


@pytest.mark.asyncio
async def test_same_day_increase_rejected():
    req, user, principal = context()
    await r.set_daily_limit(req, r.RiskUpdate(daily_loss_pct="1"), user, principal)
    with pytest.raises(HTTPException) as exc:
        await r.set_daily_limit(req, r.RiskUpdate(daily_loss_pct="2"), user, principal)
    assert exc.value.status_code == 409
    reduced = await r.set_daily_limit(req, r.RiskUpdate(daily_loss_pct="0.1"), user, principal)
    assert reduced.daily_loss_pct == "0.1"


@pytest.mark.asyncio
async def test_cross_user_policy_isolation():
    req, user, principal = context()
    other = SimpleNamespace(tenant_id=uuid4(), id=uuid4())
    await r.set_daily_limit(req, r.RiskUpdate(daily_loss_pct="3.5"), user, principal)
    assert (await r.get_risk_view(req, other)).daily_loss_pct is None


@pytest.mark.asyncio
async def test_csrf_rejected():
    req, user, principal = context(csrf="invalid")
    with pytest.raises(HTTPException) as exc:
        await r.set_daily_limit(req, r.RiskUpdate(daily_loss_pct="2"), user, principal)
    assert exc.value.status_code in (400, 403)


@pytest.mark.asyncio
async def test_loss_latch_survives_recovery(monkeypatch):
    req, user, principal = context()
    await r.set_daily_limit(req, r.RiskUpdate(daily_loss_pct="1"), user, principal)
    await req.app.state.redis.set(r.live_connection_key(user), b"encrypted-placeholder")
    async def first(*args):
        return "99", "accountfingerprint"
    monkeypatch.setattr(r, "read_account_equity", first)
    # Baseline starts at 99.
    initial = await r.get_risk_view(req, user)
    assert initial.new_entries_blocked is False
    async def loss(*args):
        return "97", "accountfingerprint"
    monkeypatch.setattr(r, "read_account_equity", loss)
    breached = await r.get_risk_view(req, user)
    assert breached.new_entries_blocked
    async def recovered(*args):
        return "105", "accountfingerprint"
    monkeypatch.setattr(r, "read_account_equity", recovered)
    assert (await r.get_risk_view(req, user)).state == "DAILY_LOSS_LIMIT_REACHED"


@pytest.mark.asyncio
async def test_key_rotation_cannot_reset_baseline(monkeypatch):
    req, user, principal = context()
    await r.set_daily_limit(req, r.RiskUpdate(daily_loss_pct="1"), user, principal)
    await req.app.state.redis.set(r.live_connection_key(user), b"encrypted-placeholder")
    async def account1(*args):
        return "100", "fingerprint1"
    monkeypatch.setattr(r, "read_account_equity", account1)
    await r.get_risk_view(req, user)
    async def account2(*args):
        return "100", "fingerprint2"
    monkeypatch.setattr(r, "read_account_equity", account2)
    changed = await r.get_risk_view(req, user)
    assert changed.state == "ACCOUNT_CHANGED_REVIEW_REQUIRED"
    assert changed.new_entries_blocked
