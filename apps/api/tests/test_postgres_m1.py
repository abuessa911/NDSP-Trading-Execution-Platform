"""Real PostgreSQL tests; opt in only to the explicitly named local isolated target.

No SQLite fallback. No environment DATABASE_URL is ever used. The Docker
project label and database name are checked before any synthetic test write.
"""
import asyncio
import json
import os
import subprocess
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from nex_api.audit import persist_audit
from nex_api.config import Settings
from nex_api.database import database_is_available
from nex_api.main import create_app
from nex_api.models import AuditEvent, SECURITY_TENANT_ID
from test_oidc import issue_token, make_verifier
from test_oidc import signing_material as oidc_signing_material


@pytest.fixture
def signing_material():
    return oidc_signing_material.__wrapped__()

PROJECT = os.environ.get("NEX_M1_TEST_PROJECT", "nex-m1-isolated-verification")
if not (PROJECT == "nex-m1-isolated-verification" or (
    PROJECT.startswith("nex-m1-isolated-verification-")
    and PROJECT.removeprefix("nex-m1-isolated-verification-").isalnum()
)):
    raise ValueError("Only explicitly isolated NEX test projects are allowed")
CONTAINER = PROJECT + "-db-1"
pytestmark = pytest.mark.skipif(
    os.environ.get("NEX_M1_POSTGRES_TEST") != "isolated",
    reason="Explicit isolated PostgreSQL opt-in required; never substitutes SQLite",
)


@pytest.fixture(scope="module")
def target():
    info = json.loads(subprocess.check_output(["docker", "inspect", CONTAINER]))[0]
    assert info["Config"]["Labels"]["com.docker.compose.project"] == PROJECT
    ip = info["NetworkSettings"]["Networks"][PROJECT + "_nex"]["IPAddress"]
    assert ip.startswith("172.")  # Local Docker bridge, never environment database.
    return {
        "app": f"postgresql+asyncpg://nex_app:synthetic-runtime-only@{ip}:5432/nex",
        "migration":
            f"postgresql+asyncpg://nex_migrator:synthetic-migrator-only@{ip}:5432/nex",
        "bootstrap":
            f"postgresql+asyncpg://nex_test_bootstrap:synthetic-bootstrap-only@{ip}:5432/nex",
    }


@pytest.fixture
def identities(target):
    tenant_a, tenant_b = uuid4(), uuid4()
    user_ids = {role: uuid4() for role in ("USER", "OPERATOR", "ADMIN", "SUPER_ADMIN",
                                         "DISABLED", "DISABLED_TENANT")}

    async def seed():
        engine = create_async_engine(target["migration"])
        async with engine.begin() as connection:
            assert (await connection.execute(text("SELECT current_database()"))).scalar() == "nex"
            await connection.execute(text(
                "INSERT INTO tenants(id,name,status) VALUES (:a,'Synthetic A','active'), "
                "(:b,'Synthetic B','disabled')"
            ), {"a": tenant_a, "b": tenant_b})
            for role, user_id in user_ids.items():
                await connection.execute(text(
                    "INSERT INTO users(id,tenant_id,email,role,status,issuer,subject) "
                    "VALUES (:id,:tenant,'synthetic@example.test',:role,:status,"
                    "'https://idp.example.test',:subject)"
                ), {"id": user_id, "tenant": tenant_b if role == "DISABLED_TENANT" else tenant_a,
                    "role": role if role in {"USER", "OPERATOR", "ADMIN", "SUPER_ADMIN"} else "USER",
                    "status": "disabled" if role == "DISABLED" else "active",
                    "subject": str(user_id)})
        await engine.dispose()

    asyncio.run(seed())
    return tenant_a, tenant_b, user_ids


