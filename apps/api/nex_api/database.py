from collections.abc import AsyncIterator
import asyncio

from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from nex_api.config import Settings


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def create_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession] | None:
    if not settings.database_url:
        return None
    engine = create_async_engine(
        normalize_database_url(settings.database_url),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        hide_parameters=True,
        connect_args={"timeout": 3, "command_timeout": 3},
    )
    return async_sessionmaker(engine, expire_on_commit=False)


async def database_is_available(
    session_factory: async_sessionmaker[AsyncSession] | None,
) -> bool:
    if session_factory is None:
        return False
    try:
        async with asyncio.timeout(3), session_factory() as session:
            await session.execute(text("SELECT 1"))
            role = (await session.execute(text(
                "SELECT current_user = 'nex_app' AND NOT rolsuper AND NOT rolbypassrls "
                "FROM pg_roles WHERE rolname=current_user"
            ))).scalar()
            if not role:
                return False
            version = (await session.execute(text(
                "SELECT version_num FROM alembic_version"
            ))).scalar()
            if version != "0006_verified_self_signup":
                return False
            from nex_api.models import Base
            for name, table in Base.metadata.tables.items():
                columns = (await session.execute(text(
                    "SELECT column_name, is_nullable FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name=:name"
                ), {"name": name})).all()
                expected = {(c.name, "YES" if c.nullable else "NO") for c in table.columns}
                if set(columns) != expected:
                    return False
                connection = await session.connection()
                reflected = await connection.run_sync(
                    lambda conn: inspect(conn).get_columns(name, schema="public")
                )
                expected_types = {
                    c.name: str(c.type.compile(dialect=session.get_bind().dialect))
                    for c in table.columns
                }
                actual_types = {
                    c["name"]: str(c["type"].compile(dialect=session.get_bind().dialect))
                    for c in reflected
                }
                if actual_types != expected_types:
                    return False
                rls = (await session.execute(text(
                    "SELECT relrowsecurity AND relforcerowsecurity FROM pg_class "
                    "WHERE oid=to_regclass(:name)"
                ), {"name": name})).scalar()
                if not rls:
                    return False
            constraints = set((await session.execute(text(
                "SELECT conname FROM pg_constraint WHERE connamespace='public'::regnamespace"
            ))).scalars())
            if not {"users_role_check", "users_status_check", "users_email_check",
                    "audit_actor_type_check", "audit_outcome_check",
                    "registration_invite_role_check", "registration_invite_status_check",
                    "registration_invite_email_normalized_check"} <= constraints:
                return False
            policy = (await session.execute(text(
                "SELECT pg_get_expr(polqual,polrelid) FROM pg_policy "
                "WHERE polname='audit_read' AND polrelid='audit_events'::regclass"
            ))).scalar()
            # The policy must keep the tenant context and exact approved roles.
            if not policy or not all(fragment in policy for fragment in (
                "app.tenant_id", "app.role", "OPERATOR", "ADMIN", "SUPER_ADMIN"
            )):
                return False
            directory_policy = (await session.execute(text(
                "SELECT pg_get_expr(polqual,polrelid) FROM pg_policy "
                "WHERE polname='admin_tenant_user_list' AND polrelid='users'::regclass"
            ))).scalar()
            if not directory_policy or not all(fragment in directory_policy for fragment in (
                "app.tenant_id", "app.role", "tenant_id", "ADMIN", "SUPER_ADMIN"
            )):
                return False
            triggers = set((await session.execute(text(
                "SELECT tgname FROM pg_trigger WHERE tgrelid='audit_events'::regclass "
                "AND tgenabled='O'"
            ))).scalars())
            if not {"audit_events_append_only", "audit_no_truncate"} <= triggers:
                return False
            if (await session.execute(text(
                "SELECT has_table_privilege(current_user,'audit_events','UPDATE') OR "
                "has_table_privilege(current_user,'audit_events','DELETE') OR "
                "has_table_privilege(current_user,'audit_events','TRUNCATE') OR "
                "has_table_privilege(current_user,'users','INSERT') OR "
                "has_table_privilege(current_user,'users','UPDATE') OR "
                "has_table_privilege(current_user,'registration_invitations','UPDATE') OR "
                "has_table_privilege(current_user,'registration_invitations','DELETE') OR "
                "has_schema_privilege(current_user,'public','CREATE')"
            ))).scalar():
                return False
            registration_policy = (await session.execute(text(
                "SELECT pg_get_expr(polwithcheck, polrelid) FROM pg_policy "
                "WHERE polname='invite_admin_insert' "
                "AND polrelid='registration_invitations'::regclass"
            ))).scalar()
            if not registration_policy or not all(part in registration_policy for part in (
                "app.tenant_id", "app.role", "app.user_id", "ADMIN", "SUPER_ADMIN", "USER"
            )):
                return False
            permitted = (await session.execute(text(
                "SELECT has_table_privilege(current_user,'registration_invitations','INSERT') "
                "AND has_function_privilege(current_user, "
                "'claim_verified_invitation(text,text,text,boolean)','EXECUTE')"
            ))).scalar()
            if not permitted:
                return False
        return True
    except Exception:
        return False


async def session_scope(
    session_factory: async_sessionmaker[AsyncSession] | None,
) -> AsyncIterator[AsyncSession]:
    if session_factory is None:
        raise RuntimeError("Database is not configured.")
    async with session_factory() as session:
        yield session