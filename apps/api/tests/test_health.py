from fastapi.testclient import TestClient

from nex_api.config import Settings
from nex_api.main import create_app


def test_liveness_is_available_without_external_services() -> None:
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/api/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_fails_when_required_services_are_not_configured() -> None:
    with TestClient(create_app(Settings(_env_file=None))) as client:
        response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["components"] == {
        "database": "unavailable",
        "redis": "unavailable",
        "oidc": "not_configured",
    }