def test_schema_roles_grants_and_rls(target):
    async def check():
        engine = create_async_engine(target["app"])
        factory = async_sessionmaker(engine)
        assert await database_is_available(factory)
        async with engine.connect() as conn:
            assert (await conn.execute(text("SELECT current_user"))).scalar() == "nex_app"
            assert (await conn.execute(text("SELECT count(*) FROM users"))).scalar() == 0
            assert (await conn.execute(text("SELECT count(*) FROM tenants"))).scalar() == 0
            roles = (await conn.execute(text(
                "SELECT rolname,rolsuper,rolbypassrls,rolcreatedb,rolcreaterole FROM pg_roles "
                "WHERE rolname IN ('nex_app','nex_migrator') ORDER BY rolname"
            ))).all()
            assert len(roles) == 2
            assert all(not any(row[1:]) for row in roles)
            for table in ("tenants", "users", "audit_events"):
                assert not (await conn.execute(text(
                    "SELECT has_table_privilege('nex_app',:table,'UPDATE') OR "
                    "has_table_privilege('nex_app',:table,'DELETE') OR "
                    "has_table_privilege('nex_app',:table,'TRUNCATE')"
                ), {"table": table})).scalar()
        await engine.dispose()
    asyncio.run(check())


def test_durable_audit_actors_outcomes_and_append_only(target, identities):
    tenant, other, users = identities

    async def check():
        engine = create_async_engine(target["app"])
        factory = async_sessionmaker(engine, expire_on_commit=False)
        correlation = uuid4()
        async with factory() as rolled_back:
            await rolled_back.execute(text("SELECT 1"))
            for actor in ("USER", "ADMIN", "SYSTEM", "SERVICE"):
                for outcome in ("SUCCESS", "DENIED", "FAILED"):
                    await persist_audit(
                        factory, tenant_id=tenant, correlation_id=correlation,
                        actor_type=actor, actor_id=str(users["USER"]) if actor == "USER" else None,
                        action="SYNTHETIC_TEST", object_type="TEST", outcome=outcome,
                        metadata_json={"token": "do-not-store", "returned": 1},
                    )
            await rolled_back.rollback()
        async with factory() as session:
            await session.execute(text(
                "SELECT set_config('app.tenant_id',:tenant,true), "
                "set_config('app.role','OPERATOR',true)"
            ), {"tenant": str(tenant)})
            rows = (await session.execute(select(AuditEvent).where(
                AuditEvent.correlation_id == correlation
            ))).scalars().all()
            assert len(rows) == 12
            assert all(row.metadata_json == {"returned": 1} for row in rows)
            await session.execute(text("SELECT set_config('app.tenant_id',:tenant,true)"),
                                  {"tenant": str(other)})
            assert not (await session.execute(select(AuditEvent).where(
                AuditEvent.correlation_id == correlation
            ))).scalars().all()
        for statement in (
            "UPDATE audit_events SET action='BAD'",
            "DELETE FROM audit_events", "TRUNCATE audit_events",
        ):
            with pytest.raises(Exception):
                async with engine.begin() as conn:
                    await conn.execute(text(statement))
        await engine.dispose()
        migrator = create_async_engine(target["migration"])
        for statement in (
            "UPDATE audit_events SET action='BAD'", "DELETE FROM audit_events",
            "TRUNCATE audit_events", "TRUNCATE audit_events_legacy",
        ):
            with pytest.raises(Exception):
                async with migrator.begin() as conn:
                    await conn.execute(text(statement))
        for values in ("'INVALID','SUCCESS'", "'USER','invalid'"):
            with pytest.raises(Exception):
                async with migrator.begin() as conn:
                    await conn.execute(text(
                        "INSERT INTO audit_events(id,tenant_id,correlation_id,actor_type,"
                        "outcome,action,object_type) VALUES "
                        f"('{uuid4()}','{tenant}','{uuid4()}',{values},'TEST','TEST')"
                    ))
        await migrator.dispose()
    asyncio.run(check())



def test_administrator_audit_rls_is_readable_and_tenant_scoped(target, identities):
    """The app role never bypasses tenant RLS, even for SUPER_ADMIN."""
    tenant, other, _ = identities

    async def check():
        engine = create_async_engine(target["app"])
        factory = async_sessionmaker(engine, expire_on_commit=False)
        correlation = uuid4()
        await persist_audit(
            factory, tenant_id=tenant, correlation_id=correlation,
            actor_type="ADMIN", action="SYNTHETIC_ADMIN_RLS_TEST",
            object_type="TEST", outcome="SUCCESS",
        )
        async with factory() as session:
            for role in ("USER", "OPERATOR", "ADMIN", "SUPER_ADMIN"):
                await session.execute(text(
                    "SELECT set_config('app.tenant_id',:tenant,true), "
                    "set_config('app.role',:role,true)"
                ), {"tenant": str(tenant), "role": role})
                rows = (await session.execute(select(AuditEvent).where(
                    AuditEvent.correlation_id == correlation
                ))).scalars().all()
                assert len(rows) == (0 if role == "USER" else 1), role
                await session.execute(text(
                    "SELECT set_config('app.tenant_id',:tenant,true)"
                ), {"tenant": str(other)})
                assert not (await session.execute(select(AuditEvent).where(
                    AuditEvent.correlation_id == correlation
                ))).scalars().all(), role
        await engine.dispose()

    asyncio.run(check())

