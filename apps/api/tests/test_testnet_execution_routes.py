"""Real authenticated HTTP -> encrypted vault -> durable engine -> local signer fixture.

No exchange network, real credentials or real-money writes. Real Redis, sessions,
CSRF, account scoping, locks and file reload are exercised.
"""
import asyncio
from threading import Event
from uuid import UUID, uuid4

from cryptography.fernet import Fernet
import httpx
from pydantic import SecretStr
import pytest

from test_browser_auth import ORIGIN, signed_in
from test_hunter_workspace import (workspace_browser as workspace_browser,
    redis_socket as redis_socket, browser as browser)
from test_hunter_testnet_lifecycle import ExchangeFixture, KEY, SECRET
from nex_api import hunter_live_executor as legacy
from nex_api.binance_testnet_connector import AccountProbe
from nex_api.routes import trading_control as control
from nex_api.routes import testnet_execution as routes
from nex_api.testnet_execution import TestnetExecution as DemoExecution, PRESET

BASE = "/api/v1/trading/testnet"


@pytest.fixture
def demo_browser(workspace_browser, tmp_path, monkeypatch):  # noqa: F811 - pytest fixtures
    owner = workspace_browser
    owner.user.role = "OPERATOR"
    owner.client.app.state.settings.hunter_testnet_vault_key = SecretStr(Fernet.generate_key().decode())
    csrf, _ = signed_in(owner)
    owner.headers = {"Origin": ORIGIN, "X-NEX-CSRF": csrf}
    service = DemoExecution(tmp_path/"execution")
    owner.client.app.state.testnet_execution = service
    with service.session(routes.scope(owner.user)) as session:
        state_path = session.state_path
    owner.venue = ExchangeFixture(state_path)
    real_exchange = legacy.Exchange

    def connector(mode, key, secret):
        assert mode == "testnet" and key == KEY and secret == SECRET
        return real_exchange(mode, key, secret, transport=httpx.MockTransport(owner.venue.handle))
    service.exchange_factory = connector

    async def probe(key, secret):
        assert key == KEY and secret == SECRET
        return AccountProbe(reachable=True, authenticated=True)
    monkeypatch.setattr(control, "probe_testnet_account", probe)
    return owner


def configure(owner, **overrides):
    values = {k: v for k, v in PRESET.items() if k not in {"mode", "mainnet_enabled", "strategy"}}
    return owner.client.put(BASE+"/configuration", headers=owner.headers,
        json=values | {"confirmation": "BINANCE_DEMO_ONLY"} | overrides)


def connect(owner, key=KEY):
    return owner.client.post("/api/v1/trading/control/testnet/connect", headers=owner.headers,
                            json={"api_key": key, "api_secret": SECRET})


def action(owner, name, *, request_id=None, revision=None, position_id=None, **extra):
    if revision is None:
        revision = owner.client.get(BASE).json()["revision"]
    return owner.client.post(BASE+"/actions", headers=owner.headers, json={
        "request_id": request_id or str(uuid4()), "revision": revision, "action": name,
        "position_id": position_id, "confirmation": "BINANCE_DEMO_ONLY"} | extra)


