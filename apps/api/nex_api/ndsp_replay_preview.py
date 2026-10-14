"""M2-B disposable PostgreSQL replay proof for synthetic verified decisions.

Not connected to FastAPI, NDSP, or trading. Tenant_id must come from a trusted
server-side identity; this preview deliberately supplies no identity adapter.
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

import asyncpg  # type: ignore[import-untyped]

from nex_api.ndsp_contract_preview import (
    NDSPContractRejected,
    VerifiedSyntheticDecision,
)

ReceiptState = Literal["STORED", "IDEMPOTENT"]


async def record_synthetic_receipt(
    pool: asyncpg.Pool,
    *,
    tenant_id: UUID,
    verified: VerifiedSyntheticDecision,
) -> ReceiptState:
    """Append-only tenant receipt; serialize concurrent versions per decision.

    The caller is solely an isolated fixture with test signatures. Database
    constraint/RLS are the authority for tenant isolation. A replay of the
    latest identical receipt is safe; stale or conflicting versions fail.
    """
    if (not isinstance(tenant_id, UUID) or tenant_id.int == 0
            or not isinstance(verified, VerifiedSyntheticDecision)
            or verified.source_environment != "test"
            or verified.execution_authorized
            or verified.decision_version < 1):
        raise NDSPContractRejected("NDSP_REPLAY_CONTEXT_INVALID")

    async with pool.acquire() as connection, connection.transaction():
        await connection.execute(
            "SELECT set_config('m2b.tenant_id',$1,true)", str(tenant_id),
        )
        # Scope lock by tenant+decision. Collisions serialize unrelated
        # requests but cannot permit a missing uniqueness/version check.
        await connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
            str(tenant_id) + ":" + str(verified.decision_id),
        )
        row = await connection.fetchrow(
            "SELECT decision_version,evidence_hash "
            "FROM m2b_preview.decision_receipts "
            "WHERE tenant_id=$1 AND decision_id=$2 "
            "ORDER BY decision_version DESC LIMIT 1",
            tenant_id, verified.decision_id,
        )
        if row is not None:
            if verified.decision_version < row["decision_version"]:
                raise NDSPContractRejected("NDSP_REPLAY_STALE_VERSION")
            if verified.decision_version == row["decision_version"]:
                if verified.evidence_hash != row["evidence_hash"]:
                    raise NDSPContractRejected("NDSP_REPLAY_VERSION_CONFLICT")
                return "IDEMPOTENT"
        await connection.execute(
            "INSERT INTO m2b_preview.decision_receipts("
            "tenant_id,decision_id,decision_version,evidence_hash) "
            "VALUES ($1,$2,$3,$4)",
            tenant_id, verified.decision_id, verified.decision_version,
            verified.evidence_hash,
        )
        return "STORED"