def test_oidc_to_postgres_disabled_and_role_boundaries(target, identities, signing_material):
    tenant, other, users = identities
    private_key, jwks = signing_material
    app = create_app(Settings(_env_file=None, database_url=target["app"]))
    with TestClient(app) as client:
        assert app.state.settings.database_url == target["app"]
        verifier = make_verifier(jwks)
        app.state.oidc_verifier = verifier
        # Real cryptographic verification; no principal/authorization override.
        import jwt
        import time
        for role, user_id in users.items():
            token = jwt.encode(
                {"iss": "https://idp.example.test", "sub": str(user_id), "aud": "nex-api",
                 "iat": int(time.time()), "exp": int(time.time()) + 120, "amr": ["mfa"]},
                private_key, algorithm="RS256", headers={"kid": "nex-test-key"},
            )
            headers = {"Authorization": f"Bearer {token}"}
            me = client.get("/api/v1/me", headers=headers)
            if role in {"USER", "OPERATOR"}:
                assert me.status_code == 200, me.text
                assert me.json()["tenant_id"] == str(tenant)
            else:
                assert me.status_code == 403, me.text
                expected = ("USER_DISABLED" if role == "DISABLED" else
                            "TENANT_DISABLED" if role == "DISABLED_TENANT" else
                            "MFA_EXTERNAL_REQUIREMENT")
                assert me.json()["reason_code"] == expected
            audit = client.get(f"/api/v1/tenants/{tenant}/audit-events", headers=headers)
            assert audit.status_code == (200 if role == "OPERATOR" else 403), audit.text
            admin_audit = client.get("/admin/v1/audit", headers=headers)
            # /admin/v1/audit is administrator-only; OPERATOR is never an admin.
            # Synthetic JWT amr=["mfa"] is not external administrator MFA proof.
            assert admin_audit.status_code == 403, admin_audit.text
            expected_admin_reason = {
                "USER": "ROLE_NOT_ALLOWED",
                "OPERATOR": "ROLE_NOT_ALLOWED",
                "ADMIN": "MFA_EXTERNAL_REQUIREMENT",
                "SUPER_ADMIN": "MFA_EXTERNAL_REQUIREMENT",
                "DISABLED": "USER_DISABLED",
                "DISABLED_TENANT": "TENANT_DISABLED",
            }[role]
            assert admin_audit.json()["reason_code"] == expected_admin_reason, admin_audit.text
            if role == "OPERATOR":
                denied = client.get(f"/api/v1/tenants/{other}/audit-events", headers=headers)
                assert denied.status_code == 404
                assert all(event["tenant_id"] == str(tenant) for event in audit.json())
        missing = client.get("/api/v1/me")
        assert missing.status_code == 401
        invalid = client.get("/api/v1/me", headers={"Authorization": "Bearer tampered"})
        assert invalid.status_code == 401
        expired_token = jwt.encode(
            {"iss": "https://idp.example.test", "sub": str(users["USER"]),
             "aud": "nex-api", "iat": int(time.time()) - 600, "exp": int(time.time()) - 300},
            private_key, algorithm="RS256", headers={"kid": "nex-test-key"},
        )
        prefix, signature = token.rsplit(".", 1)
        tampered_token = prefix + "." + ("a" if signature[0] != "a" else "b") + signature[1:]
        for bad_token in (expired_token, tampered_token):
            assert client.get("/api/v1/me", headers={
                "Authorization": f"Bearer {bad_token}",
            }).status_code == 401
        unknown = client.get("/api/v1/me", headers={
            "Authorization": f"Bearer {issue_token(private_key)}",
        })
        assert unknown.status_code == 403
        assert unknown.json()["reason_code"] == "IDENTITY_NOT_PROVISIONED"
        app.state.oidc_verifier = None
        dependency = client.get("/api/v1/me", headers={"Authorization": "Bearer x"})
        assert dependency.status_code == 503
        assert dependency.json()["reason_code"] == "SYSTEM_DEPENDENCY_UNHEALTHY"
        assert client.post("/api/v1/auth/logout").status_code == 501

    async def audit_evidence():
        engine = create_async_engine(target["migration"])
        async with engine.connect() as conn:
            codes = set((await conn.execute(text(
                "SELECT reason_code FROM audit_events"
            ))).scalars())
            assert {"AUTH_NOT_VALID", "USER_DISABLED", "TENANT_DISABLED",
                    "ROLE_NOT_ALLOWED", "MFA_EXTERNAL_REQUIREMENT",
                    "SYSTEM_DEPENDENCY_UNHEALTHY", "IDENTITY_NOT_PROVISIONED"} <= codes
            assert (await conn.execute(text(
                "SELECT count(*) FROM audit_events WHERE tenant_id=:tenant"
            ), {"tenant": SECURITY_TENANT_ID})).scalar() > 0
        await engine.dispose()
    asyncio.run(audit_evidence())


