"""Only approved, actually enforced provider assurance can unlock admin sessions."""
import time
import math
from typing import Any

from fastapi import Request

from nex_api.browser_provider import ProviderFailure
from nex_api.config import Settings

POLICY = "keycloak-password-totp-v1"


def assurance(settings: Settings, claims: dict[str, Any]) -> dict[str, Any]:
    # Called only after ID-token signature/issuer/admin-audience/nonce validation.
    from nex_api.dependencies import failure
    methods = claims.get("amr")
    authenticated = claims.get("auth_time")
    now = time.time()
    if (settings.oidc_admin_mfa_policy != POLICY
            or not isinstance(methods, list) or not all(isinstance(m, str) for m in methods)
            or not {"pwd", "otp"}.issubset(methods)
            or isinstance(authenticated, bool) or not isinstance(authenticated, (int, float))
            or not math.isfinite(authenticated)
            or authenticated > now + 30
            or now - authenticated > settings.oidc_admin_mfa_max_age):
        raise failure("MFA_NOT_VALID", "Fresh provider password and TOTP assurance required.")
    return {"policy": POLICY, "client": settings.oidc_admin_mfa_client_id,
            "auth_time": authenticated, "methods": ["pwd", "otp"],
            "expires_at": authenticated + settings.oidc_admin_mfa_max_age}


async def enforce(request: Request, data: dict[str, Any] | None,
                  opaque: str | None = None) -> None:
    from nex_api.dependencies import failure
    settings = request.app.state.settings
    if settings.oidc_admin_mfa_policy != POLICY:
        raise failure("MFA_EXTERNAL_REQUIREMENT", "Verified administrative MFA is required.")
    proof = (data or {}).get("mfa")
    if (not isinstance(proof, dict) or proof.get("policy") != POLICY
            or proof.get("client") != settings.oidc_admin_mfa_client_id
            or proof.get("methods") != ["pwd", "otp"]
            or (data or {}).get("issuer") != settings.oidc_issuer):
        raise failure("MFA_REQUIRED", "Verified administrative MFA is required.")
    assert data is not None
    now = time.time()
    if (proof.get("auth_time", now + 31) > now + 30
            or min(proof.get("expires_at", 0),
                   proof.get("auth_time", 0) + settings.oidc_admin_mfa_max_age) <= now):
        raise failure("MFA_EXPIRED", "Fresh administrator authentication required.")
    try:
        provider = request.app.state.browser_provider.administrator()
        live = await provider.introspect(data["access_token"])
    except (ProviderFailure, KeyError):
        raise failure("MFA_PROVIDER_UNAVAILABLE", "Administrator session verification unavailable.", 503)
    if (live.get("active") is not True
            or live.get("client_id") != settings.oidc_admin_mfa_client_id
            or live.get("sub") != data["subject"]):
        if opaque:
            await request.app.state.browser_sessions.take("session", opaque)
            from nex_api.routes.auth import event
            await event(request, "SESSION_REVOKED")
        raise failure("MFA_REVOKED", "Administrator provider session is no longer active.")
    request.state.administrator_mfa_verified = True
