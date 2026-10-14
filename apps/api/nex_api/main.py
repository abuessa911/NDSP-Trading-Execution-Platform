from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Literal
from uuid import UUID, uuid4

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.exc import SQLAlchemyError

from nex_api.audit import AuditUnavailable, persist_audit
from nex_api.config import Settings, get_settings
from nex_api.database import create_session_factory
from nex_api.dependencies import get_administrator, get_provisioned_user, get_session
from nex_api.logging import configure_logging
from nex_api.models import SECURITY_TENANT_ID, Tenant, User
from nex_api.oidc import OIDCVerifier
from nex_api.routes.health import ReadyResponse, readiness, router as health_router
from nex_api.routes.tenants import AuditEventView, router as tenants_router
from nex_api.routes.auth import router as auth_router
from nex_api.browser_provider import BrowserProvider
from nex_api.browser_sessions import BrowserSessions
from nex_api.market_data_internal import router as market_data_router
from nex_api.secrets import build_secret_provider, resolve_configuration
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ErrorResponse(BaseModel):
    reason_code: str
    message: str
    correlation_id: str


class AdminDirectoryUser(BaseModel):
    id: UUID
    email: str
    role: str
    status: str


class AdminDirectoryView(BaseModel):
    tenant_id: UUID
    tenant_name: str
    tenant_status: str
    users: list[AdminDirectoryUser]
    truncated: bool


class OperationalCapability(BaseModel):
    status: Literal["CONFIGURED", "NOT_CONFIGURED", "NOT_IMPLEMENTED"]
    reason_code: str


class AdminOperationsView(BaseModel):
    tenant_id: UUID
    entitlements: dict[str, bool]
    subscription: OperationalCapability
    trading_safety: dict[str, bool | str]
    exchange: OperationalCapability
    ndsp_connector: OperationalCapability
    worker_queues: OperationalCapability
    notifications: OperationalCapability
    incidents: OperationalCapability


