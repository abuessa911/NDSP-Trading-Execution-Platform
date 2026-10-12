import json
from pathlib import Path

from nex_api.config import Settings
from nex_api.main import create_app


def test_m1_runtime_and_client_input_contract_are_identical():
    contract = json.loads(Path("lib/api-spec/openapi.yaml").read_text())
    assert create_app(Settings(_env_file=None)).openapi() == contract
    assert contract["components"]["securitySchemes"]["NEXSession"]["in"] == "cookie"
    assert set(contract["paths"]) == {
        "/api/health/live", "/api/health/ready", "/api/health/auth", "/api/v1/me",
        "/api/v1/tenants/{tenant_id}/audit-events",
        "/api/v1/auth/login", "/api/v1/auth/logout", "/api/v1/health/summary",
        "/api/v1/auth/callback", "/api/v1/auth/session", "/api/v1/auth/refresh",
        "/admin/v1/system/health", "/admin/v1/audit",
    }