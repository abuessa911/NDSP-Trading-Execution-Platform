from unittest.mock import AsyncMock
from uuid import UUID

from fastapi.testclient import TestClient

from nex_api.config import Settings
from nex_api.dependencies import get_administrator
from nex_api.main import create_app
from nex_api.models import User


def test_administrator_operations_reports_only_authoritative_or_absent_state(monkeypatch):
    user = User(
        id=UUID(int=2), tenant_id=UUID(int=3), email="admin@example.test",
        role="ADMIN", status="active", issuer="https://idp.example.test", subject="admin",
    )
    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[get_administrator] = lambda: user
    monkeypatch.setattr("nex_api.main.persist_audit", AsyncMock())
    with TestClient(app) as client:
        response = client.get("/api/v1/admin/operations")
        assert response.status_code == 200
        assert response.json() == {
            "tenant_id": str(user.tenant_id),
            "entitlements": {"live_trading": False},
            "subscription": {
                "status": "NOT_IMPLEMENTED", "reason_code": "BILLING_NOT_IMPLEMENTED",
            },
            "trading_safety": {
                "trading_mode": "paper", "live_trading_enabled": False,
                "global_kill_switch": True, "binance_allow_withdraw": False,
            },
            "exchange": {
                "status": "NOT_CONFIGURED",
                "reason_code": "EXCHANGE_CONNECTOR_NOT_CONFIGURED",
            },
            "ndsp_connector": {
                "status": "NOT_CONFIGURED", "reason_code": "NDSP_CONNECTOR_NOT_CONFIGURED",
            },
            "worker_queues": {
                "status": "NOT_IMPLEMENTED", "reason_code": "M1_DATA_SOURCE_NOT_IMPLEMENTED",
            },
            "notifications": {
                "status": "NOT_IMPLEMENTED", "reason_code": "M1_DATA_SOURCE_NOT_IMPLEMENTED",
            },
            "incidents": {
                "status": "NOT_IMPLEMENTED", "reason_code": "M1_DATA_SOURCE_NOT_IMPLEMENTED",
            },
        }
        assert client.post("/api/v1/admin/operations").status_code == 405


def test_administrator_audit_returns_tenant_scoped_events_on_both_routes(monkeypatch):
    from datetime import datetime, timezone
    from types import SimpleNamespace
    from nex_api.dependencies import get_session

    user = User(id=UUID(int=2), tenant_id=UUID(int=3), email="admin@example.test",
                role="ADMIN", status="active", issuer="https://idp.example.test", subject="admin")
    event = SimpleNamespace(
        id=UUID(int=10), tenant_id=user.tenant_id, correlation_id=UUID(int=11),
        actor_type="ADMIN", actor_id="admin", action="TEST_EVENT", object_type="test",
        object_id=None, outcome="SUCCESS", reason_code=None, source_ip_hash=None,
        user_agent_hash=None, before_hash=None, after_hash=None, metadata_json={},
        created_at=datetime.now(timezone.utc),
    )
    queries = []
    async def execute(query):
        queries.append(query)
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [event]))
    async def database():
        yield SimpleNamespace(execute=execute)
    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[get_administrator] = lambda: user
    app.dependency_overrides[get_session] = database
    monkeypatch.setattr("nex_api.main.persist_audit", AsyncMock())
    with TestClient(app) as client:
        for route in ("/api/v1/admin/audit", "/admin/v1/audit"):
            response = client.get(route)
            assert response.status_code == 200
            assert response.json()[0]["action"] == "TEST_EVENT"
            assert response.json()[0]["tenant_id"] == str(user.tenant_id)
    assert len(queries) == 2
    for query in queries:
        assert str(user.tenant_id) in [str(value) for value in query.compile().params.values()]
        assert query.compile().params["param_1"] == 100
