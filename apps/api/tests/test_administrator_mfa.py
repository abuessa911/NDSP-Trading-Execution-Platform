"""Deterministic safeguards only; acceptance requires actual Keycloak/TOTP."""
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from nex_api.administrator_mfa import POLICY, assurance, enforce
from nex_api.config import Settings

ISSUER = "https://localhost:18443/oidc/realms/nex-m1-test"


def cfg(**extra):
    values = dict(environment="test", oidc_browser_login_enabled=True,
                  oidc_issuer=ISSUER, oidc_audience="nex-m1-browser",
                  oidc_jwks_url=ISSUER + "/protocol/openid-connect/certs",
                  oidc_client_id="nex-m1-browser",
                  oidc_redirect_uri="https://localhost:18443/api/v1/auth/callback",
                  oidc_post_logout_redirect_uri="https://localhost:18443/",
                  secret_provider="file", oidc_admin_mfa_policy=POLICY,
                  oidc_admin_mfa_client_id="nex-m1-admin")
    return Settings(_env_file=None, **(values | extra))


@pytest.mark.parametrize("claims", [
    {}, {"amr": ["mfa"], "auth_time": time.time()},
    {"amr": ["pwd"], "auth_time": time.time()},
    {"amr": ["otp"], "auth_time": time.time()},
    {"amr": ["pwd", "otp"], "auth_time": True},
    {"amr": ["pwd", "otp"], "auth_time": time.time() + 90},
    {"amr": ["pwd", "otp"], "auth_time": time.time() - 1000},
])
def test_reject_inadequate_assurance(claims):
    with pytest.raises(HTTPException) as failure:
        assurance(cfg(), claims)
    assert failure.value.detail["reason_code"] == "MFA_NOT_VALID"


@pytest.mark.parametrize("extra", [
    {"environment": "production"},
    {"oidc_issuer": "https://other.example.test/realm"},
    {"oidc_admin_mfa_policy": "arbitrary-trusted-string"},
    {"oidc_admin_mfa_client_id": "nex-m1-browser"},
    {"oidc_admin_mfa_max_age": 0},
])
def test_unapproved_provider_policy_fails_configuration(extra):
    with pytest.raises(ValidationError):
        cfg(**extra)


def fixture():
    settings = cfg()
    data = {"issuer": ISSUER, "subject": "deterministic-test-only",
            "access_token": "not-a-real-token",
            "mfa": assurance(settings, {"amr": ["pwd", "otp"], "auth_time": time.time()})}
    provider = SimpleNamespace(introspect=AsyncMock(return_value={
        "active": True, "client_id": "nex-m1-admin", "sub": data["subject"],
    }))
    state = SimpleNamespace(settings=settings,
                            browser_provider=SimpleNamespace(administrator=lambda: provider))
    request = SimpleNamespace(app=SimpleNamespace(state=state), state=SimpleNamespace())
    return request, data, provider


@pytest.mark.asyncio
async def test_trusted_assurance_requires_live_matching_provider_session():
    request, data, provider = fixture()
    await enforce(request, data)
    assert request.state.administrator_mfa_verified is True
    provider.introspect.assert_awaited_once()


@pytest.mark.parametrize("live", [
    {"active": False},
    {"active": True, "client_id": "different-client", "sub": "deterministic-test-only"},
    {"active": True, "client_id": "nex-m1-admin", "sub": "different-subject"},
])
@pytest.mark.asyncio
async def test_revocation_identity_and_client_mismatch_fail_closed(live):
    request, data, provider = fixture()
    provider.introspect.return_value = live
    with pytest.raises(HTTPException) as failure:
        await enforce(request, data)
    assert failure.value.detail["reason_code"] == "MFA_REVOKED"


@pytest.mark.asyncio
async def test_expired_assurance_never_calls_provider():
    request, data, provider = fixture()
    data["mfa"]["expires_at"] = time.time() - 1
    with pytest.raises(HTTPException) as failure:
        await enforce(request, data)
    assert failure.value.detail["reason_code"] == "MFA_EXPIRED"
    provider.introspect.assert_not_awaited()


@pytest.mark.asyncio
async def test_arbitrary_client_role_or_mfa_boolean_is_not_assurance():
    request, data, provider = fixture()
    data["mfa"] = {"verified": True, "amr": ["mfa"], "role": "SUPER_ADMIN"}
    with pytest.raises(HTTPException) as failure:
        await enforce(request, data)
    assert failure.value.detail["reason_code"] == "MFA_REQUIRED"
    provider.introspect.assert_not_awaited()
