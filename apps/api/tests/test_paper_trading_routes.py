from uuid import UUID, uuid4

import pytest
from test_browser_auth import ORIGIN
from test_hunter_workspace import (apply, workspace_browser as workspace_browser,
    redis_socket as redis_socket, browser as browser)
from test_paper_broker import batch, NOW, POLICY

from nex_api.paper_broker import PaperBroker
from nex_api.routes import paper_trading as routes
from nex_api.binance_closed_candles import MarketDataUnavailable

@pytest.fixture
def paper_browser(workspace_browser, tmp_path, monkeypatch):  # noqa: F811 - pytest fixture injection
    owner = workspace_browser
    owner.user.role = "OPERATOR"
    owner.client.app.state.paper_broker = PaperBroker(tmp_path/"paper"/"ledger.db", clock=lambda: NOW)
    assert apply(owner).status_code == 200
    # Set the shared mode to MANUAL while retaining the other confirmed fields.
    csrf = owner.client.get("/api/v1/auth/session").json()["csrf_token"]
    selection = owner.client.get("/api/v1/trading/profile/workspace").json()
    for key in ("persisted", "execution_authorized", "ndsp_contract_bound"):
        selection.pop(key)
    selection["execution_method"] = "MANUAL"
    assert owner.client.put("/api/v1/trading/profile/workspace", json=selection,
        headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf}).status_code == 200
    async def candles(**kwargs):
        from dataclasses import replace
        original = batch()
        return replace(original, symbol=kwargs["symbol"], interval=kwargs["interval"],
            candles=tuple(replace(row, symbol=kwargs["symbol"], interval=kwargs["interval"])
                          for row in original.candles))
    # Use the supported BTC/5m market to preserve genuine candle boundaries.
    selection.update(symbol="BTCUSDT", interval="5m")
    assert owner.client.put("/api/v1/trading/profile/workspace", json=selection,
        headers={"Origin": ORIGIN, "X-NEX-CSRF": csrf}).status_code == 200
    monkeypatch.setattr(routes, "fetch_closed_candles", candles)
    return owner

def headers(owner):
    return {"Origin": ORIGIN, "X-NEX-CSRF": owner.client.get("/api/v1/auth/session").json()["csrf_token"]}

def setup(owner):
    return owner.client.put("/api/v1/trading/paper/account", headers=headers(owner),
        json={"initial_equity": "1000", "strategy_id": "trend-ladder", "policy": POLICY})

def order(owner, **overrides):
    return owner.client.post("/api/v1/trading/paper/orders", headers=headers(owner),
        json={"request_id": str(uuid4()), "action": "OPEN", "side": "LONG", "quantity": "1"} | overrides)

def test_no_virtual_money_or_history_is_invented_before_setup(paper_browser):
    result = paper_browser.client.get("/api/v1/trading/paper")
    assert result.status_code == 200
    assert result.json() == {"mode": "PAPER", "configured": False, "real_orders_enabled": False,
                             "position": None, "orders": [], "total_orders": 0}

def test_configure_trade_view_and_idempotent_close_use_real_server_ledger(paper_browser):
    owner = paper_browser
    assert setup(owner).status_code == 200
    opened = order(owner)
    assert opened.status_code == 200 and opened.json()["status"] == "FILLED_SIMULATED"
    result = owner.client.get("/api/v1/trading/paper").json()
    assert result["position"]["side"] == "LONG" and result["total_orders"] == 1
    key = str(uuid4())
    closed = order(owner, action="CLOSE", request_id=key, position_id=result["position"]["id"])
    assert closed.status_code == 200
    assert order(owner, action="CLOSE", request_id=key, position_id=result["position"]["id"]).json() == closed.json()
    result = owner.client.get("/api/v1/trading/paper").json()
    assert result["position"] is None and result["total_orders"] == 2
    assert result["real_orders_enabled"] is False

def test_account_scope_cannot_be_supplied_or_read_by_other_user(paper_browser):
    owner = paper_browser
    assert setup(owner).status_code == 200
    assert order(owner).status_code == 200
    denied = order(owner, tenant_id=str(uuid4()))
    assert denied.status_code == 422
    owner.user.id = UUID(int=1234)
    result = owner.client.get("/api/v1/trading/paper").json()
    assert result["configured"] is False and result["orders"] == []

@pytest.mark.parametrize("route,method", [
    ("/account", "put"), ("/orders", "post"), ("/start", "post"), ("/stop", "post"),
])
def test_every_paper_mutation_requires_csrf(paper_browser, route, method):
    body = ({"initial_equity": "1000", "strategy_id": "trend-ladder", "policy": POLICY}
            if route == "/account" else
            {"request_id": str(uuid4()), "action": "OPEN", "side": "LONG", "quantity": "1"}
            if route == "/orders" else None)
    result = getattr(paper_browser.client, method)("/api/v1/trading/paper"+route,
        json=body, headers={"Origin": ORIGIN, "X-NEX-CSRF": "wrong"})
    assert result.status_code == 403

