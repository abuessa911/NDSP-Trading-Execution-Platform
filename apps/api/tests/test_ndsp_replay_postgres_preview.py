"""Actual disposable PostgreSQL RLS/idempotency test for synthetic NDSP only.

Always skipped unless explicitly opted in to a fresh localhost CI database.
No NEX/NDSP migrations or production database are ever touched.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

import asyncpg
import pytest

from nex_api.ndsp_contract_preview import (
    NDSPContractRejected,
    VerifiedSyntheticDecision,
)
from nex_api.ndsp_replay_preview import record_synthetic_receipt

ADMIN_DSN = os.environ.get("M2B_PREVIEW_ADMIN_DSN", "")


def _safe_admin_dsn() -> str:
    uri = urlsplit(ADMIN_DSN)
    if (uri.scheme != "postgresql" or uri.hostname not in {"localhost", "127.0.0.1"}
            or uri.port != 5432 or uri.path != "/nex_m2b_preview"
            or uri.username != "m2b_fixture"
            or uri.password != "synthetic-m2b-admin-only"
            or uri.query or uri.fragment):
        raise RuntimeError("REFUSE_UNSAFE_M2B_PREVIEW_DATABASE")
    return ADMIN_DSN


def _synthetic(version: int = 1, digest: str | None = None) -> VerifiedSyntheticDecision:
    return VerifiedSyntheticDecision(
        decision_id=UUID("c0047cb0-6675-44aa-912b-998672a83d81"),
        decision_version=version,
        asset="BTCUSDT", timeframe="4H", direction="FLAT",
        decision_state="BLOCKED", scenario_state="UNDER_MONITORING",
        risk_class="BLOCKED",
        valid_until=datetime(2026, 10, 15, tzinfo=timezone.utc),
        evidence_hash=digest or "sha256:" + "b" * 64,
    )


async def _check_replay_database() -> None:
    # Guard is enforced BEFORE opening ANY database connection.
    dsn = _safe_admin_dsn()
    admin = await asyncpg.connect(dsn=dsn, timeout=3)
    app_pool = None
    owned_role = False
    owned_schema = False
    try:
        assert await admin.fetchval("SELECT current_database()") == "nex_m2b_preview"
        assert await admin.fetchval(
            "SELECT rolsuper FROM pg_roles WHERE rolname=current_user",
        ) is True
        if (await admin.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname='nex_m2b_preview_app'",
        ) or await admin.fetchval(
            "SELECT 1 FROM pg_namespace WHERE nspname='m2b_preview'",
        )):
            raise RuntimeError("REFUSE_REUSE_OF_M2B_PREVIEW_RESOURCES")
        await admin.execute(
            "CREATE ROLE nex_m2b_preview_app LOGIN PASSWORD "
            "'synthetic-m2b-app-only' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE",
        )
        owned_role = True
        ddl = (Path(__file__).resolve().parents[3]
               / "infra/testing/m2b_receipt_preview.sql").read_text()
        await admin.execute(ddl)
        owned_schema = True

        app_pool = await asyncpg.create_pool(
            dsn="postgresql://nex_m2b_preview_app:synthetic-m2b-app-only"
                "@127.0.0.1:5432/nex_m2b_preview",
            min_size=1, max_size=4, command_timeout=3, timeout=3,
        )
        tenant_a = UUID("6d4ef9b2-a953-4995-8cac-b00b06c11223")
        tenant_b = UUID("24c6c487-5420-4a91-a00d-c34c7ec50c6f")
        one = _synthetic()
        two = _synthetic(2)
        assert await record_synthetic_receipt(
            app_pool, tenant_id=tenant_a, verified=one,
        ) == "STORED"
        assert await record_synthetic_receipt(
            app_pool, tenant_id=tenant_a, verified=one,
        ) == "IDEMPOTENT"
        assert await record_synthetic_receipt(
            app_pool, tenant_id=tenant_b, verified=one,
        ) == "STORED"
        assert await record_synthetic_receipt(
            app_pool, tenant_id=tenant_a, verified=two,
        ) == "STORED"
        with pytest.raises(NDSPContractRejected, match="NDSP_REPLAY_STALE_VERSION"):
            await record_synthetic_receipt(
                app_pool, tenant_id=tenant_a, verified=one,
            )
        with pytest.raises(NDSPContractRejected, match="NDSP_REPLAY_VERSION_CONFLICT"):
            await record_synthetic_receipt(
                app_pool, tenant_id=tenant_a,
                verified=replace(two, evidence_hash="sha256:" + "c" * 64),
            )
        with pytest.raises(NDSPContractRejected, match="NDSP_REPLAY_CONTEXT_INVALID"):
            await record_synthetic_receipt(
                app_pool, tenant_id=UUID(int=0), verified=two,
            )

        concurrent = await asyncio.gather(*[
            record_synthetic_receipt(
                app_pool, tenant_id=tenant_a, verified=_synthetic(3),
            )
            for _ in range(5)
        ])
        assert concurrent.count("STORED") == 1
        assert concurrent.count("IDEMPOTENT") == 4

        async with app_pool.acquire() as conn:
            # No tenant context = no data; RLS must hold even for SELECT.
            assert await conn.fetchval(
                "SELECT count(*) FROM m2b_preview.decision_receipts",
            ) == 0
            async with conn.transaction():
                await conn.execute(
                    "SELECT set_config('m2b.tenant_id',$1,true)", str(tenant_a),
                )
                versions = await conn.fetch(
                    "SELECT decision_version FROM m2b_preview.decision_receipts "
                    "ORDER BY decision_version",
                )
                assert [r["decision_version"] for r in versions] == [1, 2, 3]
                # Tenant A cannot see B's record.
                assert await conn.fetchval(
                    "SELECT count(*) FROM m2b_preview.decision_receipts "
                    "WHERE tenant_id=$1", tenant_b,
                ) == 0
                with pytest.raises(asyncpg.InsufficientPrivilegeError):
                    await conn.execute(
                        "UPDATE m2b_preview.decision_receipts SET decision_version=99",
                    )
            async with conn.transaction():
                await conn.execute(
                    "SELECT set_config('m2b.tenant_id',$1,true)", str(tenant_b),
                )
                assert await conn.fetchval(
                    "SELECT count(*) FROM m2b_preview.decision_receipts",
                ) == 1
                with pytest.raises(asyncpg.InsufficientPrivilegeError):
                    await conn.execute(
                        "DELETE FROM m2b_preview.decision_receipts",
                    )

        # Pool restart is meaningful evidence of durable database receipts.
        await app_pool.close()
        app_pool = await asyncpg.create_pool(
            dsn="postgresql://nex_m2b_preview_app:synthetic-m2b-app-only"
                "@127.0.0.1:5432/nex_m2b_preview",
            min_size=1, max_size=3, command_timeout=3, timeout=3,
        )
        assert await record_synthetic_receipt(
            app_pool, tenant_id=tenant_a, verified=_synthetic(3),
        ) == "IDEMPOTENT"

        # Also verify the role has no dangerous grants.
        async with app_pool.acquire() as conn:
            denied = await conn.fetchval(
                "SELECT has_table_privilege(current_user,"
                "'m2b_preview.decision_receipts','UPDATE') OR "
                "has_table_privilege(current_user,"
                "'m2b_preview.decision_receipts','DELETE') OR "
                "has_table_privilege(current_user,"
                "'m2b_preview.decision_receipts','TRUNCATE')",
            )
            assert denied is False
            assert await conn.fetchval(
                "SELECT rolsuper OR rolbypassrls FROM pg_roles "
                "WHERE rolname=current_user",
            ) is False
        print("M2B_DISPOSABLE_POSTGRES_RECEIPTS_AND_RLS=PASS")
    finally:
        if app_pool is not None:
            await app_pool.close()
        if owned_schema:
            await admin.execute("DROP SCHEMA m2b_preview CASCADE")
        if owned_role:
            await admin.execute("DROP ROLE nex_m2b_preview_app")
        await admin.close()


@pytest.mark.skipif(
    not ADMIN_DSN, reason="Requires fresh synthetic PostgreSQL CI service",
)
def test_real_postgres_tenant_isolation_and_atomic_versions() -> None:
    asyncio.run(_check_replay_database())


def test_preview_replay_has_no_ndsp_or_exchange_client() -> None:
    from nex_api import ndsp_replay_preview as code

    assert not hasattr(code, "submit_order")
    assert not hasattr(code, "publish_to_ndsp")
    assert not hasattr(code, "get_ndsp_decisions")
    assert code.ReceiptState is not None
