# ruff: noqa: F811 -- pytest intentionally shadows imported fixture names
"""Real owner HTTP + Redis + durable worker against a signed local DEMO fixture.

No exchange sockets or real credentials/orders. Covers stopping, crash ambiguity,
expiry, role loss, protection, ownership and a complete automatic order lifecycle.
"""
from decimal import Decimal

import httpx
import pytest

from test_browser_auth import ORIGIN
from test_hunter_workspace import (workspace_browser as workspace_browser,
    redis_socket as redis_socket, browser as browser)
from test_testnet_execution_routes import (demo_browser as demo_browser,
    configure, connect, action, BASE)
from nex_api import hunter_live_executor as engine
from nex_api import testnet_worker as worker
from nex_api.routes import testnet_execution as routes
from nex_api.routes import trading_control as control
from nex_api.testnet_execution import TestnetExecution as DemoExecution


def automate(owner, enabled=True, **extra):
    return owner.client.put(BASE+"/automation", headers=owner.headers, json={
        "enabled": enabled, "revision": owner.client.get(BASE).json()["revision"],
        "confirmation": "BINANCE_DEMO_ONLY"} | extra)


def start(owner):
    assert configure(owner).status_code == 200
    assert connect(owner).status_code == 200
    response = automate(owner)
    assert response.status_code == 200, response.text
    assert response.json()["automation"]["state"] == "RUNNING"
    return owner.client.app.state.testnet_execution.automation_accounts()[0]


def cycle(owner, authority, monkeypatch, *, allowed=True):
    async def check(app, record):
        assert record == authority
        return allowed
    monkeypatch.setattr(worker, "owner_allowed", check)
    return owner.client.portal.call(worker.tick, owner.client.app, authority)


def view(owner):
    return owner.client.get(BASE).json()


def make_active(owner, authority, monkeypatch):
    cycle(owner, authority, monkeypatch)
    assert view(owner)["pending_order"]["signal"] == "ENTER_LONG"
    cycle(owner, authority, monkeypatch)
    assert view(owner)["active_position"] and not view(owner)["pending_order"]


def finish_stop(owner, authority, monkeypatch):
    for _ in range(5):
        cycle(owner, authority, monkeypatch)
        if view(owner)["automation"]["state"] == "STOPPED":
            break
    final = view(owner)
    assert final["automation"]["state"] == "STOPPED", final
    assert not final["active_position"] and not final["pending_order"]
    return final


def test_automatic_protected_lifecycle_restart_stop_cleanup_and_flat(demo_browser, monkeypatch):
    owner = demo_browser
    authority = start(owner)
    make_active(owner, authority, monkeypatch)
    old = owner.client.app.state.testnet_execution
    owner.client.app.state.testnet_execution = DemoExecution(old.root, exchange_factory=old.exchange_factory)
    assert automate(owner, False).json()["automation"]["state"] == "STOPPING"
    finish_stop(owner, authority, monkeypatch)
    assert owner.venue.mutations == ["PROTECTIVE_STOP", "ENTRY_FILLED",
                                    "REDUCE_ONLY_EXIT_FILLED", "ORPHAN_STOP_CANCELED"]
    assert view(owner)["mainnet_orders_enabled"] is False


def test_start_replay_does_not_extend_lease_and_blocks_manual_configuration_and_key_changes(demo_browser):
    owner = demo_browser
    start(owner)
    service = owner.client.app.state.testnet_execution
    with service.session(routes.scope(owner.user)) as account:
        auto = account.automation()
        auto["expires_at"] -= 1000
        account.save_automation(auto)
    assert automate(owner).json()["automation"]["expires_at"] == auto["expires_at"]
    calls = list(owner.venue.calls)
    assert action(owner, "entry").status_code == 409
    assert configure(owner).status_code == 409
    assert owner.client.delete("/api/v1/trading/control/testnet/connect",
                               headers=owner.headers).status_code == 409
    assert connect(owner, key="ANOTHER_DEMO_KEY").status_code == 409
    assert owner.venue.calls == calls
    assert connect(owner).status_code == 200


@pytest.mark.parametrize("payload", [
    {"mode": "mainnet"}, {"scope": "another-owner"}, {"enabled": "true"},
    {"confirmation": "LIVE"}, {"duration": 86400}])
def test_automation_request_cannot_change_venue_scope_or_duration(demo_browser, payload):
    owner = demo_browser
    configure(owner)
    connect(owner)
    assert automate(owner, **payload).status_code == 422
    assert owner.venue.calls == []


def test_automation_requires_authenticated_operator_csrf_keys_and_revision(demo_browser):
    owner = demo_browser
    configure(owner)
    assert automate(owner).status_code == 409
    connect(owner)
    assert automate(owner, revision="00000000-0000-0000-0000-000000000000").status_code == 409
    csrf = owner.headers["X-NEX-CSRF"]
    owner.headers["X-NEX-CSRF"] = "bad"
    assert automate(owner).status_code == 403
    owner.headers["X-NEX-CSRF"] = csrf
    owner.user.role = "USER"
    assert automate(owner).status_code == 403
    owner.user.role = "OPERATOR"
    owner.client.cookies.clear()
    assert owner.client.put(BASE+"/automation", headers={"Origin": ORIGIN},
        json={"enabled": True, "revision": "00000000-0000-0000-0000-000000000000",
              "confirmation": "BINANCE_DEMO_ONLY"}).status_code == 401
    assert owner.venue.calls == []


