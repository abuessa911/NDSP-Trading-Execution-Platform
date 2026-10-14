"""M2-A internal route tests: never connect to live Binance in CI."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from nex_api.binance_closed_candles import (
    ClosedCandleBatch, MarketDataUnavailable, _parse_rows,
)
from nex_api.config import Settings
from nex_api.dependencies import get_administrator, get_provisioned_user
from nex_api.main import create_app
from nex_api.market_data_internal import GLOBAL_BUDGET, TENANT_BUDGET
from nex_api.models import User


class IsolatedRedis:
    def __init__(self):
        self.values: dict[str, str] = {}
        self.quotas: dict[str, int] = {}
        self.unavailable = False

    async def eval(self, script, count, tenant_key, global_key, tenant_budget, global_budget, ttl):
        assert count == 2 and "INCR" in script and ttl == 60
        if self.unavailable:
            raise OSError("disposable fixture down")
        used_tenant = self.quotas.get(tenant_key, 0)
        used_global = self.quotas.get(global_key, 0)
        if used_tenant >= tenant_budget or used_global >= global_budget:
            return 0
        self.quotas[tenant_key] = used_tenant + 1
        self.quotas[global_key] = used_global + 1
        return 1

    async def set(self, key, value, ex):
        if self.unavailable:
            raise OSError("disposable fixture down")
        assert ex == 900
        self.values[key] = value

    async def aclose(self):
        return None

    async def get(self, key):
        if self.unavailable:
            raise OSError("disposable fixture down")
        return self.values.get(key)


START = 1_796_000_100_000
DURATION = 300_000
ALIGNED = START // DURATION * DURATION
SERVER = ALIGNED + 2 * DURATION + 5_000
USER = User(
    id=UUID(int=82), tenant_id=UUID(int=83), role="ADMIN",
    email="m2a@example.test", status="active",
    issuer="https://issuer.example.test", subject="m2a",
)
PATH = "/api/v1/admin/market-data/closed-candles"
STATUS = "/api/v1/admin/market-data/observation"
PARAMS = {"market": "spot", "symbol": "BTCUSDT", "interval": "5m", "limit": 5}
STATUS_PARAMS = {k: v for k, v in PARAMS.items() if k != "limit"}


def valid_batch():
    rows = [
        [ALIGNED, "100", "104", "99", "101", "2", ALIGNED + DURATION - 1],
        [ALIGNED + DURATION, "101", "105", "100", "102", "3",
         ALIGNED + 2 * DURATION - 1],
    ]
    candles = _parse_rows(rows, "spot", "BTCUSDT", "5m", SERVER)
    return ClosedCandleBatch("spot", "BTCUSDT", "5m", SERVER, candles)


@pytest.fixture
def client(monkeypatch):
    app = create_app(Settings(_env_file=None, environment="test", m2a_public_market_enabled=True))
    app.dependency_overrides[get_administrator] = lambda: USER
    monkeypatch.setattr("nex_api.main.persist_audit", AsyncMock())
    redis = IsolatedRedis()
    read = AsyncMock(return_value=valid_batch())
    with TestClient(app) as http:
        app.state.redis = redis
        app.state.market_data_reader = read
        yield SimpleNamespace(http=http, redis=redis, read=read, app=app)


def test_read_only_candles_have_decimals_as_strings_and_no_open_bar(client):
    response = client.http.get(PATH, params=PARAMS)
    assert response.status_code == 200, response.text
    view = response.json()
    assert view["status"] == "READ_ONLY_OK"
    assert view["tenant_id"] == str(USER.tenant_id)
    assert view["orders_sent"] == 0
    assert len(view["candles"]) == 2
    assert view["candles"][-1]["close"] == "102"
    assert view["candles"][-1]["close_time_ms"] < view["server_time_ms"]
    client.read.assert_awaited_once_with(
        market="spot", symbol="BTCUSDT", interval="5m", limit=5,
    )
    assert client.http.post(PATH, params=PARAMS).status_code == 405
    assert client.http.delete(PATH, params=PARAMS).status_code == 405


def test_last_observation_reports_status_without_unbounded_history(client):
    empty = client.http.get(STATUS, params=STATUS_PARAMS)
    assert empty.status_code == 200
    assert empty.json()["status"] == "NOT_OBSERVED"
    assert client.http.get(PATH, params=PARAMS).status_code == 200
    after = client.http.get(STATUS, params=STATUS_PARAMS)
    assert after.status_code == 200
    assert after.json()["status"] == "READ_ONLY_OK"
    assert after.json()["latest_closed_ms"] == ALIGNED + 2 * DURATION - 1


def test_exchange_failure_fails_closed_and_is_observable(client):
    client.read.side_effect = MarketDataUnavailable("EXCHANGE_RATE_LIMITED")
    response = client.http.get(PATH, params=PARAMS)
    assert response.status_code == 503
    assert response.json()["reason_code"] == "EXCHANGE_RATE_LIMITED"
    status = client.http.get(STATUS, params=STATUS_PARAMS)
    assert status.json()["status"] == "BLOCKED"
    assert status.json()["reason_code"] == "EXCHANGE_RATE_LIMITED"
    assert "exchange response" not in response.text.lower()


def test_shared_redis_budget_prevents_additional_exchange_calls(client):
    for _ in range(TENANT_BUDGET):
        assert client.http.get(PATH, params=PARAMS).status_code == 200
    count = client.read.await_count
    response = client.http.get(PATH, params=PARAMS)
    assert response.status_code == 429
    assert response.json()["reason_code"] == "M2A_RATE_BUDGET_EXHAUSTED"
    assert client.read.await_count == count
    assert GLOBAL_BUDGET > TENANT_BUDGET
    assert len(client.redis.quotas) == 2


def test_redis_outage_and_unavailable_monitoring_block_data(client):
    client.redis.unavailable = True
    response = client.http.get(PATH, params=PARAMS)
    assert response.status_code == 503
    assert response.json()["reason_code"] == "M2A_REDIS_UNAVAILABLE"
    client.read.assert_not_awaited()
    assert client.http.get(STATUS, params=STATUS_PARAMS).status_code == 503


@pytest.mark.parametrize("overrides", [
    {"market": "coinm_futures"}, {"symbol": "BTCUSDT/../order"},
    {"interval": "1m"}, {"limit": 31}, {"limit": 1},
])
def test_invalid_inputs_never_read_the_exchange(client, overrides):
    bad = {**PARAMS, **overrides}
    response = client.http.get(PATH, params=bad)
    assert response.status_code == 422
    client.read.assert_not_awaited()
    assert not client.redis.quotas


def test_tenant_observations_are_strictly_isolated(client):
    assert client.http.get(PATH, params=PARAMS).status_code == 200
    assert client.http.get(STATUS, params=STATUS_PARAMS).json()["status"] == "READ_ONLY_OK"
    other = User(
        id=UUID(int=122), tenant_id=UUID(int=123), role="ADMIN",
        email="other@example.test", status="active",
        issuer="https://issuer.example.test", subject="other",
    )
    client.app.dependency_overrides[get_administrator] = lambda: other
    response = client.http.get(STATUS, params=STATUS_PARAMS)
    assert response.status_code == 200
    assert response.json()["status"] == "NOT_OBSERVED"


def test_default_off_blocks_network_and_production_can_never_enable(monkeypatch):
    with pytest.raises(ValidationError, match="M2A market API is test-only"):
        Settings(_env_file=None, environment="production", m2a_public_market_enabled=True)
    app = create_app(Settings(_env_file=None, environment="test"))
    app.dependency_overrides[get_administrator] = lambda: USER
    monkeypatch.setattr("nex_api.main.persist_audit", AsyncMock())
    read = AsyncMock(return_value=valid_batch())
    with TestClient(app) as http:
        app.state.market_data_reader = read
        response = http.get(PATH, params=PARAMS)
        assert response.status_code == 503
        assert response.json()["reason_code"] == "M2A_INTERNAL_MARKET_DISABLED"
    read.assert_not_awaited()


def test_anonymous_client_is_denied_before_exchange(monkeypatch):
    app = create_app(Settings(_env_file=None, environment="test", m2a_public_market_enabled=True))
    monkeypatch.setattr("nex_api.main.persist_audit", AsyncMock())
    read = AsyncMock(return_value=valid_batch())
    with TestClient(app) as http:
        app.state.market_data_reader = read
        response = http.get(PATH, params=PARAMS)
    assert response.status_code == 401
    read.assert_not_awaited()


def test_monitoring_storage_outage_never_reports_success(client):
    client.redis.set = AsyncMock(side_effect=OSError("monitoring fixture lost"))
    response = client.http.get(PATH, params=PARAMS)
    assert response.status_code == 503
    assert response.json()["reason_code"] == "M2A_OBSERVABILITY_UNAVAILABLE"



@pytest.mark.parametrize("role", ["USER", "OPERATOR"])
def test_non_admin_role_is_denied_using_real_admin_dependency(monkeypatch, role):
    user = User(
        id=UUID(int=242), tenant_id=UUID(int=243), role=role,
        email="viewer@example.test", status="active",
        issuer="https://issuer.example.test", subject="viewer",
    )
    app = create_app(Settings(_env_file=None, environment="test",
                              m2a_public_market_enabled=True))
    app.dependency_overrides[get_provisioned_user] = lambda: user
    monkeypatch.setattr("nex_api.main.persist_audit", AsyncMock())
    read = AsyncMock(return_value=valid_batch())
    with TestClient(app) as http:
        app.state.market_data_reader = read
        response = http.get(PATH, params=PARAMS)
    assert response.status_code == 403
    assert response.json()["reason_code"] == "ROLE_NOT_ALLOWED"
    read.assert_not_awaited()


def test_global_shared_rate_budget_across_tenants(client):
    for n in range(GLOBAL_BUDGET):
        current = User(
            id=UUID(int=300 + n), tenant_id=UUID(int=400 + n), role="ADMIN",
            email="isolated@example.test", status="active",
            issuer="https://issuer.example.test", subject=str(n),
        )
        client.app.dependency_overrides[get_administrator] = lambda u=current: u
        assert client.http.get(PATH, params=PARAMS).status_code == 200
    count = client.read.await_count
    other = User(
        id=UUID(int=999), tenant_id=UUID(int=1000), role="ADMIN",
        email="other@example.test", status="active",
        issuer="https://issuer.example.test", subject="other",
    )
    client.app.dependency_overrides[get_administrator] = lambda: other
    assert client.http.get(PATH, params=PARAMS).status_code == 429
    assert client.read.await_count == count
