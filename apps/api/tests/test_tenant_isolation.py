"""PostgreSQL behavior is tested in test_postgres_m1, not SQLite substitutes."""
from fastapi.testclient import TestClient

from nex_api.config import Settings
from nex_api.main import create_app


def test_audit_persistence_unavailable_is_explicit() -> None:
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/api/v1/me")
    assert response.status_code == 503
    assert response.json()["reason_code"] == "AUDIT_PERSISTENCE_UNAVAILABLE"