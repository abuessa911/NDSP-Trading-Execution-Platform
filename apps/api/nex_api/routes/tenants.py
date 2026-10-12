from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nex_api.dependencies import get_provisioned_user, get_session, get_tenant_access
from nex_api.models import AuditEvent, User

router = APIRouter(prefix="/v1", tags=["identity and tenancy"])


class MeResponse(BaseModel):
    user_id: UUID
    tenant_id: UUID
    email: str
    role: Literal["USER", "OPERATOR", "ADMIN", "SUPER_ADMIN"]
    status: str
    entitlements: dict[str, bool]


class AuditEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_id: UUID
    correlation_id: UUID
    actor_type: Literal["USER", "ADMIN", "SYSTEM", "SERVICE"]
    actor_id: str | None
    action: str
    object_type: str
    object_id: str | None
    outcome: Literal["SUCCESS", "DENIED", "FAILED"]
    reason_code: str | None
    source_ip_hash: str | None
    user_agent_hash: str | None
    before_hash: str | None
    after_hash: str | None
    metadata_json: dict[str, Any]
    created_at: datetime


@router.get("/me", response_model=MeResponse, operation_id="getMe")
async def get_me(user: Annotated[User, Depends(get_provisioned_user)]) -> MeResponse:
    return MeResponse.model_validate({
        "user_id": user.id, "tenant_id": user.tenant_id, "email": user.email,
        "role": user.role, "status": user.status, "entitlements": {"live_trading": False},
    })


@router.get("/tenants/{tenant_id}/audit-events", response_model=list[AuditEventView],
            operation_id="listTenantAuditEvents")
async def list_audit_events(
    tenant_id: UUID,
    user: Annotated[User, Depends(get_tenant_access)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[AuditEventView]:
    events = (await session.execute(select(AuditEvent).where(
        AuditEvent.tenant_id == user.tenant_id
    ).order_by(AuditEvent.created_at.desc()).limit(limit))).scalars().all()
    return [AuditEventView.model_validate(event) for event in events]