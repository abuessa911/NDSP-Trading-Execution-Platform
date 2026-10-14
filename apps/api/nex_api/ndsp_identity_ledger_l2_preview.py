"""Disposable M2-B L2 identity/version ledger; SYNTHETIC TEST DATA ONLY.

No production NDSP connector, FastAPI route, exchange client, real KMS, or
trading capability. The tenant is injected by a trusted CI fixture ONLY.
RLS with a settable GUC is NOT approved production tenant authentication.
"""
from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Mapping
from uuid import UUID, uuid4

import asyncpg  # type: ignore[import-untyped]

from nex_api.ndsp_contract_preview import NDSPContractRejected
from nex_api.ndsp_source_binding_preview import verify_test_only_source_binding

SOURCE_ISSUER = "ndsp-source-slice-test"
ReceiptState = Literal["STORED", "IDEMPOTENT"]


@dataclass(frozen=True, slots=True)
class LedgerReceipt:
    binding_id: UUID
    result: ReceiptState
    execution_authorized: bool = False


def _fingerprints(raw: bytes) -> tuple[str, str, str]:
    # Call ONLY after the independent verifier checks duplicate keys,
    # exact field set, source, canonical bytes, signature and expiry.
    doc = json.loads(raw)
    if not isinstance(doc, dict):
        raise NDSPContractRejected("NDSP_L2_INVALID_DOCUMENT")
    canonical = json.dumps(
        {key: value for key, value in doc.items() if key != "signature"},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    signature = base64.b64decode(doc["signature"], validate=True)
    return (
        "sha256:" + hashlib.sha256(canonical).hexdigest(),
        "sha256:" + hashlib.sha256(signature).hexdigest(),
        str(doc["key_id"]),
    )


async def accept_synthetic_signed_decision(
    pool: asyncpg.Pool,
    *,
    tenant_id: UUID,
    raw: bytes,
    source: Mapping[str, object],
    public_keys: Mapping[str, bytes],
    now_utc: datetime,
) -> LedgerReceipt:
    """Append immutable source-to-NEX UUID and signed version in a transaction.

    Production integration is BLOCKED. The source-derived signed decision ID
    remains unchanged; the new NEX binding UUID is never fed to the issuer.
    """
    if not isinstance(tenant_id, UUID) or tenant_id.int == 0:
        raise NDSPContractRejected("NDSP_L2_TENANT_INVALID")

    verified = verify_test_only_source_binding(
        raw, source=source, public_keys=public_keys, now_utc=now_utc,
    )
    if verified.source_environment != "test" or verified.execution_authorized:
        raise NDSPContractRejected("NDSP_L2_SOURCE_NOT_APPROVED")
    source_id = source["decision_id"]
    if not isinstance(source_id, str):
        raise NDSPContractRejected("NDSP_L2_SOURCE_ID_INVALID")
    canonical_hash, signature_hash, key_id = _fingerprints(raw)

    async with pool.acquire() as connection, connection.transaction():
        await connection.execute(
            "SELECT set_config('m2b_l2.tenant_id',$1,true)", str(tenant_id),
        )
        # Lock source identity (not a caller-selected UUID). PostgreSQL unique
        # constraints remain authoritative, even in a lock-hash collision.
        await connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
            str(tenant_id) + ":" + SOURCE_ISSUER + ":test:" + source_id,
        )
        binding = await connection.fetchrow(
            "SELECT binding_id,signed_decision_id "
            "FROM m2b_l2_preview.decision_bindings "
            "WHERE tenant_id=$1 AND issuer_id=$2 AND source_environment='test' "
            "AND source_decision_id=$3",
            tenant_id, SOURCE_ISSUER, source_id,
        )
        if binding is None:
            binding_id = uuid4()
            await connection.execute(
                "INSERT INTO m2b_l2_preview.decision_bindings ("
                "binding_id,tenant_id,issuer_id,source_environment,"
                "source_decision_id,signed_decision_id) "
                "VALUES ($1,$2,$3,'test',$4,$5)",
                binding_id, tenant_id, SOURCE_ISSUER, source_id,
                verified.decision_id,
            )
        else:
            binding_id = binding["binding_id"]
            if binding["signed_decision_id"] != verified.decision_id:
                raise NDSPContractRejected("NDSP_L2_IDENTITY_CONFLICT")

        latest = await connection.fetchrow(
            "SELECT decision_version,evidence_hash,canonical_payload_hash,"
            "signature_hash,key_id FROM m2b_l2_preview.decision_versions "
            "WHERE tenant_id=$1 AND binding_id=$2 "
            "ORDER BY decision_version DESC LIMIT 1",
            tenant_id, binding_id,
        )
        if latest is not None:
            if verified.decision_version < latest["decision_version"]:
                raise NDSPContractRejected("NDSP_L2_STALE_VERSION")
            if verified.decision_version == latest["decision_version"]:
                if (latest["evidence_hash"] != verified.evidence_hash
                        or latest["canonical_payload_hash"] != canonical_hash
                        or latest["signature_hash"] != signature_hash
                        or latest["key_id"] != key_id):
                    raise NDSPContractRejected("NDSP_L2_VERSION_CONFLICT")
                return LedgerReceipt(binding_id, "IDEMPOTENT")

        await connection.execute(
            "INSERT INTO m2b_l2_preview.decision_versions ("
            "binding_id,tenant_id,decision_version,evidence_hash,"
            "canonical_payload_hash,signature_hash,key_id) "
            "VALUES ($1,$2,$3,$4,$5,$6,$7)",
            binding_id, tenant_id, verified.decision_version,
            verified.evidence_hash, canonical_hash, signature_hash, key_id,
        )
        return LedgerReceipt(binding_id, "STORED")
