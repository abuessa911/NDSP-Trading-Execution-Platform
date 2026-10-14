"""NDSP M2-B L4 source-issued test vectors -> independent NEX verifier/ledger.

No production NDSP requests or real user data. Tests are scoped to approved
synthetic vectors from an isolated Contabo CDS source-slice module.
PostgreSQL test opens ONLY a fresh localhost 'nex_m2b_preview' CI database.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

import asyncpg
import pytest

from nex_api.ndsp_contract_preview import NDSPContractRejected
from nex_api.ndsp_identity_ledger_l2_preview import accept_synthetic_signed_decision
from nex_api.ndsp_source_binding_preview import verify_test_only_source_binding

ROOT = Path(__file__).parent / "fixtures" / "ndsp_l4_source_publisher"
NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)
TENANT_A = UUID("a53d4c75-d39e-4cd8-894b-7ed173e57226")
TENANT_B = UUID("7cd7c91b-970a-43cb-b9a0-1edff7a0110d")
APP_DSN = (
    "postgresql://m2b_l2_preview_app:synthetic-m2b-l2-app-only"
    "@127.0.0.1:5432/nex_m2b_preview"
)
ADMIN_DSN = os.environ.get("M2B_L4_ADMIN_DSN", "")


def inputs(version: int) -> tuple[bytes, dict[str, object], dict[str, bytes]]:
    signed = (ROOT / f"signed_decision_v{version}.json").read_bytes()
    source: dict[str, object] = json.loads(
        (ROOT / f"source_metadata_v{version}.json").read_text(),
    )
    trust = json.loads((ROOT / "trusted_test_public_key.json").read_text())
    assert trust["profile_status"] == "PROPOSED_SYNTHETIC_TEST_ONLY"
    assert trust["private_key_persisted"] is False
    assert trust["algorithm"] == "Ed25519"
    keys: dict[str, bytes] = {
        trust["key_id"]: base64.b64decode(trust["public_key_base64"], validate=True),
    }
    assert len(next(iter(keys.values()))) == 32
    assert source["decision_id"] == "CD-TEST-L4-20261014"
    return signed, source, keys


def test_two_independent_ndsp_issuer_versions_verify_without_real_data() -> None:
    ids = []
    hashes = []
    key_ids = []
    for version in (1, 2):
        raw, source, keys = inputs(version)
        verified = verify_test_only_source_binding(
            raw, public_keys=keys, source=source, now_utc=NOW,
        )
        ids.append(verified.decision_id)
        hashes.append(verified.evidence_hash)
        key_ids.append(next(iter(keys)))
        assert verified.decision_version == version
        assert verified.asset == "BTCUSDT"
        assert verified.execution_authorized is False
        assert verified.direction == "FLAT"
        assert verified.decision_state == "BLOCKED"
        assert verified.source_environment == "test"
        # Private metadata and the original source text ID are not exported
        # in the frozen NDSP-NEX-1.0 signed envelope.
        assert b"CD-TEST-L4-20261014" not in raw
        assert b"synthetic_evidence_hash" not in raw
    assert ids[0] == ids[1]
    assert hashes[0] != hashes[1]
    assert key_ids[0] == key_ids[1]


@pytest.mark.parametrize("change", ["version", "identity", "private"])
def test_source_change_without_new_signature_fails_closed(change: str) -> None:
    raw, source, keys = inputs(1)
    source = dict(source)
    if change == "version":
        source["version"] = 2
    elif change == "identity":
        source["decision_id"] = "CD-TEST-OTHER-20261014"
    else:
        source["visibility"] = "private"
    with pytest.raises(NDSPContractRejected):
        verify_test_only_source_binding(
            raw, public_keys=keys, source=source, now_utc=NOW,
        )


def test_public_test_key_is_pinned_not_payload_supplied() -> None:
    raw, source, _ = inputs(1)
    with pytest.raises(NDSPContractRejected, match="NDSP_KEY_NOT_APPROVED"):
        verify_test_only_source_binding(
            raw, public_keys={}, source=source, now_utc=NOW,
        )


def _safe_dsn() -> str:
    url = urlsplit(ADMIN_DSN)
    if (
        url.scheme != "postgresql"
        or url.hostname not in ("localhost", "127.0.0.1")
        or url.port != 5432
        or url.path != "/nex_m2b_preview"
        or url.username != "m2b_fixture"
        or url.password != "synthetic-m2b-admin-only"
        or url.query or url.fragment
    ):
        raise RuntimeError("REFUSE_UNSAFE_L4_DATABASE")
    return ADMIN_DSN


async def _proof_postgresql() -> None:
    admin = await asyncpg.connect(_safe_dsn(), timeout=3)
    pool: asyncpg.Pool | None = None
    owned_role = False
    owned_schema = False
    try:
        assert await admin.fetchval("SELECT current_database()") == "nex_m2b_preview"
        assert await admin.fetchval(
            "SELECT rolsuper FROM pg_roles WHERE rolname=current_user",
        ) is True
        if await admin.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname='m2b_l2_preview_app'",
        ) or await admin.fetchval(
            "SELECT 1 FROM pg_namespace WHERE nspname='m2b_l2_preview'",
        ):
            raise RuntimeError("REFUSE_REUSE_OF_L4_DISPOSABLE_SCHEMA")

        await admin.execute(
            "CREATE ROLE m2b_l2_preview_app LOGIN "
            "PASSWORD 'synthetic-m2b-l2-app-only' "
            "NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE",
        )
        owned_role = True
        ddl = (Path(__file__).resolve().parents[3]
               / "infra/testing/m2b_l2_identity_ledger_preview.sql").read_text()
        await admin.execute(ddl)
        owned_schema = True
        pool = await asyncpg.create_pool(
            dsn=APP_DSN, min_size=1, max_size=4, timeout=3, command_timeout=5,
        )
        first, src1, keys = inputs(1)
        second, src2, keys2 = inputs(2)
        assert keys == keys2

        async def accept(tenant: UUID, raw: bytes, source: dict[str, object]):
            assert pool is not None
            return await accept_synthetic_signed_decision(
                pool, tenant_id=tenant, raw=raw, source=source,
                public_keys=keys, now_utc=NOW,
            )

        r1 = await accept(TENANT_A, first, src1)
        assert r1.result == "STORED"
        assert (await accept(TENANT_A, first, src1)).result == "IDEMPOTENT"
        r2 = await accept(TENANT_A, second, src2)
        assert r2.result == "STORED" and r2.binding_id == r1.binding_id
        assert (await accept(TENANT_A, second, src2)).result == "IDEMPOTENT"

        with pytest.raises(NDSPContractRejected, match="NDSP_L2_STALE_VERSION"):
            await accept(TENANT_A, first, src1)

        other = await accept(TENANT_B, first, src1)
        assert other.binding_id != r1.binding_id

        async with pool.acquire() as conn:
            assert await conn.fetchval(
                "SELECT count(*) FROM m2b_l2_preview.decision_versions",
            ) == 0
            async with conn.transaction():
                await conn.execute(
                    "SELECT set_config('m2b_l2.tenant_id',$1,true)", str(TENANT_A),
                )
                versions = await conn.fetch(
                    "SELECT decision_version FROM m2b_l2_preview.decision_versions "
                    "WHERE binding_id=$1 ORDER BY decision_version",
                    r1.binding_id,
                )
                assert [row["decision_version"] for row in versions] == [1, 2]
                name = await conn.fetchval(
                    "SELECT source_decision_id FROM m2b_l2_preview.decision_bindings "
                    "WHERE binding_id=$1", r1.binding_id,
                )
                assert name == "CD-TEST-L4-20261014"
                assert await conn.fetchval(
                    "SELECT COUNT(*) FROM m2b_l2_preview.decision_bindings "
                    "WHERE tenant_id=$1", TENANT_B,
                ) == 0

        await pool.close()
        pool = None
        pool = await asyncpg.create_pool(
            dsn=APP_DSN, min_size=1, max_size=2, timeout=3,
        )
        assert (await accept(TENANT_A, second, src2)).result == "IDEMPOTENT"
        print("M2B_L4_CROSS_LANGUAGE_PERSISTED_REPLAY=PASS")
    finally:
        if pool is not None:
            await pool.close()
        if owned_schema:
            await admin.execute("DROP SCHEMA m2b_l2_preview CASCADE")
        if owned_role:
            await admin.execute("DROP ROLE m2b_l2_preview_app")
        await admin.close()


@pytest.mark.skipif(
    not ADMIN_DSN, reason="fresh loopback PostgreSQL service required",
)
def test_disposable_postgres_accepts_source_signed_versions_only() -> None:
    asyncio.run(_proof_postgresql())
