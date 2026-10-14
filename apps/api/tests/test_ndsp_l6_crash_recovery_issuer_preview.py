"""Disposable PostgreSQL crash recovery with signed TEST issuer and TEST IdP.

No access to production NDSP/CDS databases, user accounts, real IdP,
private production keys, exchange or live execution. Secrets below are
hard-coded synthetic CI fixtures, NOT shared service credentials.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import asyncpg
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from nex_api.ndsp_contract_preview import NDSPContractRejected
from nex_api.ndsp_source_export_l5_preview import AUDIENCE, ISSUER
from nex_api.ndsp_source_issuer_l6_preview import (
    read_latest_synthetic_signed,
    reserve_synthetic_revision,
    seal_synthetic_revision,
)

FIXTURES = Path(__file__).parent / "fixtures" / "ndsp_l4_source_publisher"
SOURCE_ID = "CD-TEST-L4-20261014"
TENANT = UUID("b2f8bd7e-3489-40ea-b099-cf7b927c1b33")
OTHER_TENANT = UUID("cf5b6c26-2091-4ea1-92cd-0b1939dccf8a")
NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)
ADMIN_DSN = os.environ.get("M2B_L6_ADMIN_DSN", "")
APP_DSN = (
    "postgresql://m2b_l6_preview_app:synthetic-l6-app-only"
    "@127.0.0.1:5432/nex_m2b_preview"
)


def _dsn() -> str:
    parsed = urlsplit(ADMIN_DSN)
    if (
        parsed.scheme != "postgresql"
        or parsed.hostname not in ("127.0.0.1", "localhost")
        or parsed.port != 5432
        or parsed.path != "/nex_m2b_preview"
        or parsed.username != "m2b_fixture"
        or parsed.password != "synthetic-m2b-admin-only"
        or parsed.query or parsed.fragment
    ):
        raise RuntimeError("REFUSE_UNSAFE_L6_DATABASE")
    return ADMIN_DSN


def _fixtures(version: int) -> tuple[bytes, dict[str, object], dict[str, bytes]]:
    raw = (FIXTURES / f"signed_decision_v{version}.json").read_bytes()
    metadata: dict[str, object] = json.loads(
        (FIXTURES / f"source_metadata_v{version}.json").read_text(),
    )
    metadata.pop("version")
    trust = json.loads((FIXTURES / "trusted_test_public_key.json").read_text())
    assert trust["private_key_persisted"] is False
    keys = {
        trust["key_id"]: base64.b64decode(trust["public_key_base64"], validate=True),
    }
    return raw, metadata, keys


def _idp_keys() -> tuple[bytes, bytes]:
    key = Ed25519PrivateKey.generate()
    return (
        key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
        key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
        ),
    )


def _token(key: bytes, tenant: UUID, scope: str, **modifications: object) -> str:
    now = datetime.now(timezone.utc)
    claims: dict[str, object] = {
        "iss": ISSUER, "aud": AUDIENCE, "sub": "test-principal-l6",
        "iat": int((now - timedelta(seconds=5)).timestamp()),
        "nbf": int((now - timedelta(seconds=5)).timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "source_environment": "test", "tenant_id": str(tenant), "scope": scope,
    }
    claims.update(modifications)
    return jwt.encode(claims, key, algorithm="EdDSA")


def test_l6_non_ci_database_refused() -> None:
    if not ADMIN_DSN:
        with pytest.raises(RuntimeError, match="REFUSE_UNSAFE_L6_DATABASE"):
            _dsn()


def test_l6_has_no_runtime_http_order_or_live_db_connector() -> None:
    import nex_api.ndsp_source_issuer_l6_preview as module

    for name in ("place_order", "submit_order", "create_app", "fetch_real_ndsp"):
        assert not hasattr(module, name)


async def _proof() -> None:
    # Refuse unsafe DSN before any connection.
    admin = await asyncpg.connect(dsn=_dsn(), timeout=3)
    pool: asyncpg.Pool | None = None
    created_role = False
    created_schema = False
    try:
        assert await admin.fetchval("SELECT current_database()") == "nex_m2b_preview"
        assert await admin.fetchval(
            "SELECT rolsuper FROM pg_roles WHERE rolname=current_user",
        ) is True
        if await admin.fetchval(
            "SELECT 1 FROM pg_namespace WHERE nspname='m2b_l6_preview'",
        ) or await admin.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname='m2b_l6_preview_app'",
        ):
            raise RuntimeError("REFUSE_REUSE_OF_L6_DATABASE_FIXTURES")
        await admin.execute(
            "CREATE ROLE m2b_l6_preview_app LOGIN PASSWORD "
            "'synthetic-l6-app-only' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE",
        )
        created_role = True
        ddl = (Path(__file__).resolve().parents[3]
               / "infra/testing/m2b_l6_source_issuer_journal_preview.sql").read_text()
        await admin.execute(ddl)
        created_schema = True
        pool = await asyncpg.create_pool(
            dsn=APP_DSN, min_size=1, max_size=8, timeout=3, command_timeout=6,
        )

        idp_priv, idp_pub = _idp_keys()
        wrong_idp_priv, _ = _idp_keys()
        owners = {SOURCE_ID: TENANT}  # test-only SERVER-owned fixture, not request arg
        reserve_token = _token(idp_priv, TENANT, "ndsp.source.reserve")
        seal_token = _token(idp_priv, TENANT, "ndsp.source.seal")
        read_token = _token(idp_priv, TENANT, "ndsp.source.read")
        other_token = _token(idp_priv, OTHER_TENANT, "ndsp.source.reserve")
        first, source1, keys = _fixtures(1)
        second, source2, keys2 = _fixtures(2)
        assert keys == keys2
        operation_1, operation_2 = uuid4(), uuid4()

        async def reserve(
            token: str, operation: UUID, source: dict[str, object],
            ownership: dict[str, UUID] = owners,
        ):
            assert pool is not None
            return await reserve_synthetic_revision(
                pool, token=token, idp_public_key_pem=idp_pub,
                trusted_source_owners=ownership, operation_id=operation,
                source=source, now_utc=NOW,
            )

        async def seal(token: str, ver: int, raw: bytes):
            assert pool is not None
            return await seal_synthetic_revision(
                pool, token=token, idp_public_key_pem=idp_pub,
                trusted_source_owners=owners, source_decision_id=SOURCE_ID,
                version=ver, signed_bytes=raw, trusted_signer_public_keys=keys,
                now_utc=NOW,
            )

        async def read(token: str = read_token, now: datetime = NOW):
            assert pool is not None
            return await read_latest_synthetic_signed(
                pool, token=token, idp_public_key_pem=idp_pub,
                trusted_source_owners=owners, source_decision_id=SOURCE_ID,
                now_utc=now,
            )

        # Concurrent same operation: unique durable version = 1.
        parallel = await asyncio.gather(*[
            reserve(reserve_token, operation_1, source1) for _ in range(6)
        ])
        assert sum(x.status == "RESERVED" for x in parallel) == 1
        assert sum(x.status == "IDEMPOTENT" for x in parallel) == 5
        assert {x.version for x in parallel} == {1}
        with pytest.raises(NDSPContractRejected, match="NDSP_L6_SOURCE_PENDING_SIGNATURE"):
            await read()
        with pytest.raises(NDSPContractRejected, match="NDSP_L6_PREDECESSOR_UNSIGNED"):
            await reserve(reserve_token, operation_2, source2)
        with pytest.raises(NDSPContractRejected, match="NDSP_L6_SOURCE_OWNER_DENIED"):
            await reserve(other_token, uuid4(), source1)
        with pytest.raises(NDSPContractRejected, match="NDSP_L5_UNTRUSTED_IDENTITY"):
            await reserve(_token(wrong_idp_priv, TENANT, "ndsp.source.reserve"), uuid4(), source1)
        with pytest.raises(NDSPContractRejected, match="NDSP_L5_SCOPE_OR_ENVIRONMENT_DENIED"):
            await reserve(read_token, uuid4(), source1)
        with pytest.raises(NDSPContractRejected, match="NDSP_L6_OPERATION_REUSED_WITH_OTHER_SOURCE"):
            await reserve(reserve_token, operation_1, source2)

        # Simulate process death after reservation before signature: reconnect.
        await pool.close()
        pool = await asyncpg.create_pool(
            dsn=APP_DSN, min_size=1, max_size=4, timeout=3,
        )
        retry = await reserve(reserve_token, operation_1, source1)
        assert retry.status == "IDEMPOTENT" and retry.version == 1
        with pytest.raises(NDSPContractRejected, match="NDSP_L6_SOURCE_PENDING_SIGNATURE"):
            await read()

        with pytest.raises(NDSPContractRejected, match="NDSP_L6_REVISION_NOT_RESERVED"):
            await seal(seal_token, 2, second)
        with pytest.raises(NDSPContractRejected):
            await seal(seal_token, 1, second)
        assert (await seal(seal_token, 1, first)).status == "SEALED"
        assert (await seal(seal_token, 1, first)).status == "IDEMPOTENT"
        assert (await read()).signed_bytes == first

        # Source ID retains original CD while versions strictly increase.
        reserved_two = await reserve(reserve_token, operation_2, source2)
        assert reserved_two.status == "RESERVED" and reserved_two.version == 2
        with pytest.raises(NDSPContractRejected, match="NDSP_L6_SOURCE_PENDING_SIGNATURE"):
            await read()
        assert (await seal(seal_token, 2, second)).status == "SEALED"
        newest = await read()
        assert newest.signed_bytes == second
        assert newest.version == 2
        assert newest.execution_authorized is False
        with pytest.raises(NDSPContractRejected, match="NDSP_L6_SOURCE_EXPIRED"):
            await read(now=datetime(2026, 10, 15, 10, tzinfo=timezone.utc))

        async with pool.acquire() as conn:
            assert await conn.fetchval(
                "SELECT count(*) FROM m2b_l6_preview.source_revisions",
            ) == 0
            assert await conn.fetchval(
                "SELECT count(*) FROM m2b_l6_preview.sealed_artifacts",
            ) == 0
            async with conn.transaction():
                await conn.execute(
                    "SELECT set_config('m2b_l6.tenant_id',$1,true)", str(TENANT),
                )
                numbers = await conn.fetch(
                    "SELECT decision_version FROM m2b_l6_preview.source_revisions "
                    "WHERE source_decision_id=$1 ORDER BY decision_version", SOURCE_ID,
                )
                assert [x["decision_version"] for x in numbers] == [1, 2]
                assert await conn.fetchval(
                    "SELECT count(*) FROM m2b_l6_preview.sealed_artifacts",
                ) == 2
                for table in ("source_revisions", "sealed_artifacts"):
                    for op in ("UPDATE", "DELETE", "TRUNCATE"):
                        assert await conn.fetchval(
                            "SELECT has_table_privilege(current_user,$1,$2)",
                            "m2b_l6_preview." + table, op,
                        ) is False
                assert await conn.fetchval(
                    "SELECT rolsuper OR rolbypassrls FROM pg_roles "
                    "WHERE rolname=current_user",
                ) is False

        await pool.close()
        pool = await asyncpg.create_pool(
            dsn=APP_DSN, min_size=1, max_size=3, timeout=3,
        )
        assert (await read()).signed_bytes == second
        assert (await reserve(reserve_token, operation_2, source2)).status == "IDEMPOTENT"
        print("M2B_L6_DURABLE_RESERVATION_SIGNATURE_CRASH_RECOVERY=PASS")
    finally:
        if pool is not None:
            await pool.close()
        if created_schema:
            await admin.execute("DROP SCHEMA m2b_l6_preview CASCADE")
        if created_role:
            await admin.execute("DROP ROLE m2b_l6_preview_app")
        await admin.close()


@pytest.mark.skipif(
    not ADMIN_DSN, reason="Requires fresh localhost PostgreSQL 16 in GitHub CI",
)
def test_disposable_issuer_journal_recovery_and_authorization() -> None:
    asyncio.run(_proof())
