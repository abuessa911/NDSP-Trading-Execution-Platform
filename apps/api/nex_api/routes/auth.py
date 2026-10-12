"""OIDC browser BFF: single-use PKCE transactions and revocable opaque sessions."""
import hashlib
import hmac
import json
import secrets
import time
import asyncio
from typing import Any, Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from nex_api.audit import AuditUnavailable, persist_audit
from nex_api.browser_provider import BrowserProvider, ProviderFailure
from nex_api.browser_sessions import BrowserSessions, COOKIE_PATH, FLOW_COOKIE, SESSION_COOKIE, Record
from nex_api.dependencies import Principal, failure, get_provisioned_user
from nex_api.models import SECURITY_TENANT_ID, User
from nex_api.oidc import OIDCTokenError

router = APIRouter(prefix="/v1/auth", tags=["authentication"])


class LoginResult(BaseModel):
    authorization_url: str


class LogoutResult(BaseModel):
    status: str
    provider_revoked: bool
    logout_url: str | None


class SessionResult(BaseModel):
    authenticated: bool
    user_id: str
    tenant_id: str
    role: str
    csrf_token: str
    administrator_mfa_verified: bool = False


def context(request: Request, action: str) -> tuple[BrowserProvider, BrowserSessions]:
    if not request.app.state.settings.oidc_browser_login_enabled:
        raise failure(f"OIDC_{action}_EXTERNAL_REQUIREMENT",
                      "Provider browser authentication is not configured.", 501)
    provider = request.app.state.browser_provider
    store = request.app.state.browser_sessions
    if not provider or not store:
        raise failure("SYSTEM_DEPENDENCY_UNHEALTHY", "Authentication dependency unavailable.", 503)
    return provider, store


async def event(request: Request, action: str, outcome: str = "SUCCESS",
                reason: str | None = None) -> None:
    user = request.state.audit_user
    await persist_audit(
        request.app.state.session_factory,
        tenant_id=user["tenant_id"] if user else SECURITY_TENANT_ID,
        correlation_id=request.state.correlation_id,
        actor_type=("ADMIN" if user and user["role"] in {"ADMIN", "SUPER_ADMIN"}
                    else "USER" if user else "SYSTEM"),
        actor_id=user["id"] if user else None,
        action=action, object_type="AUTHENTICATION", outcome=outcome, reason_code=reason,
    )


def headers() -> dict[str, str]:
    return {"Cache-Control": "no-store", "Pragma": "no-cache", "Referrer-Policy": "no-referrer"}


def reason(error: HTTPException) -> str:
    return str(error.detail.get("reason_code", "AUTH_NOT_VALID")) \
        if isinstance(error.detail, dict) else "AUTH_NOT_VALID"


def cookie(response: JSONResponse | RedirectResponse, name: str, value: str, ttl: int) -> None:
    response.set_cookie(name, value, max_age=ttl, path=COOKIE_PATH,
                        secure=True, httponly=True, samesite="lax")


def clear(response: JSONResponse | RedirectResponse, name: str) -> None:
    response.delete_cookie(name, path=COOKIE_PATH, secure=True, httponly=True, samesite="lax")


async def rejected(request: Request, action: str, code: str, status: int) -> JSONResponse:
    try:
        await event(request, action, "DENIED" if status < 500 else "FAILED", code)
    except AuditUnavailable:
        code, status = "AUDIT_PERSISTENCE_UNAVAILABLE", 503
    request.state.auth_audit_managed = True
    response = JSONResponse(status_code=status, headers=headers(), content={
        "reason_code": code, "message": "Authentication request rejected.",
        "correlation_id": str(request.state.correlation_id),
    })
    clear(response, FLOW_COOKIE)
    return response


async def callback_rejected(request: Request, action: str, code: str, status: int
                            ) -> RedirectResponse:
    result = await rejected(request, action, code, status)
    # Also remove authorization code/state from browser history after a failure.
    safe_code = json.loads(result.body)["reason_code"]
    response = RedirectResponse(
        request.app.state.settings.oidc_post_logout_redirect_uri + "?auth_error=" + safe_code,
        status_code=303, headers=headers(),
    )
    clear(response, FLOW_COOKIE)
    return response


def same_origin(request: Request) -> None:
    target = urlsplit(request.app.state.settings.oidc_redirect_uri or "")
    if request.headers.get("origin") != f"{target.scheme}://{target.netloc}":
        raise failure("CSRF_NOT_VALID", "Same-origin authentication request required.")


async def local_record(request: Request, store: BrowserSessions) -> tuple[str, Record]:
    opaque = request.cookies.get(SESSION_COOKIE, "")
    record = await store.load("session", opaque)
    if not record or record.data.get("expires_at", 0) <= time.time():
        raise failure("SESSION_REVOKED", "A valid application session is required.", 401)
    return opaque, record


async def authorize(request: Request, data: dict[str, Any]) -> User:
    factory = request.app.state.session_factory
    if factory is None:
        raise failure("SYSTEM_DEPENDENCY_UNHEALTHY", "Database unavailable.", 503)
    async with factory() as session:
        return await get_provisioned_user(
            request, Principal(data["issuer"], data["subject"], data), session
        )


