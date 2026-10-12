from collections.abc import AsyncIterator
import asyncio
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID
from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from nex_api.models import Tenant, User
from nex_api.oidc import OIDCConfigurationError, OIDCTokenError, OIDCVerifier
from nex_api.browser_sessions import SESSION_COOKIE
import time

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="OIDCBearer")
session_scheme = APIKeyCookie(
    name=SESSION_COOKIE, auto_error=False, scheme_name="NEXSession",
    description="Opaque cookie in browser mode. Bearer JWTs cannot bypass session revocation.",
)


def failure(code: str, message: str, status: int = 403) -> HTTPException:
    return HTTPException(status, detail={"reason_code": code, "message": message},
                         headers={"WWW-Authenticate": "Bearer"} if status == 401 else None)


@dataclass(frozen=True)
class Principal:
    issuer: str
    subject: str
    session_data: dict[str, Any] | None = None
    opaque: str | None = None


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory = request.app.state.session_factory
    if factory is None:
        raise failure("SYSTEM_DEPENDENCY_UNHEALTHY", "Database unavailable.", 503)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session_cookie: Annotated[str | None, Depends(session_scheme)] = None,
) -> Principal:
    if request.app.state.settings.oidc_browser_login_enabled:
        # Browser mode is exclusively session-based. An unexpired external JWT
        # cannot bypass local logout by being replayed as a bearer token.
        store = request.app.state.browser_sessions
        if store is None:
            raise failure("SYSTEM_DEPENDENCY_UNHEALTHY", "Session service unavailable.", 503)
        try:
            async with asyncio.timeout(3):
                record = await store.load(
                    "session", session_cookie or request.cookies.get(SESSION_COOKIE, "")
                )
            if (not record or record.data.get("expires_at", 0) <= time.time()
                    or record.data.get("auth_expires_at", 0) <= time.time()):
                raise failure("SESSION_REVOKED", "A valid application session is required.", 401)
            return Principal(record.data["issuer"], record.data["subject"], record.data,
                             session_cookie or request.cookies.get(SESSION_COOKIE, ""))
        except HTTPException:
            raise
        except Exception:
            raise failure("SYSTEM_DEPENDENCY_UNHEALTHY", "Session service unavailable.", 503)
    if credentials is None:
        raise failure("AUTH_NOT_VALID", "A valid bearer token is required.", 401)
    verifier: OIDCVerifier | None = request.app.state.oidc_verifier
    if verifier is None:
        raise failure("SYSTEM_DEPENDENCY_UNHEALTHY", "Identity provider unavailable.", 503)
    try:
        async with asyncio.timeout(4):
            claims = await verifier.verify(credentials.credentials)
    except (OIDCConfigurationError, TimeoutError):
        raise failure("SYSTEM_DEPENDENCY_UNHEALTHY", "Identity provider unavailable.", 503)
    except OIDCTokenError:
        raise failure("AUTH_NOT_VALID", "Invalid bearer token.", 401)
    return Principal(issuer=claims["iss"], subject=claims["sub"])


async def get_provisioned_user(
    request: Request,
    principal: Annotated[Principal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    if session.get_bind().dialect.name == "postgresql":
        await session.execute(text(
            "SELECT set_config('app.issuer', :issuer, true), "
            "set_config('app.subject', :subject, true)"
        ), {"issuer": principal.issuer, "subject": principal.subject})
    user = (await session.execute(select(User).where(
        User.issuer == principal.issuer, User.subject == principal.subject
    ))).scalar_one_or_none()
    if user is None:
        raise failure("IDENTITY_NOT_PROVISIONED", "Identity is not provisioned.")
    # A rollback expires ORM attributes, even with expire_on_commit=False.
    # Evidence middleware runs after the session closes: snapshot only safe IDs.
    request.state.audit_user = {"id": str(user.id), "tenant_id": user.tenant_id, "role": user.role}
    if user.status != "active":
        raise failure("USER_DISABLED", "User is disabled.")
    if session.get_bind().dialect.name == "postgresql":
        await session.execute(text(
            "SELECT set_config('app.tenant_id', :tenant, true), "
            "set_config('app.role', :role, true)"
        ), {"tenant": str(user.tenant_id), "role": user.role})
    tenant = await session.get(Tenant, user.tenant_id)
    if tenant is None or tenant.status != "active":
        raise failure("TENANT_DISABLED", "Tenant is unavailable.")
    if user.role in {"ADMIN", "SUPER_ADMIN"}:
        from nex_api.administrator_mfa import enforce
        await enforce(request, principal.session_data, principal.opaque)
    if user.role not in {"USER", "OPERATOR", "ADMIN", "SUPER_ADMIN"}:
        raise failure("ROLE_NOT_ALLOWED", "Role is not permitted.")
    return user


async def get_tenant_access(
    tenant_id: UUID,
    user: Annotated[User, Depends(get_provisioned_user)],
) -> User:
    if user.tenant_id != tenant_id:
        raise failure("TENANT_NOT_FOUND", "Tenant not found.", 404)
    if user.role not in {"OPERATOR", "ADMIN", "SUPER_ADMIN"}:
        raise failure("ROLE_NOT_ALLOWED", "Audit access requires an operator.")
    return user


async def get_operator(
    user: Annotated[User, Depends(get_provisioned_user)],
) -> User:
    if user.role not in {"OPERATOR", "ADMIN", "SUPER_ADMIN"}:
        raise failure("ROLE_NOT_ALLOWED", "Operational access requires an operator.")
    return user


async def get_administrator(
    user: Annotated[User, Depends(get_provisioned_user)],
) -> User:
    if user.role not in {"ADMIN", "SUPER_ADMIN"}:
        raise failure("ROLE_NOT_ALLOWED", "Administrative access requires an administrator.")
    return user