"""Live Binance keys: authenticated, server-side, fail-closed, no orders."""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException
from pydantic import SecretStr
from starlette.requests import Request

from nex_api.binance_live_readonly_connector import LiveAccountProbe, LiveConnectivityError
from nex_api.dependencies import Principal
from nex_api.routes import trading_control as control


class FakeRedis:
    def __init__(self):
        self.items = {}

    async def get(self, key):
        return self.items.get(key)

    async def ttl(self, key):
        return 3600 if key in self.items else -2

    async def exists(self, key):
        return int(key in self.items)

    async def set(self, key, value, *, ex=None, nx=False, xx=False):
        self.items[key] = value
        return True

    async def delete(self, key):
        return int(self.items.pop(key, None) is not None)


def ctx(*, vault=True, csrf="valid"):
    app = FastAPI()
    app.state.redis = FakeRedis()
    app.state.settings = SimpleNamespace(
        oidc_redirect_uri="https://bot.ndsp.app/api/v1/auth/callback",
        hunter_live_vault_key=(
            SecretStr(Fernet.generate_key().decode()) if vault else None
        ),
    )
    request = Request({
        "type": "http", "method": "POST", "path": "/api/v1/trading/control/live/connect",
        "headers": [(b"origin", b"https://bot.ndsp.app"), (b"x-nex-csrf", csrf.encode())],
        "app": app,
    })
    user = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
    principal = Principal("issuer", "subject", {"csrf": "valid"})
    return request, user, principal


@pytest.mark.asyncio
async def test_real_readonly_key_encrypted_held_one_hour_and_deleted(monkeypatch):
    request, user, principal = ctx()
    async def fake_probe(key, secret):
        assert key == "test_key_123456"
        assert secret == "super-secret"
        return LiveAccountProbe(True, True, True)
    monkeypatch.setattr(control, "probe_live_readonly_account", fake_probe)
    credentials = control.ConnectionRequest(
        api_key="test_key_123456", api_secret="super-secret"
    )
    result = await control.live_readonly_connect(request, credentials, user, principal)
    assert result.authenticated and not result.execution_enabled
    assert result.expires_in_seconds == 3600
    stored = await request.app.state.redis.get(control.live_connection_key(user))
    assert b"super-secret" not in stored
    assert b"test_key_123456" not in stored
    status = await control.state(request, user)
    assert status.live_readonly_key_saved and not status.execution_enabled
    removed = await control.live_readonly_disconnect(request, user, principal)
    assert not removed.authenticated
    assert not await request.app.state.redis.exists(control.live_connection_key(user))


@pytest.mark.asyncio
async def test_no_vault_prevents_any_network_call(monkeypatch):
    request, user, principal = ctx(vault=False)
    async def fail(*args, **kwargs):
        raise AssertionError("Forbidden upstream")
    monkeypatch.setattr(control, "probe_live_readonly_account", fail)
    with pytest.raises(HTTPException) as error:
        await control.live_readonly_connect(
            request, control.ConnectionRequest(
                api_key="test_key_123456", api_secret="super-secret"
            ), user, principal)
    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_csrf_enforced_for_real_account_changes(monkeypatch):
    request, user, principal = ctx(csrf="invalid")
    async def fail(*args, **kwargs):
        raise AssertionError("Forbidden upstream")
    monkeypatch.setattr(control, "probe_live_readonly_account", fail)
    with pytest.raises(HTTPException) as error:
        await control.live_readonly_connect(
            request, control.ConnectionRequest(
                api_key="test_key_123456", api_secret="super-secret"
            ), user, principal)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_rejected_trade_permission_never_persists(monkeypatch):
    request, user, principal = ctx()
    async def reject(*args, **kwargs):
        raise LiveConnectivityError("LIVE_PRIVILEGED_KEY_REJECTED")
    monkeypatch.setattr(control, "probe_live_readonly_account", reject)
    with pytest.raises(HTTPException) as err:
        await control.live_readonly_connect(
            request, control.ConnectionRequest(
                api_key="test_key_123456", api_secret="super-secret"
            ), user, principal)
    assert err.value.status_code == 422
    assert not await request.app.state.redis.exists(control.live_connection_key(user))
