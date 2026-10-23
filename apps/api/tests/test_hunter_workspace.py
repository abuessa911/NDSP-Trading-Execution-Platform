"""Workspace API, tenant isolation and in-flight stop/apply races using real Redis.

The disposable Redis instance has a private Unix socket and no TCP listener.
No exchange credentials, real account, real orders or production data are used.
"""
import json
from decimal import Decimal
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from types import SimpleNamespace
from uuid import UUID

import pytest
from redis import Redis as SyncRedis
from redis.asyncio import Redis

from test_browser_auth import browser, signed_in, ORIGIN  # shared auth fixture
from nex_api.routes import trading_profile as profile
from nex_api.routes import trading_control as control
from nex_api.routes import strategy_scanner as scanner


@pytest.fixture
def redis_socket():
    binary = shutil.which("redis-server")
    if not binary:
        pytest.skip("redis-server is needed for atomic Redis integration checks")
    with tempfile.TemporaryDirectory(prefix="hunter-workspace-") as directory:
        socket = str(Path(directory) / "redis.sock")
        process = subprocess.Popen([
            binary, "--port", "0", "--unixsocket", socket, "--unixsocketperm", "700",
            "--save", "", "--appendonly", "no", "--logfile", "/dev/null",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            client = SyncRedis(unix_socket_path=socket)
            for _ in range(100):
                try:
                    if client.ping():
                        break
                except Exception:
                    if process.poll() is not None:
                        pytest.fail("DISPOSABLE_REDIS_START_FAILED")
                    time.sleep(0.02)
            else:
                pytest.fail("DISPOSABLE_REDIS_TIMEOUT")
            client.close()
            yield socket
        finally:
            process.terminate()
            process.wait(timeout=5)


@pytest.fixture
def workspace_browser(browser, redis_socket):
    connection = Redis(unix_socket_path=redis_socket)
    browser.store.redis = connection
    browser.client.app.state.redis = connection
    browser.client.app.state.settings.hunter_market_monitor_enabled = True
    yield browser
    browser.client.portal.call(connection.aclose)


def apply(browser, **overrides):
    csrf, _ = signed_in(browser)
    settings = profile.WorkspaceSettings(
        symbol="ETHUSDT", interval="1h", mode="INVESTMENT",
        execution_method="AUTOMATIC", leverage=20, margin_mode="CROSS",
        **overrides,
    ).model_dump()
    return browser.client.put("/api/v1/trading/profile/workspace",
        json=settings, headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf})


def test_workspace_and_candles_require_session(workspace_browser):
    for path in ("/api/v1/trading/profile/workspace", "/api/v1/trading/profile/workspace/candles"):
        assert workspace_browser.client.get(path).status_code == 401


def test_confirm_persists_every_field_and_legacy_style_stays_compatible(workspace_browser):
    browser = workspace_browser
    response = apply(browser)
    assert response.status_code == 200, response.text
    view = response.json()
    for key, expected in {
        "symbol": "ETHUSDT", "interval": "1h", "mode": "INVESTMENT",
        "execution_method": "AUTOMATIC", "leverage": 20, "margin_mode": "CROSS",
        "persisted": True, "execution_authorized": False, "ndsp_contract_bound": False,
    }.items():
        assert view[key] == expected
    assert browser.client.get("/api/v1/trading/profile/workspace").json() == view
    assert browser.client.get("/api/v1/trading/profile").json()["mode"] == "INVESTMENT"
    csrf = browser.client.get("/api/v1/auth/session").json()["csrf_token"]
    assert browser.client.put("/api/v1/trading/profile", json={"mode": "SPECULATIVE"},
        headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf}).status_code == 200
    changed = browser.client.get("/api/v1/trading/profile/workspace").json()
    assert changed["mode"] == "SPECULATIVE" and changed["symbol"] == "ETHUSDT"


def test_workspace_is_scoped_to_authenticated_account_and_tenant(workspace_browser):
    browser = workspace_browser
    assert apply(browser).status_code == 200
    previous = browser.user.id
    browser.user.id = UUID(int=15)
    assert browser.client.get("/api/v1/trading/profile/workspace").json()["persisted"] is False
    browser.user.id = previous
    browser.user.tenant_id = UUID(int=25)
    assert browser.client.get("/api/v1/trading/profile/workspace").json()["persisted"] is False


@pytest.mark.parametrize("extra", [
    {"leverage": 0}, {"leverage": 126}, {"leverage": True}, {"leverage": "20"},
    {"leverage": 1.0}, {"symbol": "BTCUSDT&x=1"}, {"interval": "1m"},
    {"execution_method": "LIVE"}, {"execute": True}, {"mode": "UNVERIFIED"},
])
def test_unverified_or_invalid_configuration_cannot_be_saved(workspace_browser, extra):
    browser = workspace_browser
    csrf, _ = signed_in(browser)
    data = profile.WorkspaceSettings().model_dump() | extra
    result = browser.client.put("/api/v1/trading/profile/workspace",
        json=data, headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf})
    assert result.status_code == 422
    assert browser.client.get("/api/v1/trading/profile/workspace").json()["persisted"] is False


@pytest.mark.parametrize("headers", [{}, {"Origin": ORIGIN, "X-NEX-CSRF": "wrong"},
                                    {"Origin": "https://evil.example", "X-NEX-CSRF": "wrong"}])
def test_configuration_write_requires_origin_and_csrf(workspace_browser, headers):
    browser = workspace_browser
    signed_in(browser)
    result = browser.client.put("/api/v1/trading/profile/workspace",
        json=profile.WorkspaceSettings().model_dump(), headers=headers)
    assert result.status_code == 403


