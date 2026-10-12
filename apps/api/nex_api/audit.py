import asyncio
from typing import Any, cast
from uuid import UUID, uuid4
from datetime import datetime, UTC

from sqlalchemy import insert, text, Table
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from nex_api.models import AuditEvent

# Deliberately allowlist scalar operational counters, never arbitrary payloads.
METADATA_KEYS = {"returned", "status_code", "role", "service", "operation"}


def sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    return {key: value for key, value in (metadata or {}).items()
            if key in METADATA_KEYS and isinstance(value, (int, bool))}


async def append_audit_event(
    session: AsyncSession, *, tenant_id: UUID, correlation_id: UUID,
    actor_type: str, actor_id: str | None, action: str, object_type: str,
    outcome: str, object_id: str | None = None, reason_code: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> AuditEvent:
    if actor_type not in {"USER", "ADMIN", "SYSTEM", "SERVICE"}:
        raise ValueError("Invalid audit actor type")
    if outcome not in {"SUCCESS", "DENIED", "FAILED"}:
        raise ValueError("Invalid audit outcome")
    event = AuditEvent(
        id=uuid4(), created_at=datetime.now(UTC),
        tenant_id=tenant_id, correlation_id=correlation_id, actor_type=actor_type,
        actor_id=actor_id, action=action, object_type=object_type, object_id=object_id,
        outcome=outcome, reason_code=reason_code,
        metadata_json=sanitize_metadata(metadata_json),
    )
    # ORM server-default RETURNING requires SELECT under PostgreSQL RLS. The
    # evidence writer must not acquire read privileges just to append an event.
    await session.execute(insert(cast(Table, AuditEvent.__table__)).inline().values(
        **{column.name: getattr(event, column.name) for column in AuditEvent.__table__.columns}
    ))
    return event


class AuditUnavailable(RuntimeError):
    pass


async def persist_audit(
    factory: async_sessionmaker[AsyncSession] | None, **fields: Any,
) -> None:
    """Separate bounded transaction: survives business/request rollback."""
    if factory is None:
        raise AuditUnavailable("Required audit persistence is unavailable")
    try:
        async with asyncio.timeout(3):
            async with factory() as session:
                if session.get_bind().dialect.name == "postgresql":
                    # No security writes through superuser/template/external roles.
                    role = (await session.execute(text(
                        "SELECT current_user = 'nex_app' AND NOT rolsuper AND NOT rolbypassrls "
                        "FROM pg_roles WHERE rolname=current_user"
                    ))).scalar()
                    if not role:
                        raise AuditUnavailable("Unsafe audit runtime role")
                    await session.execute(
                        text("SELECT set_config('app.tenant_id', :tenant, true)"),
                        {"tenant": str(fields["tenant_id"])},
                    )
                await append_audit_event(session, **fields)
                await session.commit()
    except Exception as error:
        raise AuditUnavailable("Required audit persistence is unavailable") from error