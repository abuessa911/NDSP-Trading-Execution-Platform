"""Hunter isolated control endpoints: no real-money or order capabilities."""
import json
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException
from pydantic import SecretStr
from starlette.requests import Request

from nex_api.binance_testnet_connector import AccountProbe
from nex_api.dependencies import Principal
from nex_api.routes import trading_control as control


class FakeRedis:
    def __init__(self):
        self.db = {}

    async def get(self, key):
        return self.db.get(key)

    async def mget(self, *keys):
        return [self.db.get(key) for key in keys]

    async def ttl(self, key):
        return 900 if key in self.db else -2

    async def exists(self, key):
        return int(key in self.db)

    async def set(self, key, value, *, ex=None, nx=False, xx=False):
        if nx and key in self.db:
            return False
        if xx and key not in self.db:
            return False
        self.db[key] = value
        return True

    async def delete(self, key):
        return int(self.db.pop(key, None) is not None)

    async def eval(self, script, count, *args):
        assert script == control.CONFIRMED_MONITOR_START
        dest, style, workspace, expected_style, expected_workspace, raw, ttl = args
        if ((self.db.get(style) or "") != expected_style
                or (self.db.get(workspace) or "") != expected_workspace):
            return 0
        self.db[dest] = raw
        return 1


def context(*, origin="https://bot.ndsp.app", csrf="proof", monitor=True, vault=True):
    app = FastAPI()
    app.state.redis = FakeRedis()
    app.state.settings = SimpleNamespace(
        oidc_redirect_uri="https://bot.ndsp.app/api/v1/auth/callback",
        hunter_market_monitor_enabled=monitor,
        hunter_testnet_vault_key=SecretStr(Fernet.generate_key().decode()) if vault else None,
    )
    headers = [(b"origin", origin.encode()), (b"x-nex-csrf", csrf.encode())]
    request = Request({"type": "http", "method": "POST", "path": "/api/v1/trading/control",
                       "headers": headers, "app": app})
    user = SimpleNamespace(id=uuid4(), tenant_id=uuid4())
    principal = Principal("issuer", "subject", {"csrf": "proof"})
    return request, user, principal


@pytest.mark.asyncio
async def test_start_reads_real_closed_candle_and_stops_without_any_order(monkeypatch):
    request, user, principal = context()
    calls = []

    async def fake_market(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(candles=(
            SimpleNamespace(close=Decimal("75000.25"), close_time_ms=1700000000000),
        ))
    monkeypatch.setattr(control, "fetch_closed_candles", fake_market)

    started = await control.start_monitor(request, user, principal)
    assert started.state == "MONITORING"
    assert started.execution_enabled is False
    assert started.order_submission_available is False
    assert started.last_closed_price == "75000.25"
    assert calls == [{"market": "usdm_futures", "symbol": "BTCUSDT",
                      "interval": "5m", "limit": 3}]
    stopped = await control.stop_monitor(request, user, principal)
    assert stopped.state == "STOPPED"


@pytest.mark.asyncio
async def test_cannot_start_without_worker(monkeypatch):
    request, user, principal = context(monitor=False)
    with pytest.raises(HTTPException) as failure:
        await control.start_monitor(request, user, principal)
    assert failure.value.status_code == 503


@pytest.mark.asyncio
async def test_csrf_origin_and_token_required_even_for_stop():
    request, user, principal = context(csrf="incorrect")
    with pytest.raises(HTTPException) as failure:
        await control.stop_monitor(request, user, principal)
    assert failure.value.detail["reason_code"] == "CSRF_NOT_VALID"
    request, user, principal = context(origin="https://malicious.example")
    with pytest.raises(HTTPException) as failure:
        await control.stop_monitor(request, user, principal)
    assert failure.value.detail["reason_code"] == "CSRF_NOT_VALID"


@pytest.mark.asyncio
async def test_testnet_credentials_encrypted_and_removable(monkeypatch):
    request, user, principal = context()
    seen = []

    async def fake_probe(key, secret):
        seen.append((key, secret))
        return AccountProbe(reachable=True, authenticated=True)
    monkeypatch.setattr(control, "probe_testnet_account", fake_probe)
    credentials = control.ConnectionRequest(api_key="test_api_123456",
                                            api_secret="secret_for_test")
    verified = await control.testnet_connect(request, credentials, user, principal)
    assert verified.authenticated and not verified.execution_enabled
    stored = await request.app.state.redis.get(control.connection_key(user))
    assert b"secret_for_test" not in stored and b"test_api_123456" not in stored
    assert seen == [("test_api_123456", "secret_for_test")]
    assert (await control.state(request, user)).testnet_key_saved
    removed = await control.testnet_disconnect(request, user, principal)
    assert removed.authenticated is False
    assert await request.app.state.redis.get(control.connection_key(user)) is None


@pytest.mark.asyncio
async def test_missing_encryption_key_rejects_before_probing(monkeypatch):
    request, user, principal = context(vault=False)

    async def must_not_probe(*args, **kwargs):
        raise AssertionError("No network must happen")
    monkeypatch.setattr(control, "probe_testnet_account", must_not_probe)
    credentials = control.ConnectionRequest(api_key="test_api_123456",
                                            api_secret="secret_for_test")
    with pytest.raises(HTTPException) as failure:
        await control.testnet_connect(request, credentials, user, principal)
    assert failure.value.status_code == 503


def test_monitor_stale_after_heartbeat_timeout():
    data = {"desired": "RUNNING", "checked_ms": 1700000000000,
            "close": "1.23", "closed_ms": 1700000000000}
    result = control.view(json.dumps(data), 20, True)
    assert result.state == "STALLED"
    assert result.execution_enabled is False