def test_readiness_schema_drift_and_absence(target):
    async def check():
        runtime = create_async_engine(target["app"])
        factory = async_sessionmaker(runtime)
        migrator = create_async_engine(target["migration"])
        assert await database_is_available(factory)
        async with migrator.begin() as connection:
            await connection.execute(text("ALTER TABLE users DROP CONSTRAINT users_role_check"))
        try:
            assert not await database_is_available(factory)
        finally:
            async with migrator.begin() as connection:
                await connection.execute(text(
                    "ALTER TABLE users ADD CONSTRAINT users_role_check "
                    "CHECK(role IN ('USER','OPERATOR','ADMIN','SUPER_ADMIN'))"
                ))
        async with migrator.begin() as connection:
            await connection.execute(text("ALTER TABLE alembic_version RENAME TO hidden_version"))
        try:
            assert not await database_is_available(factory)
        finally:
            async with migrator.begin() as connection:
                await connection.execute(text("ALTER TABLE hidden_version RENAME TO alembic_version"))
        await runtime.dispose()
        await migrator.dispose()
    asyncio.run(check())


def test_readiness_success_and_dependency_failures(target, signing_material):
    info = json.loads(subprocess.check_output([
        "docker", "inspect", PROJECT + "-redis-1"
    ]))[0]
    assert info["Config"]["Labels"]["com.docker.compose.project"] == PROJECT
    ip = info["NetworkSettings"]["Networks"][PROJECT + "_nex"]["IPAddress"]
    app = create_app(Settings(
        _env_file=None, database_url=target["app"],
        redis_url=f"redis://:synthetic-redis-only@{ip}:6379/0",
    ))
    _, jwks = signing_material
    with TestClient(app) as client:
        app.state.oidc_verifier = make_verifier(jwks)
        ready = client.get("/api/health/ready")
        assert ready.status_code == 200, ready.text
        assert ready.json()["status"] == "ready"
        redis = app.state.redis
        app.state.redis = None
        assert client.get("/api/health/ready").status_code == 503
        app.state.redis = redis

        async def outage():
            raise RuntimeError("synthetic provider unavailable")

        verifier = app.state.oidc_verifier
        verifier._fetch_jwks = outage
        assert client.get("/api/health/ready").status_code == 503
        app.state.session_factory = None
        assert client.get("/api/health/ready").status_code == 503
        # Restore for lifespan engine disposal.
        from nex_api.database import create_session_factory
        app.state.session_factory = create_session_factory(app.state.settings)