def create_app(settings: Settings | None = None) -> FastAPI:
    supplied = settings or get_settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        provider = build_secret_provider(supplied)
        configured = resolve_configuration(supplied, provider)
        app.state.secret_provider = provider
        app.state.settings = configured
        app.state.session_factory = create_session_factory(configured)
        app.state.redis = Redis.from_url(
            configured.redis_url, socket_connect_timeout=2, socket_timeout=2
        ) if configured.redis_url else None
        app.state.oidc_verifier = OIDCVerifier(
            issuer=configured.oidc_issuer or "", audience=configured.oidc_audience or "",
            jwks_url=configured.oidc_jwks_url or "",
            allowed_algorithm=configured.oidc_allowed_algorithm,
            cache_seconds=configured.oidc_jwks_cache_seconds,
        ) if configured.oidc_configured else None
        app.state.browser_provider = BrowserProvider(configured) \
            if configured.oidc_browser_login_enabled else None
        app.state.browser_sessions = BrowserSessions(
            app.state.redis, configured.nex_session_encryption_key.get_secret_value()
        ) if (configured.oidc_browser_login_enabled and app.state.redis is not None
              and configured.nex_session_encryption_key is not None) else None
        yield
        if app.state.redis is not None:
            await app.state.redis.aclose()
        if app.state.session_factory is not None:
            await app.state.session_factory.kw["bind"].dispose()

    app = FastAPI(
        title="NEX Control API", version="1.0.0",
        description="M1 only. OIDC PKCE browser sessions; administrative MFA remains unverified.",
        docs_url="/api/docs" if supplied.environment != "production" else None,
        redoc_url=None, openapi_url="/api/openapi.json", lifespan=lifespan,
        responses={code: {"model": ErrorResponse} for code in (401, 403, 404, 422, 500, 503)},
    )
    app.include_router(health_router, prefix="/api")
    app.include_router(tenants_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    # M2-A routes remain admin + server MFA guarded and disabled by default.
    app.include_router(market_data_router)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> JSONResponse:
        detail = error.detail if isinstance(error.detail, dict) else {
            "reason_code": "REQUEST_REJECTED", "message": "Request rejected."
        }
        return JSONResponse(status_code=error.status_code, headers=error.headers,
                            content=detail | {"correlation_id": str(request.state.correlation_id)})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={
            "reason_code": "REQUEST_NOT_VALID", "message": "Invalid request.",
            "correlation_id": str(request.state.correlation_id),
        })

    @app.get("/api/v1/health/summary", response_model=ReadyResponse,
             operation_id="getHealthSummary", responses={503: {"model": ReadyResponse}})
    async def summary(
        request: Request, response: Response,
        user: Annotated[User, Depends(get_provisioned_user)],
    ) -> dict[str, object]:
        return await readiness(request, response)

    # Native admin API paths are forwarded separately from static /admin UI
    # routes. Registration changes routing only, never authorization.
    # Browser sessions are deliberately scoped to /api (HttpOnly Secure cookie).
    # Reuse the SAME server-authoritative administrator dependency on a cookie-safe
    # browser route; retain canonical /admin/v1 contracts unchanged.
    @app.get("/api/v1/admin/system/health", include_in_schema=False)
    @app.get("/admin/v1/system/health", response_model=ReadyResponse,
             operation_id="getAdminHealth", responses={503: {"model": ReadyResponse}})
    async def admin_health(
        request: Request, response: Response, user: Annotated[User, Depends(get_administrator)],
    ) -> dict[str, object]:
        return await readiness(request, response)

    @app.get("/api/v1/admin/audit", include_in_schema=False)
    @app.get("/admin/v1/audit", response_model=list[AuditEventView],
             operation_id="getAdminAudit")
    async def admin_audit(
        user: Annotated[User, Depends(get_administrator)],
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> list[AuditEventView]:
        events = (await session.execute(select(AuditEvent).where(
            AuditEvent.tenant_id == user.tenant_id
        ).order_by(AuditEvent.created_at.desc()).limit(100))).scalars().all()
        return [AuditEventView.model_validate(event) for event in events]

    # Internal, browser-only, read-only directory. Same server-side administrator
    # MFA dependency as other control endpoints; RLS adds tenant-scoped SELECT.
    # Not part of the public M1 OpenAPI contract.
    @app.get("/api/v1/admin/directory",
             response_model=AdminDirectoryView, include_in_schema=False)
    async def admin_directory(
        user: Annotated[User, Depends(get_administrator)],
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> AdminDirectoryView:
        tenant = await session.get(Tenant, user.tenant_id)
        if tenant is None or tenant.status != "active":
            raise HTTPException(
                status_code=403,
                detail={"reason_code": "TENANT_DISABLED", "message": "Tenant unavailable."},
            )
        rows = (await session.execute(
            select(User).where(User.tenant_id == user.tenant_id)
            .order_by(User.created_at.desc(), User.id).limit(101)
        )).scalars().all()
        return AdminDirectoryView(
            tenant_id=tenant.id, tenant_name=tenant.name,
            tenant_status=tenant.status,
            users=[AdminDirectoryUser(
                id=entry.id, email=entry.email, role=entry.role, status=entry.status
            ) for entry in rows[:100]],
            truncated=len(rows) > 100,
        )

    # Internal browser-only operational projection. It contains only validated
    # server configuration and explicit absence states; it never guesses health
    # for services/data stores that M1 does not implement.
    @app.get("/api/v1/admin/operations",
             response_model=AdminOperationsView, include_in_schema=False)
    async def admin_operations(
        request: Request,
        user: Annotated[User, Depends(get_administrator)],
    ) -> AdminOperationsView:
        not_implemented = OperationalCapability(
            status="NOT_IMPLEMENTED", reason_code="M1_DATA_SOURCE_NOT_IMPLEMENTED"
        )
        return AdminOperationsView(
            tenant_id=user.tenant_id,
            entitlements={"live_trading": request.app.state.settings.live_trading_enabled},
            subscription=OperationalCapability(
                status="NOT_IMPLEMENTED", reason_code="BILLING_NOT_IMPLEMENTED"
            ),
            trading_safety=request.app.state.settings.trading_safety,
            exchange=OperationalCapability(
                status="NOT_CONFIGURED", reason_code="EXCHANGE_CONNECTOR_NOT_CONFIGURED"
            ),
            ndsp_connector=OperationalCapability(
                status="NOT_CONFIGURED", reason_code="NDSP_CONNECTOR_NOT_CONFIGURED"
            ),
            worker_queues=not_implemented,
            notifications=not_implemented,
            incidents=not_implemented,
        )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        correlation_id = uuid4()
        request.state.correlation_id = correlation_id
        request.state.audit_user = None
        try:
            response = await call_next(request)
        except Exception as error:
            code = ("SYSTEM_DEPENDENCY_UNHEALTHY" if isinstance(error, SQLAlchemyError)
                    else "INTERNAL_ERROR")
            response = JSONResponse(status_code=503 if code != "INTERNAL_ERROR" else 500,
                                    content={"reason_code": code, "message": "Request failed.",
                                             "correlation_id": str(correlation_id)})
            structlog.get_logger("nex.api").error("unhandled_request_error",
                                                 correlation_id=str(correlation_id))
        # Audit every M1 identity/admin request, including auth, authorization and
        # unhandled failures. Never copy path/query/header/body or token claims.
        if (request.url.path.startswith(("/api/v1/", "/admin/"))
                and not getattr(request.state, "auth_audit_managed", False)):
            user = request.state.audit_user
            outcome = ("SUCCESS" if response.status_code < 400 else
                       "DENIED" if response.status_code < 500 else "FAILED")
            reason = None
            if response.status_code >= 400:
                # Only safe server error code from the rendered response.
                import json
                body = (b"".join([chunk async for chunk in response.body_iterator])
                        if hasattr(response, "body_iterator") else bytes(response.body))
                try:
                    reason = json.loads(body).get("reason_code", "REQUEST_REJECTED")
                except (ValueError, AttributeError):
                    reason = "REQUEST_REJECTED"
                response = Response(body, status_code=response.status_code,
                                    headers=dict(response.headers), media_type="application/json")
            try:
                await persist_audit(
                    request.app.state.session_factory,
                    tenant_id=user["tenant_id"] if user else SECURITY_TENANT_ID,
                    correlation_id=correlation_id,
                    actor_type=("ADMIN" if user and user["role"] in {"ADMIN", "SUPER_ADMIN"}
                                else "USER" if user else "SYSTEM"),
                    actor_id=user["id"] if user else None,
                    action=getattr(request.scope.get("route"), "operation_id", None)
                    or "M1_REQUEST", object_type="CONTROL_API",
                    outcome=outcome, reason_code=reason,
                    metadata_json={"status_code": response.status_code},
                )
            except AuditUnavailable:
                structlog.get_logger("nex.api").error(
                    "audit_persistence_unavailable", correlation_id=str(correlation_id)
                )
                response = JSONResponse(status_code=503, content={
                    "reason_code": "AUDIT_PERSISTENCE_UNAVAILABLE",
                    "message": "Required security evidence could not be persisted.",
                    "correlation_id": str(correlation_id),
                })
        response.headers["X-Correlation-ID"] = str(correlation_id)
        if request.url.path.startswith(("/api/v1/", "/admin/")):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
        return response

    return app


from nex_api.models import AuditEvent  # noqa: E402

app = create_app()