def test_regular_user_cannot_configure_virtual_operator_engine(paper_browser):
    owner = paper_browser
    owner.user.role = "USER"
    assert setup(owner).status_code == 403

def test_manual_orders_blocked_after_workspace_change(paper_browser):
    owner = paper_browser
    assert setup(owner).status_code == 200
    selection = owner.client.get("/api/v1/trading/profile/workspace").json()
    for key in ("persisted", "execution_authorized", "ndsp_contract_bound"):
        selection.pop(key)
    selection["symbol"] = "ETHUSDT"
    assert owner.client.put("/api/v1/trading/profile/workspace", json=selection,
        headers=headers(owner)).status_code == 200
    result = order(owner)
    assert result.status_code == 409 and result.json()["reason_code"] == "PAPER_WORKSPACE_CHANGED"

def test_market_failure_hides_equity_without_fabricating_a_quote(paper_browser, monkeypatch):
    owner = paper_browser
    assert setup(owner).status_code == 200
    assert order(owner).status_code == 200
    async def unavailable(**kwargs):
        raise MarketDataUnavailable("FIXTURE_NO_FEED")
    monkeypatch.setattr(routes, "fetch_closed_candles", unavailable)
    result = owner.client.get("/api/v1/trading/paper")
    assert result.status_code == 200
    assert result.json()["equity"] is None
    assert result.json()["quote_available"] is False
    assert result.json()["position"] is not None

def test_unconfigured_or_unverified_mode_cannot_start_worker(paper_browser):
    owner = paper_browser
    assert setup(owner).status_code == 200
    # MANUAL cannot start the automatic loop, even with a mocked valid strategy feed.
    result = owner.client.post("/api/v1/trading/paper/start", headers=headers(owner))
    assert result.status_code in (409, 503)
    assert owner.client.get("/api/v1/trading/paper").json()["running"] is False

def automatic(owner):
    selected = owner.client.get("/api/v1/trading/profile/workspace").json()
    for field in ("persisted", "execution_authorized", "ndsp_contract_bound"):
        selected.pop(field)
    selected["execution_method"] = "AUTOMATIC"
    assert owner.client.put("/api/v1/trading/profile/workspace", json=selected,
                            headers=headers(owner)).status_code == 200
    assert setup(owner).status_code == 200
    return selected


def test_workspace_confirmation_stops_durable_automatic_entries(paper_browser, monkeypatch):
    owner = paper_browser
    selected = automatic(owner)
    monkeypatch.setattr(routes, "evaluate", lambda *args: "NEUTRAL")
    assert owner.client.post("/api/v1/trading/paper/start", headers=headers(owner)).json()["running"]
    selected["symbol"] = "ETHUSDT"
    assert owner.client.put("/api/v1/trading/profile/workspace", json=selected,
                            headers=headers(owner)).status_code == 200
    engine = owner.client.app.state.paper_broker
    assert engine.metadata(routes.scope(owner.user))["running"] is False


def test_automatic_start_rolls_forward_yesterdays_daily_latch(paper_browser, monkeypatch):
    from datetime import date, timedelta
    owner = paper_browser
    automatic(owner)
    monkeypatch.setattr(routes, "evaluate", lambda *args: "NEUTRAL")
    engine = owner.client.app.state.paper_broker
    identifier = routes.scope(owner.user)
    with engine.transaction() as db:
        state = engine._load(db, identifier)
        state.update(day=str(date.fromisoformat(state["day"])-timedelta(days=1)), daily_hit=True)
        engine._save(db, identifier, state)
    result = owner.client.post("/api/v1/trading/paper/start", headers=headers(owner))
    assert result.status_code == 200 and result.json()["running"]
    assert engine.metadata(identifier)["daily_hit"] is False


def test_unauthenticated_paper_reads_and_writes_are_rejected(paper_browser):
    owner = paper_browser
    owner.client.cookies.clear()
    assert owner.client.get("/api/v1/trading/paper").status_code == 401
    assert owner.client.post("/api/v1/trading/paper/stop", headers={"Origin": ORIGIN}).status_code == 401


def test_legacy_decision_profile_confirmation_also_stops_paper_entries(paper_browser, monkeypatch):
    owner = paper_browser
    automatic(owner)
    monkeypatch.setattr(routes, "evaluate", lambda *args: "NEUTRAL")
    assert owner.client.post("/api/v1/trading/paper/start", headers=headers(owner)).json()["running"]
    result = owner.client.put("/api/v1/trading/profile", json={"mode": "INVESTMENT"}, headers=headers(owner))
    assert result.status_code == 200 and result.json()["mode"] == "INVESTMENT"
    assert owner.client.app.state.paper_broker.metadata(routes.scope(owner.user))["running"] is False
