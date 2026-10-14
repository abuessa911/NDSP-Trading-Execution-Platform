"""M2-B L6: disposable source-owned *simulation* of durable version issuance.

Two-phase append-only reservation -> Ed25519 source signature seal -> read.
Never imported by a production entrypoint. No real NDSP database, gateway,
identity provider, customer decisions, signing private keys or orders.
The real issuer must control the same transaction boundary as CDS; this
synthetic prototype is NOT an approved authoritative production issuer.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping
from uuid import UUID

import asyncpg  # type: ignore[import-untyped]

from nex_api.ndsp_contract_preview import NDSPContractRejected
from nex_api.ndsp_source_binding_preview import (
    SOURCE_ID_PATTERN,
    SOURCE_KEYS,
    SYMBOL_PATTERN,
    _time,
    verify_test_only_source_binding,
)
from nex_api.ndsp_source_export_l5_preview import _trusted_tenant

_ALLOWED = SOURCE_KEYS - frozenset({"version"})
_MAX_VERSION = 2**53 - 1  # test interop with Node.js fixture contract


@dataclass(frozen=True, slots=True)
class Reservation:
    status: str
    source_decision_id: str
    version: int
    execution_authorized: bool = False


@dataclass(frozen=True, slots=True)
class Sealed:
    status: str
    version: int
    execution_authorized: bool = False


@dataclass(frozen=True, slots=True)
class ReadOnlyEnvelope:
    signed_bytes: bytes
    version: int
    execution_authorized: bool = False


def _fail(code: str) -> None:
    raise NDSPContractRejected(code)


def _identity(
    token: str, public_key_pem: bytes, scope: str,
    source_id: str, trusted_source_owners: Mapping[str, UUID],
) -> UUID:
    tenant = _trusted_tenant(token, public_key_pem, scope)
    if not isinstance(source_id, str) or SOURCE_ID_PATTERN.fullmatch(source_id) is None:
        _fail("NDSP_L6_BAD_SOURCE_ID")
    # CRITICAL: JWT tenant claim alone never grants ownership of a CDS decision.
    if (not isinstance(trusted_source_owners, Mapping)
            or trusted_source_owners.get(source_id) != tenant):
        _fail("NDSP_L6_SOURCE_OWNER_DENIED")
    return tenant


def _snapshot(source: Mapping[str, object], now_utc: datetime) -> dict[str, str]:
    if not isinstance(source, Mapping) or set(source) != _ALLOWED:
        _fail("NDSP_L6_SOURCE_FIELDS_DENIED")
    if (not isinstance(now_utc, datetime) or now_utc.tzinfo is None
            or now_utc.utcoffset() != timezone.utc.utcoffset(now_utc)):
        _fail("NDSP_L6_CLOCK_INVALID")
    if any(not isinstance(v, str) for v in source.values()):
        _fail("NDSP_L6_SOURCE_TYPES_DENIED")
    data = {k: str(source[k]) for k in _ALLOWED}
    if (SOURCE_ID_PATTERN.fullmatch(data["decision_id"]) is None
            or SYMBOL_PATTERN.fullmatch(data["symbol"]) is None
            or data["market"] != "CRYPTO"
            or data["timeframe"] not in {"5m", "15m", "4H"}
            or data["decision_state"] != "Published"
            or data["visibility"] != "public"):
        _fail("NDSP_L6_SOURCE_NOT_ELIGIBLE")
    completed, published, expires = (
        _time(data["completed_at"]), _time(data["published_at"]),
        _time(data["expires_at"]),
    )
    if not completed <= published <= now_utc < expires:
        _fail("NDSP_L6_SOURCE_EXPIRED_OR_FUTURE")
    return data


def _hash(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _fingerprint(source: Mapping[str, str]) -> str:
    return _hash(json.dumps(
        dict(source), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8"))


async def reserve_synthetic_revision(
    pool: asyncpg.Pool, *,
    token: str, idp_public_key_pem: bytes,
    trusted_source_owners: Mapping[str, UUID], operation_id: UUID,
    source: Mapping[str, object], now_utc: datetime,
) -> Reservation:
    """Allocate next version IN POSTGRES after trusted fixture auth.

    Exact operation_id retry is idempotent. A pending predecessor blocks any
    newer revision until its signed artifact is durably sealed.
    """
    prepared = _snapshot(source, now_utc)
    source_id = prepared["decision_id"]
    tenant = _identity(
        token, idp_public_key_pem, "ndsp.source.reserve",
        source_id, trusted_source_owners,
    )
    if not isinstance(operation_id, UUID) or operation_id.version != 4:
        _fail("NDSP_L6_OPERATION_ID_INVALID")
    fingerprint = _fingerprint(prepared)
    async with pool.acquire() as conn, conn.transaction():
        await conn.execute("SELECT set_config('m2b_l6.tenant_id',$1,true)", str(tenant))
        await conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
            str(tenant) + ":" + source_id,
        )
        repeated = await conn.fetchrow(
            "SELECT source_decision_id,decision_version,source_fingerprint "
            "FROM m2b_l6_preview.source_revisions "
            "WHERE tenant_id=$1 AND operation_id=$2",
            tenant, operation_id,
        )
        if repeated is not None:
            if (repeated["source_decision_id"] != source_id
                    or repeated["source_fingerprint"] != fingerprint):
                _fail("NDSP_L6_OPERATION_REUSED_WITH_OTHER_SOURCE")
            return Reservation("IDEMPOTENT", source_id, repeated["decision_version"])
        last = await conn.fetchrow(
            "SELECT r.decision_version,s.decision_version AS sealed_version "
            "FROM m2b_l6_preview.source_revisions r "
            "LEFT JOIN m2b_l6_preview.sealed_artifacts s "
            "ON s.tenant_id=r.tenant_id AND s.source_decision_id=r.source_decision_id "
            "AND s.decision_version=r.decision_version "
            "WHERE r.tenant_id=$1 AND r.source_decision_id=$2 "
            "ORDER BY r.decision_version DESC LIMIT 1",
            tenant, source_id,
        )
        if last is not None and last["sealed_version"] is None:
            _fail("NDSP_L6_PREDECESSOR_UNSIGNED")
        version = 1 if last is None else last["decision_version"] + 1
        if version > _MAX_VERSION:
            _fail("NDSP_L6_VERSION_OVERFLOW")
        await conn.execute(
            "INSERT INTO m2b_l6_preview.source_revisions("
            "tenant_id,source_decision_id,decision_version,operation_id,"
            "source_snapshot,source_fingerprint) "
            "VALUES ($1,$2,$3,$4,$5::jsonb,$6)",
            tenant, source_id, version, operation_id,
            json.dumps(prepared, sort_keys=True, separators=(",", ":")), fingerprint,
        )
        return Reservation("RESERVED", source_id, version)


async def seal_synthetic_revision(
    pool: asyncpg.Pool, *,
    token: str, idp_public_key_pem: bytes,
    trusted_source_owners: Mapping[str, UUID], source_decision_id: str,
    version: int, signed_bytes: bytes, trusted_signer_public_keys: Mapping[str, bytes],
    now_utc: datetime,
) -> Sealed:
    """Verify source-signed fixture against immutable reservation BEFORE sealing.

    Cannot append a raw unsigned envelope, change source revision contents,
    overwrite a signed artifact, or attach the wrong signature/version.
    """
    tenant = _identity(
        token, idp_public_key_pem, "ndsp.source.seal",
        source_decision_id, trusted_source_owners,
    )
    if type(version) is not int or not 1 <= version <= _MAX_VERSION:
        _fail("NDSP_L6_VERSION_INVALID")
    if not isinstance(signed_bytes, bytes) or not 100 <= len(signed_bytes) <= 16384:
        _fail("NDSP_L6_SIGNED_BYTES_INVALID")
    async with pool.acquire() as conn, conn.transaction():
        await conn.execute("SELECT set_config('m2b_l6.tenant_id',$1,true)", str(tenant))
        await conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
            str(tenant) + ":" + source_decision_id,
        )
        row = await conn.fetchrow(
            "SELECT source_snapshot,source_fingerprint "
            "FROM m2b_l6_preview.source_revisions "
            "WHERE tenant_id=$1 AND source_decision_id=$2 AND decision_version=$3",
            tenant, source_decision_id, version,
        )
        if row is None:
            _fail("NDSP_L6_REVISION_NOT_RESERVED")
        raw_snapshot = row["source_snapshot"]
        snapshot = json.loads(raw_snapshot) if isinstance(raw_snapshot, str) else raw_snapshot
        if not isinstance(snapshot, dict) or _fingerprint(snapshot) != row["source_fingerprint"]:
            _fail("NDSP_L6_SNAPSHOT_INTEGRITY_FAILURE")
        reconstructed = dict(snapshot)
        reconstructed["version"] = version
        verified = verify_test_only_source_binding(
            signed_bytes, source=reconstructed,
            public_keys=trusted_signer_public_keys, now_utc=now_utc,
        )
        if verified.execution_authorized or verified.source_environment != "test":
            _fail("NDSP_L6_PRODUCTION_OR_EXECUTION_DENIED")
        doc = json.loads(signed_bytes)
        digest = _hash(signed_bytes)
        old = await conn.fetchrow(
            "SELECT signed_hash,signed_bytes FROM m2b_l6_preview.sealed_artifacts "
            "WHERE tenant_id=$1 AND source_decision_id=$2 AND decision_version=$3",
            tenant, source_decision_id, version,
        )
        if old is not None:
            if old["signed_hash"] != digest or bytes(old["signed_bytes"]) != signed_bytes:
                _fail("NDSP_L6_SEAL_CONFLICT")
            return Sealed("IDEMPOTENT", version)
        await conn.execute(
            "INSERT INTO m2b_l6_preview.sealed_artifacts("
            "tenant_id,source_decision_id,decision_version,signed_bytes,"
            "signed_hash,key_id,expires_at) VALUES($1,$2,$3,$4,$5,$6,$7)",
            tenant, source_decision_id, version, signed_bytes, digest,
            doc["key_id"], verified.valid_until,
        )
        return Sealed("SEALED", version)


async def read_latest_synthetic_signed(
    pool: asyncpg.Pool, *,
    token: str, idp_public_key_pem: bytes,
    trusted_source_owners: Mapping[str, UUID],
    source_decision_id: str, now_utc: datetime,
) -> ReadOnlyEnvelope:
    """Read nothing until newest reserved version has a verified signed seal."""
    tenant = _identity(
        token, idp_public_key_pem, "ndsp.source.read",
        source_decision_id, trusted_source_owners,
    )
    if now_utc.tzinfo is None or now_utc.utcoffset() != timezone.utc.utcoffset(now_utc):
        _fail("NDSP_L6_CLOCK_INVALID")
    async with pool.acquire() as conn, conn.transaction(readonly=True):
        await conn.execute("SELECT set_config('m2b_l6.tenant_id',$1,true)", str(tenant))
        row = await conn.fetchrow(
            "SELECT r.decision_version,s.signed_bytes,s.expires_at "
            "FROM m2b_l6_preview.source_revisions r "
            "LEFT JOIN m2b_l6_preview.sealed_artifacts s "
            "ON s.tenant_id=r.tenant_id AND s.source_decision_id=r.source_decision_id "
            "AND s.decision_version=r.decision_version "
            "WHERE r.tenant_id=$1 AND r.source_decision_id=$2 "
            "ORDER BY r.decision_version DESC LIMIT 1",
            tenant, source_decision_id,
        )
        if row is None:
            _fail("NDSP_L6_NOT_FOUND_OR_UNAUTHORIZED")
        if row["signed_bytes"] is None:
            _fail("NDSP_L6_SOURCE_PENDING_SIGNATURE")
        if row["expires_at"] <= now_utc:
            _fail("NDSP_L6_SOURCE_EXPIRED")
        return ReadOnlyEnvelope(bytes(row["signed_bytes"]), row["decision_version"])
