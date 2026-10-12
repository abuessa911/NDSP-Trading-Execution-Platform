import argparse
import asyncio
import sys
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from nex_api.audit import append_audit_event
from nex_api.config import Settings
from nex_api.database import normalize_database_url
from nex_api.models import Tenant, User, ROLES, SECURITY_TENANT_ID
from nex_api.secrets import build_secret_provider, resolve_configuration


async def _provision_owner(
    *, issuer: str, subject: str, tenant_name: str, email: str, role: str
) -> str:
    settings = Settings()
    settings = resolve_configuration(settings, build_secret_provider(settings))
    database_url = settings.migration_database_url
    if not database_url:
        raise RuntimeError("Explicit MIGRATION_DATABASE_URL must be configured.")
    if role not in ROLES or "@" not in email or len(email) > 320:
        raise ValueError("An explicit approved role and email are required.")
    if not issuer or not subject or not tenant_name.strip():
        raise ValueError("Issuer, subject, and tenant name are required.")
    if not settings.oidc_configured:
        raise ValueError("OIDC issuer, audience, and JWKS URL must be configured first.")
    if issuer != settings.oidc_issuer:
        raise ValueError("Bootstrap issuer does not match the configured OIDC issuer.")

    engine = create_async_engine(normalize_database_url(database_url), pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    tenant_id = uuid4()
    async with factory() as session:
        safe_role = (await session.execute(text(
            "SELECT current_user='nex_migrator' AND NOT rolsuper AND NOT rolbypassrls "
            "FROM pg_roles WHERE rolname=current_user"
        ))).scalar()
        if not safe_role:
            raise RuntimeError("Provisioning requires the nex_migrator operator role.")
        result = await session.execute(
            select(User).where(User.issuer == issuer, User.subject == subject)
        )
        if result.scalar_one_or_none() is not None:
            raise ValueError("This identity is already provisioned.")
        tenant = Tenant(id=tenant_id, name=tenant_name.strip())
        session.add(tenant)
        await session.flush()
        user = User(id=uuid4(), issuer=issuer, subject=subject, tenant_id=tenant.id,
                    email=email, role=role)
        session.add(user)
        await session.flush()
        if session.bind is not None and session.bind.dialect.name == "postgresql":
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
                {"tenant_id": str(tenant.id)},
            )
        await append_audit_event(
            session,
            action="INITIAL_OWNER_PROVISIONED",
            outcome="SUCCESS",
            actor_type="SYSTEM",
            actor_id="nex-bootstrap",
            tenant_id=tenant.id,
            correlation_id=uuid4(),
            object_type="USER",
            object_id=str(user.id),
        )
        await session.commit()
    await engine.dispose()
    return str(tenant_id)


async def provision_owner(
    *, issuer: str, subject: str, tenant_name: str, email: str, role: str,
) -> str:
    try:
        return await _provision_owner(
            issuer=issuer, subject=subject, tenant_name=tenant_name, email=email, role=role,
        )
    except Exception:
        # The failed provisioning transaction has rolled back. Persist a safe
        # operator failure in a distinct, bounded transaction; no input payloads.
        settings = Settings()
        settings = resolve_configuration(settings, build_secret_provider(settings))
        if not settings.migration_database_url:
            raise RuntimeError("Provisioning failed; required audit persistence unavailable.")
        engine = create_async_engine(
            normalize_database_url(settings.migration_database_url),
            hide_parameters=True, connect_args={"timeout": 3, "command_timeout": 3},
        )
        try:
            async with asyncio.timeout(4), async_sessionmaker(engine)() as session:
                safe_role = (await session.execute(text(
                    "SELECT current_user='nex_migrator' AND NOT rolsuper AND NOT rolbypassrls "
                    "FROM pg_roles WHERE rolname=current_user"
                ))).scalar()
                if not safe_role:
                    raise RuntimeError("Unsafe operator audit role.")
                await append_audit_event(
                    session, tenant_id=SECURITY_TENANT_ID, correlation_id=uuid4(),
                    actor_type="SYSTEM", actor_id="nex-bootstrap",
                    action="INITIAL_OWNER_PROVISIONING_FAILED", object_type="USER",
                    outcome="FAILED", reason_code="PROVISIONING_FAILED",
                )
                await session.commit()
        except Exception:
            raise RuntimeError("Provisioning failed; required audit persistence unavailable.") from None
        finally:
            await engine.dispose()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Provision the first NEX tenant owner from a trusted OIDC subject."
    )
    parser.add_argument("--issuer", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--tenant-name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=ROLES, required=True)
    args = parser.parse_args()
    try:
        tenant_id = asyncio.run(
            provision_owner(
                issuer=args.issuer,
                subject=args.subject,
                tenant_name=args.tenant_name,
                email=args.email,
                role=args.role,
            )
        )
    except Exception as error:
        print("Provisioning failed; verify configuration and identity inputs.", file=sys.stderr)
        raise SystemExit(1) from error
    print(f"Provisioned initial tenant owner. Tenant ID: {tenant_id}")


if __name__ == "__main__":
    main()