def test_credential_lease_must_cover_run_and_cleanup_buffer(demo_browser):
    owner = demo_browser
    configure(owner)
    connect(owner)
    owner.client.portal.call(owner.client.app.state.redis.expire,
                             control.connection_key(owner.user), 4400)
    result = automate(owner)
    assert result.status_code == 409
    assert result.json()["reason_code"] == "TESTNET_RENEW_CREDENTIALS_BEFORE_AUTOMATION"
    assert owner.venue.calls == []


@pytest.mark.parametrize("active", [False, True])
def test_expired_lease_stops_new_entries_and_closes_only_a_proved_position(demo_browser, monkeypatch, active):
    owner = demo_browser
    authority = start(owner)
    if active:
        make_active(owner, authority, monkeypatch)
    service = owner.client.app.state.testnet_execution
    with service.session(routes.scope(owner.user)) as account:
        auto = account.automation()
        auto["expires_at"] = 1
        account.save_automation(auto)
    finish_stop(owner, authority, monkeypatch)
    assert (owner.venue.mutations.count("ENTRY_FILLED") == 1) is active


@pytest.mark.parametrize("cause", ["down_cross", "daily_loss"])
def test_closed_candle_exit_and_sticky_daily_loss_reduces_only(demo_browser, monkeypatch, cause):
    owner = demo_browser
    authority = start(owner)
    make_active(owner, authority, monkeypatch)
    original = owner.venue.read
    def read(path, params):
        response = original(path, params)
        if cause == "daily_loss" and path == "/fapi/v3/account":
            payload = response.json()
            payload["totalMarginBalance"] = "970"
            return httpx.Response(200, json=payload)
        if cause == "down_cross" and path == "/fapi/v1/klines":
            rows = response.json()
            values = [Decimal("100")]*116+[Decimal("101")]*3+[Decimal("90")]
            assert engine.crossed_down(values)
            for row, close in zip(rows, values):
                row[4] = str(close)
            return httpx.Response(200, json=rows)
        return response
    owner.venue.read = read
    cycle(owner, authority, monkeypatch)
    if cause == "daily_loss":
        assert view(owner)["pending_order"]["signal"] == "EXIT_LONG"
        assert owner.venue.mutations[-1] == "REDUCE_ONLY_EXIT_FILLED"
        assert view(owner)["daily_loss_hit"]
    else:
        # EMA crossover is no longer an authorized strategy exit.
        assert view(owner)["pending_order"] is None
        assert owner.venue.mutations[-1] != "REDUCE_ONLY_EXIT_FILLED"
    automate(owner, False)
    finish_stop(owner, authority, monkeypatch)


@pytest.mark.parametrize("stage", ["entry", "exit", "cleanup"])
def test_lost_write_ack_pauses_without_repeating_after_restart(demo_browser, monkeypatch, stage):
    owner = demo_browser
    authority = start(owner)
    if stage == "entry":
        owner.venue.lost_entry_ack = True
    else:
        make_active(owner, authority, monkeypatch)
        automate(owner, False)
        if stage == "cleanup":
            cycle(owner, authority, monkeypatch)
        service = owner.client.app.state.testnet_execution
        original_factory = service.exchange_factory
        original_handle = owner.venue.handle
        def lose_ack(request):
            response = original_handle(request)
            if ((stage == "exit" and request.method == "POST" and request.url.path == "/fapi/v1/order")
                    or (stage == "cleanup" and request.method == "DELETE")):
                raise httpx.ReadTimeout("SYNTHETIC_LOST_ACK", request=request)
            return response
        def factory(mode, key, secret):
            ex = original_factory(mode, key, secret)
            ex.client.close()
            ex.client = httpx.Client(base_url=engine.ORIGINS["testnet"],
                                    transport=httpx.MockTransport(lose_ack))
            return ex
        service.exchange_factory = factory
    result = cycle(owner, authority, monkeypatch)
    assert result["state"] == "PAUSED", result
    old = owner.client.app.state.testnet_execution
    owner.client.app.state.testnet_execution = DemoExecution(old.root, exchange_factory=old.exchange_factory)
    calls, mutations = list(owner.venue.calls), list(owner.venue.mutations)
    cycle(owner, authority, monkeypatch)
    assert owner.venue.calls == calls and owner.venue.mutations == mutations


def test_crashed_receipt_is_not_automatically_recovered_or_resubmitted(demo_browser, monkeypatch):
    owner = demo_browser
    authority = start(owner)
    cycle(owner, authority, monkeypatch)
    service = owner.client.app.state.testnet_execution
    with service.session(routes.scope(owner.user)) as account:
        receipts = engine.load_json(account.receipts_path)
        receipt = next(r for r in receipts.values() if r["action"] == "entry")
        receipt["status"] = "UNCERTAIN"
        engine.save_state(account.receipts_path, receipts)
    calls = list(owner.venue.calls)
    assert cycle(owner, authority, monkeypatch)["state"] == "PAUSED"
    assert owner.venue.calls == calls


