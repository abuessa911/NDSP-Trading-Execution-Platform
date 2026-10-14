"""M2-B L2: test-only issuer-verified append-only identity/version ledger.

PostgreSQL is disposable localhost ONLY; no NDSP/NEX production DB/URLs.
No real order execution, auth, tenant mapping, or issuer key is included.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID, uuid5

import asyncpg
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from nex_api.ndsp_contract_preview import NDSPContractRejected
from nex_api.ndsp_identity_ledger_l2_preview import accept_synthetic_signed_decision
from nex_api.ndsp_source_binding_preview import (
    TEST_NAMESPACE,
    verify_test_only_source_binding,
)

ADMIN_DSN = os.environ.get("M2B_L2_ADMIN_DSN", "")
NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)
TENANT_A = UUID("71e0bfe0-4f9b-4868-98a8-395dcc9e030d")
TENANT_B = UUID("1d669cdb-9c53-4398-a85a-ea9f4f1e7239")
APP_DSN = (
    "postgresql://m2b_l2_preview_app:synthetic-m2b-l2-app-only"
    "@127.0.0.1:5432/nex_m2b_preview"
)


def _safe_admin_dsn() -> str:
    uri = urlsplit(ADMIN_DSN)
    if (uri.scheme != "postgresql" or uri.hostname not in ("127.0.0.1", "localhost")
            or uri.port != 5432 or uri.path != "/nex_m2b_preview"
            or uri.username != "m2b_fixture"
            or uri.password != "synthetic-m2b-admin-only"
            or uri.query or uri.fragment):
        raise RuntimeError("REFUSE_UNSAFE_L2_DATABASE")
    return ADMIN_DSN


def _sign(
    signer: Ed25519PrivateKey, version: int = 1, *,
    source_id: str = "CD-TEST-20261014", published_at: str = "2026-10-14T10:00:00Z",
) -> tuple[bytes, dict[str, object]]:
    source: dict[str, object] = {
        "decision_id": source_id,
        "decision_state": "Published",
        "visibility": "public",
        "market": "CRYPTO",
        "symbol": "BTCUSDT",
        "timeframe": "4H",
        "version": version,
        "completed_at": "2026-10-14T09:00:00Z",
        "published_at": published_at,
        "expires_at": "2026-10-15T10:00:00Z",
    }
    source_bytes = json.dumps(
        source, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()
    doc = {
        "contract_version": "NDSP-NEX-1.0",
        "decision_id": str(uuid5(TEST_NAMESPACE, source_id)),
        "decision_version": version,
        "asset": "BTCUSDT",
        "market": "CRYPTO",
        "timeframe": "4H",
        "direction": "FLAT",
        "decision_state": "BLOCKED",
        "scenario_state": "UNDER_MONITORING",
        "risk_class": "BLOCKED",
        "valid_from": "2026-10-14T10:00:00Z",
        "valid_until": "2026-10-15T10:00:00Z",
        "issued_at": "2026-10-14T11:00:00Z",
        "source_system": "NDSP",
        "source_environment": "test",
        "evidence_hash": "sha256:" + hashlib.sha256(source_bytes).hexdigest(),
        "key_id": "ephemeral-l2",
    }
    signed = json.dumps(
        doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()
    doc["signature"] = base64.b64encode(signer.sign(signed)).decode("ascii")
    return json.dumps(doc, separators=(",", ":")).encode(), source


def _public_keys(signer: Ed25519PrivateKey) -> dict[str, bytes]:
    return {"ephemeral-l2": signer.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )}


def test_valid_signed_synthetic_input_is_blocked_for_execution() -> None:
    signer = Ed25519PrivateKey.generate()
    raw, source = _sign(signer)
    verified = verify_test_only_source_binding(
        raw, public_keys=_public_keys(signer), source=source, now_utc=NOW,
    )
    assert verified.decision_version == 1
    assert verified.execution_authorized is False
    assert source["decision_id"] == "CD-TEST-20261014"


def test_mutated_signed_fields_are_denied_before_database() -> None:
    signer = Ed25519PrivateKey.generate()
    raw, source = _sign(signer)
    changed = json.loads(raw)
    changed["decision_version"] = 100
    with pytest.raises(NDSPContractRejected, match="NDSP_SIGNATURE_INVALID"):
        verify_test_only_source_binding(
            json.dumps(changed).encode(), source=source,
            public_keys=_public_keys(signer), now_utc=NOW,
        )
    with pytest.raises(NDSPContractRejected, match="NDSP_KEY_NOT_APPROVED"):
        verify_test_only_source_binding(
            raw, source=source, public_keys={}, now_utc=NOW,
        )


def test_disposable_guard_denies_production_credentials() -> None:
    if not ADMIN_DSN:
        with pytest.raises(RuntimeError, match="REFUSE_UNSAFE_L2_DATABASE"):
            _safe_admin_dsn()


def test_preview_module_has_no_api_or_trading_surface() -> None:
    import nex_api.ndsp_identity_ledger_l2_preview as code

    for name in ("submit_order", "fetch_decision", "publish_to_ndsp", "place_order"):
        assert not hasattr(code, name)
    assert code.SOURCE_ISSUER == "ndsp-source-slice-test"


async def _run_postgres_proof() -> None:
    # Validate the entire DSN BEFORE opening any connection.
    dsn = _safe_admin_dsn()
    admin = await asyncpg.connect(dsn=dsn, timeout=3)
    pool = None
    created_role = False
    created_schema = False
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
            raise RuntimeError("REFUSE_EXISTING_L2_TEST_RESOURCES")

        await admin.execute(
            "CREATE ROLE m2b_l2_preview_app LOGIN "
            "PASSWORD 'synthetic-m2b-l2-app-only' "
            "NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE",
        )
        created_role = True
        ddl = (Path(__file__).resolve().parents[3]
               / "infra/testing/m2b_l2_identity_ledger_preview.sql").read_text()
        await admin.execute(ddl)
        created_schema = True
        pool = await asyncpg.create_pool(
            dsn=APP_DSN, min_size=1, max_size=6, command_timeout=5, timeout=3,
        )
        signer = Ed25519PrivateKey.generate()
        keys = _public_keys(signer)
        one, src_one = _sign(signer, 1)
        two, src_two = _sign(signer, 2)
        three, src_three = _sign(signer, 3)

        async def accept(
            tenant: UUID, raw: bytes, source: dict[str, object],
        ):
            assert pool is not None
            return await accept_synthetic_signed_decision(
                pool, tenant_id=tenant, raw=raw, source=source,
                public_keys=keys, now_utc=NOW,
            )

        first = await accept(TENANT_A, one, src_one)
        assert first.result == "STORED"
        assert first.binding_id.version == 4
        assert first.execution_authorized is False
        assert (await accept(TENANT_A, one, src_one)).result == "IDEMPOTENT"
        other = await accept(TENANT_B, one, src_one)
        assert other.result == "STORED"
        assert other.binding_id != first.binding_id
        later = await accept(TENANT_A, two, src_two)
        assert later.binding_id == first.binding_id
        assert later.result == "STORED"

        with pytest.raises(NDSPContractRejected, match="NDSP_L2_STALE_VERSION"):
            await accept(TENANT_A, one, src_one)

        altered_raw, altered_src = _sign(
            signer, 2, published_at="2026-10-14T10:30:00Z",
        )
        with pytest.raises(NDSPContractRejected, match="NDSP_L2_VERSION_CONFLICT"):
            await accept(TENANT_A, altered_raw, altered_src)

        simultaneous = await asyncio.gather(*[
            accept(TENANT_A, three, src_three) for _ in range(6)
        ])
        assert sum(r.result == "STORED" for r in simultaneous) == 1
        assert sum(r.result == "IDEMPOTENT" for r in simultaneous) == 5
        assert {r.binding_id for r in simultaneous} == {first.binding_id}

        independent_raw, independent_src = _sign(
            signer, 1, source_id="CD-TEST-SECOND-20261014",
        )
        independent = await accept(TENANT_A, independent_raw, independent_src)
        assert independent.binding_id != first.binding_id

        bad_src = dict(src_one)
        bad_src["version"] = 7
        with pytest.raises(NDSPContractRejected, match="NDSP_SYNTHETIC_SOURCE_BINDING_MISMATCH"):
            await accept(TENANT_A, one, bad_src)
        with pytest.raises(NDSPContractRejected, match="NDSP_L2_TENANT_INVALID"):
            await accept(UUID(int=0), one, src_one)

        async with pool.acquire() as connection:
            assert await connection.fetchval(
                "SELECT COUNT(*) FROM m2b_l2_preview.decision_bindings",
            ) == 0
            assert await connection.fetchval(
                "SELECT COUNT(*) FROM m2b_l2_preview.decision_versions",
            ) == 0
            async with connection.transaction():
                await connection.execute(
                    "SELECT set_config('m2b_l2.tenant_id',$1,true)", str(TENANT_A),
                )
                original = await connection.fetchval(
                    "SELECT source_decision_id FROM m2b_l2_preview.decision_bindings "
                    "WHERE binding_id=$1", first.binding_id,
                )
                assert original == "CD-TEST-20261014"
                assert await connection.fetchval(
                    "SELECT COUNT(*) FROM m2b_l2_preview.decision_bindings "
                    "WHERE tenant_id=$1", TENANT_B,
                ) == 0
                versions = await connection.fetch(
                    "SELECT decision_version FROM m2b_l2_preview.decision_versions "
                    "WHERE binding_id=$1 ORDER BY decision_version",
                    first.binding_id,
                )
                assert [v["decision_version"] for v in versions] == [1, 2, 3]

            for relation in ("decision_bindings", "decision_versions"):
                # No UPDATE or DELETE privilege exists even with tenant context.
                for operation in ("UPDATE", "DELETE", "TRUNCATE"):
                    assert await connection.fetchval(
                        "SELECT has_table_privilege(current_user,$1,$2)",
                        "m2b_l2_preview." + relation, operation,
                    ) is False
            assert await connection.fetchval(
                "SELECT rolsuper OR rolbypassrls "
                "FROM pg_roles WHERE rolname=current_user",
            ) is False

            async with connection.transaction():
                await connection.execute(
                    "SELECT set_config('m2b_l2.tenant_id',$1,true)", str(TENANT_B),
                )
                assert await connection.fetchval(
                    "SELECT COUNT(*) FROM m2b_l2_preview.decision_versions",
                ) == 1
                # A forged tenant INSERT cannot bypass RLS.
                with pytest.raises(asyncpg.PostgresError):
                    await connection.execute(
                        "INSERT INTO m2b_l2_preview.decision_bindings "
                        "(binding_id,tenant_id,issuer_id,source_environment,"
                        "source_decision_id,signed_decision_id) "
                        "VALUES(gen_random_uuid(),$1,$2,'test',$3,$4)",
                        TENANT_A, "ndsp-source-slice-test", "CD-FORGED-99999",
                        UUID("dfffa7d3-b23b-4bd6-a632-f3ee154acada"),
                    )

        await pool.close()
        pool = await asyncpg.create_pool(
            dsn=APP_DSN, min_size=1, max_size=2, command_timeout=5, timeout=3,
        )
        assert (await accept(TENANT_A, three, src_three)).result == "IDEMPOTENT"
        assert (await accept(TENANT_B, one, src_one)).binding_id == other.binding_id
        print("M2B_L2_DISPOSABLE_LEDGER_TENANT_REPLAY_CONCURRENCY=PASS")
    finally:
        if pool is not None:
            await pool.close()
        if created_schema:
            await admin.execute("DROP SCHEMA m2b_l2_preview CASCADE")
        if created_role:
            await admin.execute("DROP ROLE m2b_l2_preview_app")
        await admin.close()


@pytest.mark.skipif(
    not ADMIN_DSN, reason="Needs clean localhost synthetic PostgreSQL test service",
)
def test_actual_disposable_postgresql_ledger() -> None:
    asyncio.run(_run_postgres_proof())