def test_apply_invalidates_only_owners_old_outputs(workspace_browser, redis_socket):
    browser = workspace_browser
    with SyncRedis(unix_socket_path=redis_socket) as store:
        mine = control.monitor_key(browser.user)
        other = SimpleNamespace(id=UUID(int=99), tenant_id=UUID(int=88))
        theirs = control.monitor_key(other)
        scan = scanner.active_key(browser.user, "trend-ladder")
        theirs_scan = scanner.active_key(other, "trend-ladder")
        for key in (mine, theirs, scan, scanner.result_key(scan), theirs_scan):
            store.set(key, "old-output")
        assert apply(browser).status_code == 200
        assert not store.exists(mine, scan, scanner.result_key(scan))
        assert store.get(theirs) == b"old-output"
        assert store.get(theirs_scan) == b"old-output"


def test_candles_use_saved_server_selection_even_with_other_query(workspace_browser, monkeypatch):
    browser = workspace_browser
    assert apply(browser).status_code == 200
    seen = []
    async def candles(**kwargs):
        seen.append(kwargs)
        return SimpleNamespace(
            source="BINANCE_PUBLIC_REST", market="usdm_futures",
            symbol=kwargs["symbol"], interval=kwargs["interval"],
            server_time_ms=1800000000000,
            candles=[SimpleNamespace(open_time_ms=1799996400000, close_time_ms=1799999999999,
                open=Decimal("10"), high=Decimal("12"), low=Decimal("9"),
                close=Decimal("11"), volume=Decimal("3"))],
        )
    monkeypatch.setattr(profile, "fetch_closed_candles", candles)
    result = browser.client.get("/api/v1/trading/profile/workspace/candles?symbol=BTCUSDT&interval=5m")
    assert result.status_code == 200
    assert seen == [{"market": "usdm_futures", "symbol": "ETHUSDT", "interval": "1h", "limit": 5}]
    assert result.json()["orders_sent"] == 0
    assert result.json()["execution_authorized"] is False
    assert result.json()["candles"][0]["close"] == "11"


def test_corrupt_workspace_is_unavailable_instead_of_default_or_zero(workspace_browser, redis_socket):
    browser = workspace_browser
    signed_in(browser)
    with SyncRedis(unix_socket_path=redis_socket) as store:
        store.set(profile.workspace_key(browser.user), '{"symbol":"untrusted"} garbage')
    assert browser.client.get("/api/v1/trading/profile/workspace").status_code == 503


@pytest.mark.asyncio
@pytest.mark.parametrize("replace_generation", [False, True])
async def test_inflight_market_read_cannot_undo_stop_or_replace_new_run(redis_socket, monkeypatch, replace_generation):
    async with Redis(unix_socket_path=redis_socket) as store:
        key = "hunter:monitor:v1:test:owner"
        raw = json.dumps({"desired": "RUNNING", "nonce": "old", "symbol": "ETHUSDT", "interval": "1h"})
        newer = json.dumps({"desired": "RUNNING", "nonce": "new", "symbol": "BTCUSDT", "interval": "5m"})
        await store.set(key, raw, ex=90)
        seen = []
        async def candles(**kwargs):
            seen.append(kwargs)
            if replace_generation:
                await store.set(key, newer, ex=90)
            else:
                await store.delete(key)
            return SimpleNamespace(candles=[SimpleNamespace(close=Decimal("10"), close_time_ms=1700000000000)])
        monkeypatch.setattr(control, "fetch_closed_candles", candles)
        assert await control.refresh_monitor(store, key, raw) is False
        assert await store.get(key) == (newer.encode() if replace_generation else None)
        assert seen[0]["symbol"] == "ETHUSDT" and seen[0]["interval"] == "1h"


def test_monitor_start_cannot_commit_previous_selection_after_apply(workspace_browser, monkeypatch):
    browser = workspace_browser
    browser.user.role = "OPERATOR"
    assert apply(browser).status_code == 200
    async def candles(**kwargs):
        await browser.store.redis.set(profile.workspace_key(browser.user),
            profile.WorkspaceSettings(symbol="BTCUSDT").model_dump_json())
        return SimpleNamespace(candles=[SimpleNamespace(close=Decimal("10"), close_time_ms=1700000000000)])
    monkeypatch.setattr(control, "fetch_closed_candles", candles)
    csrf = browser.client.get("/api/v1/auth/session").json()["csrf_token"]
    result = browser.client.post("/api/v1/trading/control/start", headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf})
    assert result.status_code == 409
    assert result.json()["reason_code"] == "WORKSPACE_CHANGED_RETRY"


def test_scanner_start_cannot_commit_previous_selection_after_apply(workspace_browser, monkeypatch):
    browser = workspace_browser
    browser.user.role = "OPERATOR"
    assert apply(browser).status_code == 200
    async def scan(*args):
        await browser.store.redis.set(profile.workspace_key(browser.user),
            profile.WorkspaceSettings(symbol="BTCUSDT").model_dump_json())
        return json.dumps({"nonce": args[-1], "signal": "NEUTRAL"})
    monkeypatch.setattr(scanner, "_scan_once", scan)
    csrf = browser.client.get("/api/v1/auth/session").json()["csrf_token"]
    result = browser.client.post("/api/v1/trading/strategies/trend-ladder/start",
        json={"symbol": "ETHUSDT", "interval": "1h", "workspace_bound": True},
        headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf})
    assert result.status_code == 409
    assert result.json()["reason_code"] == "WORKSPACE_CHANGED_RETRY"