def test_natural_protective_stop_is_reconciled_and_same_candle_never_reenters(demo_browser, monkeypatch):
    owner = demo_browser
    authority = start(owner)
    make_active(owner, authority, monkeypatch)
    owner.venue.quantity = Decimal(0)
    owner.venue.stop["algoStatus"] = "FINISHED"
    cycle(owner, authority, monkeypatch)
    assert not view(owner)["active_position"]
    cycle(owner, authority, monkeypatch)
    assert owner.venue.mutations.count("ENTRY_FILLED") == 1
    assert view(owner)["automation"]["last_result"] == "NO_NEW_CANDLE"


@pytest.mark.parametrize("active", [False, True])
def test_owner_revocation_stops_entries_and_finishes_existing_demo_protection(demo_browser, monkeypatch, active):
    owner = demo_browser
    authority = start(owner)
    if active:
        make_active(owner, authority, monkeypatch)
    for _ in range(5):
        result = cycle(owner, authority, monkeypatch, allowed=False)
        if result["state"] == "STOPPED":
            break
    assert result["state"] == "STOPPED"
    assert not view(owner)["active_position"] and not view(owner)["pending_order"]
    assert (owner.venue.mutations.count("ENTRY_FILLED") == 1) is active


def test_expired_credentials_pause_without_an_exchange_call(demo_browser, monkeypatch):
    owner = demo_browser
    authority = start(owner)
    owner.client.portal.call(owner.client.app.state.redis.delete, control.connection_key(owner.user))
    calls = list(owner.venue.calls)
    result = cycle(owner, authority, monkeypatch)
    assert result["state"] == "PAUSED" and result["reason"] == "TESTNET_CREDENTIALS_UNAVAILABLE"
    assert owner.venue.calls == calls


def test_untracked_position_cannot_be_adopted_by_start(demo_browser):
    owner = demo_browser
    configure(owner)
    connect(owner)
    owner.venue.quantity = Decimal("1")
    response = automate(owner)
    assert response.status_code == 409
    assert "FLAT_RECONCILED" in response.json()["reason_code"]
    assert owner.venue.mutations == []


def test_emergency_file_stops_automatic_writes(demo_browser, monkeypatch):
    owner = demo_browser
    authority = start(owner)
    original = engine.Path.exists
    monkeypatch.setattr(engine.Path, "exists", lambda p:
                        True if str(p) == "/run/hunter-ksa1-emergency-stop" else original(p))
    result = cycle(owner, authority, monkeypatch)
    assert result["state"] == "PAUSED" and result["reason"] == "EMERGENCY_STOP_ACTIVE"
    assert owner.venue.mutations == []


def test_owner_database_verification_preserves_rls_context(demo_browser):
    from contextlib import asynccontextmanager
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    owner = demo_browser
    authority = {"scope": routes.scope(owner.user), "issuer": owner.user.issuer,
                 "subject": owner.user.subject}
    tenant = SimpleNamespace(status="active")
    session = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: owner.user)),
        get=AsyncMock(return_value=tenant))
    @asynccontextmanager
    async def factory():
        yield session
    owner.client.app.state.session_factory = factory
    assert owner.client.portal.call(worker.owner_allowed, owner.client.app, authority)
    calls = session.execute.call_args_list
    assert len(calls) == 3
    assert calls[0].args[1] == {"issuer": authority["issuer"], "subject": authority["subject"]}
    assert calls[2].args[1] == {"uid": str(owner.user.id), "tenant": str(owner.user.tenant_id),
                               "role": "OPERATOR"}
    owner.user.role = "USER"
    assert not owner.client.portal.call(worker.owner_allowed, owner.client.app, authority)
    owner.user.role = "OPERATOR"
    tenant.status = "disabled"
    assert not owner.client.portal.call(worker.owner_allowed, owner.client.app, authority)
    # The fixture's real lifespan owns its original DB factory.
    owner.client.app.state.session_factory = None


def test_missing_protective_stop_pauses_without_any_repair_order(demo_browser, monkeypatch):
    owner = demo_browser
    authority = start(owner)
    make_active(owner, authority, monkeypatch)
    owner.venue.stop["algoStatus"] = "CANCELED"
    mutations = list(owner.venue.mutations)
    assert cycle(owner, authority, monkeypatch)["state"] == "PAUSED"
    assert owner.venue.mutations == mutations


def test_stop_cannot_claim_flat_if_an_untracked_position_appeared(demo_browser, monkeypatch):
    owner = demo_browser
    authority = start(owner)
    owner.venue.quantity = Decimal("1")
    assert automate(owner, False).status_code == 200
    result = cycle(owner, authority, monkeypatch)
    assert result["state"] == "PAUSED"
    assert result["reason"] == "TESTNET_UNTRACKED_POSITION_REQUIRES_REVIEW"
    assert owner.venue.mutations == []