def test_http_full_protected_lifecycle_and_receipt_replay_after_restart(demo_browser):
    owner = demo_browser
    assert configure(owner).status_code == 200
    assert connect(owner).status_code == 200
    stored = owner.client.portal.call(owner.client.app.state.redis.get, control.connection_key(owner.user))
    assert KEY.encode() not in stored and SECRET.encode() not in stored
    assert action(owner, "preflight").json()["status"] == "CONFIRMED"
    assert action(owner, "dry-run").json()["result"]["result"]["signal"] == "ENTER_LONG"
    request_id = str(uuid4())
    entered = action(owner, "entry", request_id=request_id)
    assert entered.status_code == 200 and entered.json()["status"] == "CONFIRMED"
    assert owner.venue.mutations == ["PROTECTIVE_STOP", "ENTRY_FILLED"]
    calls = list(owner.venue.calls)
    old = owner.client.app.state.testnet_execution
    replacement = DemoExecution(old.root, exchange_factory=old.exchange_factory)
    owner.client.app.state.testnet_execution = replacement
    assert action(owner, "entry", request_id=request_id).json() == entered.json()
    assert owner.venue.calls == calls
    assert action(owner, "entry").json()["status"] == "REJECTED"
    assert owner.venue.calls == calls
    assert action(owner, "inspect").json()["result"]["status"] == "ENTRY_PROTECTED_CONFIRMED"
    assert action(owner, "reconcile").json()["status"] == "CONFIRMED"
    view = owner.client.get(BASE).json()
    assert view["active_position"] and not view["pending_order"]
    assert action(owner, "exit", position_id=view["active_position"]["id"]).json()["status"] == "CONFIRMED"
    assert action(owner, "cleanup").json()["status"] == "CONFIRMED"
    assert action(owner, "reconcile").json()["result"]["status"] == "EXIT_FLAT_STOP_GONE"
    final = owner.client.get(BASE).json()
    assert not final["pending_order"] and not final["active_position"] and not final["halted"]
    assert owner.venue.mutations == ["PROTECTIVE_STOP", "ENTRY_FILLED", "REDUCE_ONLY_EXIT_FILLED", "ORPHAN_STOP_CANCELED"]
    assert all(p.stat().st_mode & 0o077 == 0 for p in old.root.rglob("*") if p.is_file())
    assert final["mainnet_orders_enabled"] is False


def test_lost_buy_ack_is_uncertain_and_cannot_duplicate_with_new_id(demo_browser):
    owner = demo_browser
    configure(owner)
    connect(owner)
    owner.venue.lost_entry_ack = True
    request_id = str(uuid4())
    result = action(owner, "entry", request_id=request_id)
    assert result.json()["status"] == "UNCERTAIN"
    calls = list(owner.venue.calls)
    assert action(owner, "entry", request_id=request_id).json() == result.json()
    assert action(owner, "entry").json()["status"] == "REJECTED"
    assert owner.venue.calls == calls and len(owner.venue.orders) == 1
    assert owner.venue.stop["algoStatus"] == "NEW"
    assert owner.client.get(BASE).json()["halted"]


def test_account_isolation_and_credential_rotation_cannot_orphan_position(demo_browser, monkeypatch):
    owner = demo_browser
    configure(owner)
    connect(owner)
    action(owner, "entry")
    action(owner, "reconcile")
    view = owner.client.get(BASE).json()
    assert configure(owner, symbol="ETHUSDT").status_code == 409
    disconnected = owner.client.delete("/api/v1/trading/control/testnet/connect", headers=owner.headers)
    assert disconnected.status_code == 409
    assert connect(owner, key="DIFFERENT_DEMO_KEY").status_code == 409
    assert connect(owner).status_code == 200  # safe TTL renewal
    owner.user.id = UUID(int=2156)
    other = owner.client.get(BASE).json()
    assert not other["configured"] and other["receipts"] == [] and other["active_position"] is None
    configure(owner)
    connect(owner)
    calls = list(owner.venue.calls)
    denied = action(owner, "entry")
    assert denied.status_code == 409 and denied.json()["reason_code"] == "TESTNET_KEY_BOUND_TO_ANOTHER_OWNER"
    assert owner.venue.calls == calls and view["active_position"]


@pytest.mark.parametrize("extra", [{"mode": "mainnet"}, {"tenant_id": str(uuid4())},
                                  {"url": "https://fapi.binance.com"}, {"confirmation": "LIVE"}])
def test_caller_cannot_select_mainnet_scope_or_url(demo_browser, extra):
    owner = demo_browser
    configure(owner)
    connect(owner)
    assert action(owner, "entry", **extra).status_code == 422
    assert owner.venue.calls == []


