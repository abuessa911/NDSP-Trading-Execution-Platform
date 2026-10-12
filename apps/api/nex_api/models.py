from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, JSON, String
from sqlalchemy import UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SECURITY_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
ROLES = ("USER", "OPERATOR", "ADMIN", "SUPER_ADMIN")


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'disabled')", name="tenants_status_check"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(24), default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("issuer", "subject", name="users_issuer_subject_uq"),
        CheckConstraint(
            "role IN ('USER','OPERATOR','ADMIN','SUPER_ADMIN')", name="users_role_check"
        ),
        CheckConstraint("status IN ('active','disabled')", name="users_status_check"),
        CheckConstraint("length(email) > 3 AND position('@' in email) > 1",
                        name="users_email_check"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="active", server_default="active")
    issuer: Mapped[str] = mapped_column(String(512))
    subject: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint("actor_type IN ('USER','ADMIN','SYSTEM','SERVICE')",
                        name="audit_actor_type_check"),
        CheckConstraint("outcome IN ('SUCCESS','DENIED','FAILED')",
                        name="audit_outcome_check"),
        Index("audit_events_tenant_created_idx", "tenant_id", "created_at"),
        Index("audit_events_actor_created_idx", "actor_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    correlation_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, default=uuid4)
    actor_type: Mapped[str] = mapped_column(String(24), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(512))
    action: Mapped[str] = mapped_column(String(96), nullable=False)
    object_type: Mapped[str] = mapped_column(String(96), nullable=False)
    object_id: Mapped[str | None] = mapped_column(String(512))
    outcome: Mapped[str] = mapped_column(String(24), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(96))
    source_ip_hash: Mapped[str | None] = mapped_column(String(64))
    user_agent_hash: Mapped[str | None] = mapped_column(String(64))
    before_hash: Mapped[str | None] = mapped_column(String(64))
    after_hash: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict,
        server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )