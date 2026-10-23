"""Administrator-only invitations for already verified OIDC account holders.

No passwords are collected. No direct user mutation is granted to nex_app.
An invitation activates only from an issuer-validated, nonce-checked ID token
with email_verified=true during the browser OIDC callback.
"""
from datetime import UTC, datetime, timedelta
import re
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from nex_api.audit import append_audit_event
from nex_api.dependencies import get_administrator, get_session
from nex_api.models import User, RegistrationInvitation
from nex_api.routes.auth import context, local_record, csrf

router = APIRouter(prefix="/api/v1/admin/registrations", tags=["registrations"],
                   include_in_schema=False)
_EMAIL_RE = re.compile(r"^[a-z0-9][a-z0-9.!#$%&'*+/=?^_`{|}~-]{0,63}@[a-z0-9][a-z0-9.-]{0,252}$")

class InvitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    email: str
    @field_validator("email")
    @classmethod
    def normalized(cls, value: str) -> str:
        email=value.strip().lower()
        if (len(email)>254 or not _EMAIL_RE.fullmatch(email)
            or ".." in email or email.endswith(".")
            or any(not x or x.startswith("-") or x.endswith("-")
                   for x in email.partition("@")[2].split("."))):
            raise ValueError("Invalid email address")
        return email

class InvitationView(BaseModel):
    id: UUID
    email: str
    role: str
    status: str
    expires_at: datetime

class InvitationsResponse(BaseModel):
    invitations: list[InvitationView]
    truncated: bool

@router.get("", response_model=InvitationsResponse)
async def invitations(
    user: Annotated[User, Depends(get_administrator)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InvitationsResponse:
    rows=(await session.execute(
        select(RegistrationInvitation)
        .where(RegistrationInvitation.tenant_id == user.tenant_id)
        .order_by(RegistrationInvitation.created_at.desc())
        .limit(101)
    )).scalars().all()
    return InvitationsResponse(invitations=[
        InvitationView.model_validate(row, from_attributes=True)
        for row in rows[:100]], truncated=len(rows)>100)

@router.post("", response_model=InvitationView, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    payload: InvitationRequest,
    request: Request,
    user: Annotated[User, Depends(get_administrator)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> InvitationView:
    # Two explicit server-side gates: existing admin/MFA principal and
    # same-origin opaque session with CSRF secret.
    _, store=context(request,"LOGIN")
    _, record=await local_record(request,store)
    csrf(request,record)
    if record.data.get("user_id")!=str(user.id) or record.data.get("tenant_id")!=str(user.tenant_id):
        raise HTTPException(403,detail={
            "reason_code":"SESSION_IDENTITY_MISMATCH","message":"Session mismatch."})
    email=payload.email
    duplicate=(await session.execute(
        select(RegistrationInvitation.id)
        .where(RegistrationInvitation.email==email,
               RegistrationInvitation.status=="PENDING")
        .limit(1))).scalar_one_or_none()
    if duplicate:
        raise HTTPException(409,detail={
            "reason_code":"INVITATION_ALREADY_PENDING",
            "message":"A pending invitation already exists."})
    now=datetime.now(UTC)
    invite=RegistrationInvitation(
        id=uuid4(),tenant_id=user.tenant_id,issued_by=user.id,
        email=email,role="USER",status="PENDING",
        expires_at=now+timedelta(hours=72))
    session.add(invite)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409,detail={
            "reason_code":"INVITATION_ALREADY_PENDING",
            "message":"A pending invitation already exists."}) from None
    # The audit event and invitation commit atomically via get_session.
    await append_audit_event(
        session,tenant_id=user.tenant_id,correlation_id=request.state.correlation_id,
        actor_type="ADMIN",actor_id=str(user.id),action="ACCOUNT_INVITATION_CREATED",
        object_type="REGISTRATION_INVITATION",object_id=str(invite.id),outcome="SUCCESS")
    # Avoid implicit ORM lazy read of values post-commit; return explicit fields.
    return InvitationView(
        id=invite.id,email=invite.email,role=invite.role,status=invite.status,
        expires_at=invite.expires_at)