def csrf(request: Request, record: Record) -> None:
    same_origin(request)
    if not hmac.compare_digest(request.headers.get("x-nex-csrf", ""), record.data["csrf"]):
        raise failure("CSRF_NOT_VALID", "A valid CSRF token is required.")


@router.post("/login", operation_id="login", response_model=LoginResult,
             responses={501: {"description": "Real provider configuration required"}})
async def login(request: Request, admin_mfa: Annotated[bool, Query()] = False) -> JSONResponse:
    provider, store = context(request, "LOGIN")
    try:
        same_origin(request)
        if admin_mfa:
            if not request.app.state.settings.oidc_admin_mfa_policy:
                raise failure("MFA_EXTERNAL_REQUIREMENT", "Administrator MFA is not configured.")
            provider = provider.administrator()
        state, binding, nonce, verifier = (secrets.token_urlsafe(48) for _ in range(4))
        url = await provider.authorization(state, nonce, verifier, fresh_mfa=True) if admin_mfa \
            else await provider.authorization(state, nonce, verifier)
        await event(request, "LOGIN_STARTED")
        await store.create("flow", state, {
            "binding": hashlib.sha256(binding.encode()).hexdigest(),
            "nonce": nonce, "verifier": verifier,
            "admin_mfa": admin_mfa,
        }, 300)
        response = JSONResponse({"authorization_url": url}, headers=headers())
        cookie(response, FLOW_COOKIE, binding, 300)
        request.state.auth_audit_managed = True
        return response
    except HTTPException as error:
        return await rejected(request, "LOGIN_DENIED", reason(error), error.status_code)
    except Exception:
        return await rejected(request, "LOGIN_FAILED", "OIDC_PROVIDER_UNAVAILABLE", 503)


@router.get("/callback", operation_id="oidcCallback",
            response_model=None,
            responses={303: {"description": "Clean redirect after validated provider callback"}})
async def callback(request: Request) -> JSONResponse | RedirectResponse:
    provider, store = context(request, "LOGIN")
    tokens: dict[str, Any] = {}
    try:
        state, code = request.query_params.get("state", ""), request.query_params.get("code", "")
        if request.query_params.get("error") or not code or len(code) > 8192:
            raise failure("OIDC_AUTHORIZATION_DENIED", "Authorization response rejected.", 401)
        pending = await store.load("flow", state)
        binding = hashlib.sha256(request.cookies.get(FLOW_COOKIE, "").encode()).hexdigest()
        if not pending or not hmac.compare_digest(pending.data["binding"], binding):
            raise failure("OIDC_STATE_NOT_VALID", "Authorization state rejected.", 401)
        if not await store.take("flow", state, pending):
            raise failure("OIDC_RESPONSE_REPLAYED", "Authorization response already consumed.", 401)
        if pending.data.get("admin_mfa"):
            provider = provider.administrator()
        tokens = await provider.exchange(code, pending.data["verifier"], pending.data["nonce"])
        claims = tokens["claims"]
        identity: dict[str, Any] = {"issuer": claims["iss"], "subject": claims["sub"]}
        mfa = None
        if pending.data.get("admin_mfa"):
            from nex_api.administrator_mfa import assurance
            mfa = assurance(request.app.state.settings, claims)
        identity |= {"mfa": mfa, "admin_mfa": bool(pending.data.get("admin_mfa"))}
        await authorize(request, identity | {"access_token": tokens["access_token"]})
        if request.state.audit_user["role"] in {"ADMIN", "SUPER_ADMIN"}:
            await event(request, "ADMIN_MFA_VERIFIED")
        await event(request, "LOGIN_SUCCESS")
        opaque = secrets.token_urlsafe(48)
        lifetime = request.app.state.settings.nex_session_seconds
        old_session = request.cookies.get(SESSION_COOKIE, "")
        if await store.take("session", old_session):
            await event(request, "SESSION_REVOKED")
        await store.create("session", opaque, identity | {
            "nonce": pending.data["nonce"],
            "user_id": request.state.audit_user["id"],
            "tenant_id": str(request.state.audit_user["tenant_id"]),
            "role": request.state.audit_user["role"],
            "csrf": secrets.token_urlsafe(48), "expires_at": time.time() + lifetime,
            "auth_expires_at": min(float(claims["exp"]), time.time() + int(tokens["expires_in"])),
            "access_token": tokens["access_token"], "refresh_token": tokens.get("refresh_token"),
        }, lifetime)
        response = RedirectResponse(request.app.state.settings.oidc_post_logout_redirect_uri,
                                    status_code=303, headers=headers())
        cookie(response, SESSION_COOKIE, opaque, lifetime)
        clear(response, FLOW_COOKIE)
        request.state.auth_audit_managed = True
        return response
    except HTTPException as error:
        if tokens:
            try:
                await provider.revoke(tokens)
            except ProviderFailure:
                pass
        return await callback_rejected(request, "LOGIN_DENIED", reason(error), error.status_code)
    except OIDCTokenError:
        return await callback_rejected(request, "LOGIN_DENIED", "OIDC_TOKEN_NOT_VALID", 401)
    except Exception:
        if tokens:
            try:
                await provider.revoke(tokens)
            except ProviderFailure:
                pass
        return await callback_rejected(request, "LOGIN_FAILED", "OIDC_EXCHANGE_FAILED", 503)