def test_upgrade_refuses_existing_identities_without_erasing_evidence(target):
    """Separate preserved legacy fixture; no destructive downgrade or guessed mappings."""
    import sys
    database = "nex_m1_legacy_upgrade_evidence"
    migration_url = target["migration"].removesuffix("/nex") + "/" + database

    async def prepare():
        engine = create_async_engine(target["bootstrap"], isolation_level="AUTOCOMMIT")
        async with engine.connect() as connection:
            exists = (await connection.execute(text(
                "SELECT 1 FROM pg_database WHERE datname=:name"
            ), {"name": database})).scalar()
            if not exists:
                await connection.execute(text(f"CREATE DATABASE {database} OWNER nex_migrator"))
        await engine.dispose()
    asyncio.run(prepare())
    environment = os.environ | {"MIGRATION_DATABASE_URL": migration_url}
    command = [sys.executable, "-m", "alembic", "-c", "apps/api/alembic.ini", "upgrade"]
    result = subprocess.run(command + ["0001_m1_foundation"], env=environment,
                            capture_output=True, text=True)
    assert result.returncode == 0, "Legacy fixture migration failed"

    tenant, user, event = uuid4(), uuid4(), uuid4()
    async def seed_and_snapshot():
        engine = create_async_engine(migration_url)
        async with engine.begin() as connection:
            await connection.execute(text(
                "INSERT INTO tenants(id,name) VALUES (:tenant,'Legacy synthetic fixture')"
            ), {"tenant": tenant})
            await connection.execute(text(
                "INSERT INTO users(id,issuer,subject) VALUES (:user,'https://legacy.test',:subject)"
            ), {"user": user, "subject": str(user)})
            await connection.execute(text("SELECT set_config('app.tenant_id',:tenant,true)"),
                                     {"tenant": str(tenant)})
            await connection.execute(text(
                "INSERT INTO audit_events(id,tenant_id,actor_id,action,outcome,details) "
                "VALUES (:event,:tenant,:user,'LEGACY_EVIDENCE','success',CAST(:details AS jsonb))"
            ), {"event": event, "tenant": tenant, "user": user,
                "details": json.dumps({"historical": True})})
        await engine.dispose()
    asyncio.run(seed_and_snapshot())
    result = subprocess.run(command + ["head"], env=environment, capture_output=True, text=True)
    assert result.returncode != 0
    assert "existing identities require explicitly approved" in result.stderr

    async def preserved():
        engine = create_async_engine(migration_url)
        async with engine.connect() as connection:
            await connection.execute(text("SELECT set_config('app.tenant_id',:tenant,true)"),
                                     {"tenant": str(tenant)})
            row = (await connection.execute(text(
                "SELECT action,outcome,details FROM audit_events WHERE id=:event"
            ), {"event": event})).one()
            assert row == ("LEGACY_EVIDENCE", "success", {"historical": True})
            assert (await connection.execute(text(
                "SELECT count(*) FROM users WHERE id=:user"
            ), {"user": user})).scalar() == 1
            assert (await connection.execute(text(
                "SELECT version_num FROM alembic_version"
            ))).scalar() == "0001_m1_foundation"
        await engine.dispose()
    asyncio.run(preserved())


def test_operator_provisioning_success_and_failure_have_durable_evidence(target, monkeypatch):
    from nex_api.bootstrap import provision_owner
    monkeypatch.setenv("MIGRATION_DATABASE_URL", target["migration"])
    monkeypatch.setenv("OIDC_ISSUER", "https://idp.example.test")
    monkeypatch.setenv("OIDC_AUDIENCE", "nex-api")
    monkeypatch.setenv("OIDC_JWKS_URL", "https://idp.example.test/jwks")
    subject = str(uuid4())

    async def check():
        inputs = {
            "issuer": "https://idp.example.test", "subject": subject,
            "tenant_name": "Synthetic operator fixture",
            "email": "synthetic@example.test", "role": "USER",
        }
        tenant = await provision_owner(**inputs)
        with pytest.raises(ValueError):
            await provision_owner(**inputs)
        engine = create_async_engine(target["migration"])
        async with engine.connect() as connection:
            assert (await connection.execute(text(
                "SELECT count(*) FROM audit_events WHERE tenant_id=:tenant "
                "AND action='INITIAL_OWNER_PROVISIONED' AND outcome='SUCCESS'"
            ), {"tenant": tenant})).scalar() == 1
            assert (await connection.execute(text(
                "SELECT count(*) FROM audit_events WHERE tenant_id=:tenant "
                "AND action='INITIAL_OWNER_PROVISIONING_FAILED' AND outcome='FAILED'"
            ), {"tenant": SECURITY_TENANT_ID})).scalar() >= 1
        await engine.dispose()
    asyncio.run(check())