def test_missing_credentials_csrf_roles_and_session_fail_before_exchange(demo_browser):
    owner = demo_browser
    configure(owner)
    denied = action(owner, "entry")
    assert denied.status_code == 409 and "CREDENTIALS_REQUIRED" in denied.json()["reason_code"]
    connect(owner)
    owner.headers["X-NEX-CSRF"] = "bad"
    assert action(owner, "entry").status_code == 403
    owner.headers["X-NEX-CSRF"] = owner.client.get("/api/v1/auth/session").json()["csrf_token"]
    owner.user.role = "USER"
    assert action(owner, "entry").status_code == 403
    owner.client.cookies.clear()
    assert owner.client.get(BASE).status_code == 401
    assert owner.venue.calls == []


def test_stale_configuration_and_wrong_exit_position_are_rejected_before_network(demo_browser):
    owner = demo_browser
    original = configure(owner).json()["revision"]
    configure(owner, daily_loss_pct="1")
    connect(owner)
    assert action(owner, "entry", revision=original).status_code == 409
    action(owner, "entry")
    action(owner, "reconcile")
    calls = list(owner.venue.calls)
    assert action(owner, "exit", position_id="HK1"+"0"*24).status_code == 409
    assert owner.venue.calls == calls


def test_concurrent_operations_lock_survives_http_worker_and_rejects_second_process(demo_browser):
    owner = demo_browser
    configure(owner)
    connect(owner)
    service = owner.client.app.state.testnet_execution
    with service.session(routes.scope(owner.user)):
        result = owner.client.get(BASE)
        assert result.status_code == 409 and result.json()["reason_code"] == "TESTNET_OPERATION_IN_PROGRESS"
        with pytest.raises(legacy.Halt, match="IN_PROGRESS"):
            with DemoExecution(service.root).session(routes.scope(owner.user)):
                pytest.fail("A second engine must not enter")
    assert owner.venue.calls == []


@pytest.mark.asyncio
async def test_disconnecting_request_keeps_lock_until_thread_completion(tmp_path):
    started, finish = Event(), Event()
    service = DemoExecution(tmp_path/"private")
    scope = str(uuid4())+":"+str(uuid4())
    def slow_operation():
        started.set()
        assert finish.wait(timeout=3)
    async def request():
        with service.session(scope):
            await routes.threaded(slow_operation)
    task = asyncio.create_task(request())
    await asyncio.to_thread(started.wait, 2)
    task.cancel()
    await asyncio.sleep(0)
    with pytest.raises(legacy.Halt, match="IN_PROGRESS"):
        with service.session(scope):
            pytest.fail("Thread is still executing")
    finish.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    with service.session(scope):
        pass


def test_idempotency_payload_conflict_never_submits_other_action(demo_browser):
    owner = demo_browser
    configure(owner)
    connect(owner)
    request_id = str(uuid4())
    assert action(owner, "preflight", request_id=request_id).status_code == 200
    calls = list(owner.venue.calls)
    result = action(owner, "entry", request_id=request_id)
    assert result.status_code == 409 and result.json()["reason_code"] == "TESTNET_REQUEST_ID_CONFLICT"
    assert owner.venue.calls == calls


def test_daily_loss_latch_survives_reconfiguration_and_recovered_equity(demo_browser):
    owner = demo_browser
    configure(owner)
    connect(owner)
    action(owner, "dry-run")
    service = owner.client.app.state.testnet_execution
    with service.session(routes.scope(owner.user)) as session:
        state = session.state()
        state["max_loss_hit"] = True
        legacy.save_state(session.state_path, state)
    assert configure(owner, daily_loss_pct="3").status_code == 409
    assert configure(owner, daily_loss_pct="1").status_code == 200
    result = action(owner, "entry")
    assert result.json()["status"] == "REJECTED"
    assert "DAILY_LOSS_ALREADY_HIT" == result.json()["reason"]
    assert not owner.venue.mutations


