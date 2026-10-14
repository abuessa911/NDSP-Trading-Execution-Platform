"""M2-B L5 disposable localhost PostgreSQL + cryptographically signed TEST IdP.

Absolutely no production credentials, real NDSP records, actual identity
provider, HTTP server or order routes. All keys are ephemeral per test run.
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

import asyncpg
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from nex_api.ndsp_contract_preview import NDSPContractRejected
from nex_api.ndsp_source_export_l5_preview import (
    AUDIENCE,
    ISSUER,
    append_synthetic_source_event,
    private_read_synthetic_envelope,
)

ROOT = Path(__file__).parent / "fixtures" / "ndsp_l4_source_publisher"
NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)
A = UUID("51c0d169-9bbd-46bc-a2e8-5e3b8b7b1306")
B = UUID("38d81a65-3b1f-4f50-b32f-756155f593cc")
SOURCE = "CD-TEST-L4-20261014"
ADMIN_DSN = os.environ.get("M2B_L5_ADMIN_DSN", "")
APP_DSN = (
    "postgresql://m2b_l5_preview_app:synthetic-l5-app-only"
    "@127.0.0.1:5432/nex_m2b_preview"
)


def _signed(version: int) -> tuple[bytes, dict[str, object], dict[str, bytes]]:
    import base64

    raw = (ROOT / f"signed_decision_v{version}.json").read_bytes()
    source: dict[str, object] = json.loads(
        (ROOT / f"source_metadata_v{version}.json").read_text(),
    )
    trust = json.loads((ROOT / "trusted_test_public_key.json").read_text())
    assert trust["profile_status"] == "PROPOSED_SYNTHETIC_TEST_ONLY"
    keys = {
        trust["key_id"]: base64.b64decode(trust["public_key_base64"], validate=True),
    }
    return raw, source, keys


def _idp() -> tuple[bytes, bytes]:
    signer = Ed25519PrivateKey.generate()
    private = signer.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public = signer.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private, public


def _token(private: bytes, tenant: UUID, scope: str, **changes: object) -> str:
    now = datetime.now(timezone.utc)
    claims: dict[str, object] = {
        "iss": ISSUER, "aud": AUDIENCE, "sub": "test-principal-service",
        "iat": int((now - timedelta(seconds=4)).timestamp()),
        "nbf": int((now - timedelta(seconds=4)).timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "tenant_id": str(tenant), "scope": scope,
        "source_environment": "test",
    }
    claims.update(changes)
    return jwt.encode(claims, private, algorithm="EdDSA")


def _db_guard() -> str:
    d = urlsplit(ADMIN_DSN)
    if (d.scheme != "postgresql" or d.hostname not in ("localhost", "127.0.0.1")
            or d.port != 5432 or d.path != "/nex_m2b_preview"
            or d.username != "m2b_fixture"
            or d.password != "synthetic-m2b-admin-only"
            or d.query or d.fragment):
        raise RuntimeError("REFUSE_NONDISPOSABLE_L5_DATABASE")
    return ADMIN_DSN


def test_non_ci_dsn_guard_denies_missing_database() -> None:
    if not ADMIN_DSN:
        with pytest.raises(RuntimeError, match="REFUSE_NONDISPOSABLE_L5_DATABASE"):
            _db_guard()


def test_no_production_http_or_order_adapter() -> None:
    import nex_api.ndsp_source_export_l5_preview as module

    for action in ("place_order", "submit_order", "fetch_real_ndsp", "create_app"):
        assert not hasattr(module, action)


async def _exercise() -> None:
    # This guard runs BEFORE opening ANY database connection.
    dsn = _db_guard()
    admin = await asyncpg.connect(dsn=dsn, timeout=3)
    pool: asyncpg.Pool | None = None
    made_role = False
    made_schema = False
    try:
        assert await admin.fetchval("SELECT current_database()") == "nex_m2b_preview"
        assert await admin.fetchval(
            "SELECT rolsuper FROM pg_roles WHERE rolname=current_user",
        ) is True
        if await admin.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname='m2b_l5_preview_app'",
        ) or await admin.fetchval(
            "SELECT 1 FROM pg_namespace WHERE nspname='m2b_l5_preview'",
        ):
            raise RuntimeError("REFUSE_EXISTING_L5_PREVIEW_OBJECTS")
        await admin.execute(
            "CREATE ROLE m2b_l5_preview_app LOGIN PASSWORD "
            "'synthetic-l5-app-only' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE",
        )
        made_role = True
        ddl = (Path(__file__).resolve().parents[3]
               / "infra/testing/m2b_l5_source_export_preview.sql").read_text()
        await admin.execute(ddl)
        made_schema = True

        pool = await asyncpg.create_pool(
            dsn=APP_DSN, min_size=1, max_size=8, timeout=3, command_timeout=6,
        )
        private, trusted_public = _idp()
        bad_private, _ = _idp()
        write_a = _token(private, A, "ndsp.source.append")
        read_a = _token(private, A, "ndsp.source.read")
        write_b = _token(private, B, "ndsp.source.append")
        read_b = _token(private, B, "ndsp.source.read")
        v1, src1, keys = _signed(1)
        v2, src2, keys2 = _signed(2)
        assert keys == keys2

        async def append(tok: str, raw: bytes, src: dict[str, object]):
            assert pool is not None
            return await append_synthetic_source_event(
                pool, token=tok, idp_public_key_pem=trusted_public,
                raw_signed=raw, source=src, source_public_keys=keys,
                trusted_source_owners={SOURCE: A}, now_utc=NOW,
            )

        async def read(tok: str, clock: datetime = NOW):
            assert pool is not None
            return await private_read_synthetic_envelope(
                pool, token=tok, idp_public_key_pem=trusted_public,
                source_decision_id=SOURCE, now_utc=clock,
            )

        parallel = await asyncio.gather(*[
            append(write_a, v1, src1) for _ in range(5)
        ])
        assert sum(row.result == "STORED" for row in parallel) == 1
        assert sum(row.result == "IDEMPOTENT" for row in parallel) == 4
        assert (await read(read_a)).document == v1
        assert (await append(write_a, v2, src2)).result == "STORED"
        assert (await append(write_a, v2, src2)).result == "IDEMPOTENT"
        latest = await read(read_a)
        assert latest.document == v2 and latest.execution_authorized is False

        with pytest.raises(NDSPContractRejected, match="NDSP_L5_STALE_VERSION"):
            await append(write_a, v1, src1)
        with pytest.raises(NDSPContractRejected, match="NDSP_L5_NOT_FOUND_OR_UNAUTHORIZED"):
            await read(read_b)
        with pytest.raises(NDSPContractRejected, match="NDSP_L5_SCOPE_OR_ENVIRONMENT_DENIED"):
            await read(write_a)
        with pytest.raises(NDSPContractRejected, match="NDSP_L5_SCOPE_OR_ENVIRONMENT_DENIED"):
            await append(read_a, v1, src1)
        with pytest.raises(NDSPContractRejected, match="NDSP_L5_UNTRUSTED_IDENTITY"):
            await read(_token(bad_private, A, "ndsp.source.read"))
        with pytest.raises(NDSPContractRejected, match="NDSP_L5_UNTRUSTED_IDENTITY"):
            await read(_token(private, A, "ndsp.source.read", aud="wrong-audience"))
        with pytest.raises(NDSPContractRejected, match="NDSP_L5_UNTRUSTED_IDENTITY"):
            await read(_token(private, A, "ndsp.source.read", exp=1))
        with pytest.raises(NDSPContractRejected, match="NDSP_L5_TENANT_INVALID"):
            await read(_token(private, A, "ndsp.source.read", tenant_id=str(UUID(int=0))))
        with pytest.raises(NDSPContractRejected, match="NDSP_L5_SOURCE_EXPIRED"):
            await read(read_a, datetime(2026, 10, 15, 10, tzinfo=timezone.utc))

        # Even a valid signed tenant B token CANNOT publish tenant A's source.
        with pytest.raises(NDSPContractRejected, match="NDSP_L5_SOURCE_OWNER_MISMATCH"):
            await append(write_b, v1, src1)
        with pytest.raises(NDSPContractRejected, match="NDSP_L5_NOT_FOUND_OR_UNAUTHORIZED"):
            await read(read_b)

        # Direct raw SQL from no tenant context must return nothing (test RLS).
        async with pool.acquire() as conn:
            assert await conn.fetchval(
                "SELECT COUNT(*) FROM m2b_l5_preview.source_issuance_events",
            ) == 0
            async with conn.transaction():
                await conn.execute(
                    "SELECT set_config('m2b_l5.tenant_id',$1,true)", str(A),
                )
                versions = await conn.fetch(
                    "SELECT decision_version FROM m2b_l5_preview.source_issuance_events "
                    "WHERE source_decision_id=$1 ORDER BY decision_version", SOURCE,
                )
                assert [r["decision_version"] for r in versions] == [1, 2]
                assert await conn.fetchval(
                    "SELECT COUNT(*) FROM m2b_l5_preview.source_issuance_events "
                    "WHERE tenant_id=$1", B,
                ) == 0
                for operation in ("UPDATE", "DELETE", "TRUNCATE"):
                    assert await conn.fetchval(
                        "SELECT has_table_privilege(current_user,$1,$2)",
                        "m2b_l5_preview.source_issuance_events", operation,
                    ) is False
                assert await conn.fetchval(
                    "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user",
                ) is False

        # Real durable persistence test: close pool and reconnect.
        await pool.close()
        pool = await asyncpg.create_pool(
            dsn=APP_DSN, min_size=1, max_size=3, timeout=3, command_timeout=6,
        )
        assert (await read(read_a)).document == v2
        assert (await append(write_a, v2, src2)).result == "IDEMPOTENT"
        print("M2B_L5_DISPOSABLE_DURABLE_AUTH_READ_GATE=PASS")
    finally:
        if pool is not None:
            await pool.close()
        if made_schema:
            await admin.execute("DROP SCHEMA m2b_l5_preview CASCADE")
        if made_role:
            await admin.execute("DROP ROLE m2b_l5_preview_app")
        await admin.close()


@pytest.mark.skipif(
    not ADMIN_DSN, reason="requires fresh CI disposable loopback PostgreSQL",
)
def test_pinned_idp_signed_tenant_scopes_durable_source_events() -> None:
    asyncio.run(_exercise())
