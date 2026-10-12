import asyncio
from typing import Any

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from nex_api.database import database_is_available

router = APIRouter(prefix="/health", tags=["health"])


class LiveResponse(BaseModel):
    status: str


class AuthConfiguration(BaseModel):
    browser_login_enabled: bool
    administrator_mfa_configured: bool = False


@router.get("/auth", response_model=AuthConfiguration, operation_id="getAuthConfiguration")
async def auth_configuration(request: Request) -> dict[str, bool]:
    # Capability only, deliberately not a readiness/acceptance declaration.
    return {"browser_login_enabled": request.app.state.settings.oidc_browser_login_enabled,
            "administrator_mfa_configured": bool(request.app.state.settings.oidc_admin_mfa_policy)}


class ReadyResponse(BaseModel):
    status: str
    reason_code: str | None
    components: dict[str, str]


@router.get("/live", response_model=LiveResponse, operation_id="getLiveness")
async def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready", response_model=ReadyResponse, operation_id="getReadiness",
            responses={503: {"model": ReadyResponse}})
async def readiness(request: Request, response: Response) -> dict[str, Any]:
    async def redis_ready() -> bool:
        try:
            async with asyncio.timeout(3):
                return bool(request.app.state.redis and await request.app.state.redis.ping())
        except Exception:
            return False

    async def oidc_ready() -> bool:
        try:
            async with asyncio.timeout(3):
                verifier = request.app.state.oidc_verifier
                if request.app.state.settings.oidc_browser_login_enabled:
                    provider = request.app.state.browser_provider
                    return bool(request.app.state.browser_sessions and provider
                                and await provider.ready())
                return bool(verifier and await verifier.ready())
        except Exception:
            return False

    database, redis, oidc = await asyncio.gather(
        database_is_available(request.app.state.session_factory), redis_ready(), oidc_ready()
    )
    ready = database and redis and oidc
    if not ready:
        response.status_code = 503
    return {
        "status": "ready" if ready else "not_ready",
        "reason_code": None if ready else "SYSTEM_DEPENDENCY_UNHEALTHY",
        "components": {
            "database": "ready" if database else "unavailable",
            "redis": "ready" if redis else "unavailable",
            "oidc": "ready" if oidc else (
                "unavailable" if request.app.state.oidc_verifier else "not_configured"
            ),
        },
    }