def test_uncertain_entry_recovery_verifies_signed_fills_without_resending(demo_browser):
    owner = demo_browser
    configure(owner)
    connect(owner)
    owner.venue.lost_entry_ack = True
    result = action(owner, "entry")
    assert result.json()["status"] == "UNCERTAIN"
    pending = owner.client.get(BASE).json()["pending_order"]
    mutations = list(owner.venue.mutations)
    assert action(owner, "recover", position_id="HK1"+"0"*24).json()["status"] == "REJECTED"
    recovered = action(owner, "recover", position_id=pending["id"])
    assert recovered.json()["status"] == "CONFIRMED", recovered.text
    view = owner.client.get(BASE).json()
    assert not view["halted"] and not view["pending_order"] and view["active_position"]
    assert owner.venue.mutations == mutations
    assert action(owner, "exit", position_id=view["active_position"]["id"]).json()["status"] == "CONFIRMED"


def test_stop_must_be_actually_active_before_a_buy_is_allowed(demo_browser):
    owner = demo_browser
    configure(owner)
    connect(owner)
    original = owner.venue.read
    def canceled_stop(path, params):
        if path == "/fapi/v1/algoOrder" and not owner.venue.quantity:
            owner.venue.stop["algoStatus"] = "CANCELED"
        return original(path, params)
    owner.venue.read = canceled_stop
    receipt = action(owner, "entry").json()
    assert receipt["status"] == "UNCERTAIN" and receipt["reason"] == "STOP_NOT_PROVEN_PROTECTIVE"
    assert owner.venue.mutations == ["PROTECTIVE_STOP"]
    assert owner.venue.quantity == 0 and not owner.venue.orders


def test_stop_trigger_cannot_be_moved_outside_the_persisted_risk_plan(demo_browser):
    owner = demo_browser
    configure(owner)
    connect(owner)
    action(owner, "entry")
    action(owner, "reconcile")
    owner.venue.stop["triggerPrice"] = "1"
    result = action(owner, "inspect").json()
    assert result["status"] == "REJECTED" and result["reason"] == "STOP_TRIGGER_CHANGED_FROM_PLAN"


def test_actual_fees_and_execution_buffers_reduce_quantity_to_risk_budget(demo_browser):
    from decimal import Decimal
    owner = demo_browser
    configure(owner, max_exposure_pct="100")
    connect(owner)
    assert action(owner, "entry").json()["status"] == "CONFIRMED"
    service = owner.client.app.state.testnet_execution
    with service.session(routes.scope(owner.user)) as session:
        state = session.state()
    intent = state["pending_order"]
    unit_risk = owner.venue.mark-Decimal(intent["stop_price"])+owner.venue.mark*Decimal(intent["cost_rate"])
    assert Decimal(intent["quantity"])*unit_risk <= Decimal("5")
    assert Decimal(intent["cost_rate"]) == Decimal("0.004")
    assert (Decimal(intent["quantity"])+Decimal(".001"))*unit_risk > Decimal("5")
    assert state["pending_order"]["quantity"] == str(owner.venue.quantity)


def test_private_file_permission_failure_blocks_before_exchange(demo_browser):
    owner = demo_browser
    configure(owner)
    connect(owner)
    service = owner.client.app.state.testnet_execution
    with service.session(routes.scope(owner.user)) as session:
        session.config_path.chmod(0o644)
    # The helper cannot GET the now-invalid config, so supply the saved revision.
    result = owner.client.get(BASE)
    assert result.status_code == 409 and result.json()["reason_code"] == "PRIVATE_FILE_PERMISSIONS"
    assert not owner.venue.calls


def test_sizing_rejection_never_creates_phantom_pending_order_or_consumes_signal(demo_browser):
    owner = demo_browser
    configure(owner, max_exposure_pct="0.01")
    connect(owner)
    denied = action(owner, "entry").json()
    assert denied["status"] == "REJECTED" and denied["reason"] == "ORDER_BELOW_EXCHANGE_MINIMUM"
    view = owner.client.get(BASE).json()
    assert not view["pending_order"] and not view["halted"]
    assert view["opening_equity"] == "1000" and not owner.venue.mutations
    assert configure(owner, max_exposure_pct="10").status_code == 200
    # A valid policy can now use that very same verified candle.
    assert action(owner, "entry").json()["status"] == "CONFIRMED"
    assert owner.venue.mutations == ["PROTECTIVE_STOP", "ENTRY_FILLED"]