@router.get("/session", operation_id="getBrowserSession", response_model=SessionResult)
async def session_view(request: Request, user: Annotated[User, Depends(get_provisioned_user)]
                       ) -> dict[str, Any]:
    _, store = context(request, "LOGIN")
    _, record = await local_record(request, store)
    return {"authenticated": True, "user_id": str(user.id), "tenant_id": str(user.tenant_id),
            "role": user.role, "csrf_token": record.data["csrf"],
            "administrator_mfa_verified": bool(
                getattr(request.state, "administrator_mfa_verified", False)
            )}


@router.post("/logout", operation_id="logout", response_model=LogoutResult,
             responses={501: {"description": "Real provider configuration required"}})
async def logout(request: Request) -> JSONResponse:
    provider, store = context(request, "LOGOUT")
    terminated = False
    try:
        opaque, record = await local_record(request, store)
        from uuid import UUID
        request.state.audit_user = {
            "id": record.data["user_id"], "tenant_id": UUID(record.data["tenant_id"]),
            "role": record.data["role"],
        }
        csrf(request, record)
        if record.data.get("admin_mfa"):
            provider = provider.administrator()
        # Terminate first, even if provider or audit subsequently fails.
        if not await store.take("session", opaque):
            raise failure("SESSION_REVOKED", "Session already terminated.", 401)
        terminated = True
        await event(request, "SESSION_REVOKED")
        revoked = await provider.revoke(record.data)
        url = await provider.logout_url()
        await event(request, "LOGOUT_SUCCESS")
        response = JSONResponse({"status": "logged_out", "provider_revoked": revoked,
                                 "logout_url": url}, headers=headers())
        request.state.auth_audit_managed = True
    except HTTPException as error:
        terminated = error.status_code == 401
        response = await rejected(request, "LOGOUT_FAILED",
                                  reason(error), error.status_code)
    except Exception:
        response = await rejected(request, "LOGOUT_FAILED", "OIDC_LOGOUT_FAILED", 503)
    if terminated:
        clear(response, SESSION_COOKIE)
    return response


@router.post("/refresh", operation_id="refreshBrowserSession")
async def refresh(request: Request) -> JSONResponse:
    provider, store = context(request, "LOGIN")
    tokens: dict[str, Any] = {}
    try:
        opaque, record = await local_record(request, store)
        csrf(request, record)
        if record.data.get("admin_mfa"):
            provider = provider.administrator()
        await authorize(request, record.data)
        token = record.data.get("refresh_token")
        if not token:
            raise failure("OIDC_REFRESH_NOT_AVAILABLE", "Refresh is not available.", 401)
        tokens = await provider.refresh(token)
        if not isinstance(tokens.get("access_token"), str):
            raise ProviderFailure("Missing refreshed access token")
        if tokens.get("id_token"):
            async with asyncio.timeout(4):
                claims = await provider.verifier.verify(tokens["id_token"])
            if (claims["iss"], claims["sub"]) != (record.data["issuer"], record.data["subject"]):
                raise OIDCTokenError("Refresh identity mismatch")
            new_nonce = claims.get("nonce")
            if new_nonce is not None and (
                not isinstance(new_nonce, str) or not hmac.compare_digest(new_nonce, record.data["nonce"])
            ):
                raise OIDCTokenError("Refresh nonce mismatch")
            if record.data.get("mfa"):
                from nex_api.administrator_mfa import assurance
                refreshed_mfa = assurance(request.app.state.settings, claims)
                if refreshed_mfa["auth_time"] != record.data["mfa"]["auth_time"]:
                    raise OIDCTokenError("Refresh cannot replace administrator authentication")
        elif record.data.get("mfa"):
            raise OIDCTokenError("Administrator refresh requires signed assurance")
        replacement = record.data | {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token", token),
            "auth_expires_at": time.time() + int(tokens["expires_in"]),
        }
        # Audit before making refreshed credentials usable; logout/CAS still wins.
        await event(request, "TOKEN_REFRESH_SUCCESS")
        if not await store.replace(opaque, record, replacement,
                                   int(record.data["expires_at"] - time.time())):
            await provider.revoke(replacement)
            raise failure("SESSION_REVOKED", "Session terminated during refresh.", 401)
        request.state.auth_audit_managed = True
        return JSONResponse({"status": "refreshed"}, headers=headers())
    except HTTPException as error:
        return await rejected(request, "TOKEN_REFRESH_DENIED",
                              reason(error), error.status_code)
    except Exception:
        if tokens:
            try:
                await provider.revoke(tokens)
            except ProviderFailure:
                pass
        return await rejected(request, "TOKEN_REFRESH_DENIED", "OIDC_REFRESH_FAILED", 503)