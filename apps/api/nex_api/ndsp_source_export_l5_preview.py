"""M2-B L5: isolated SYNTHETIC CDS-source receipt and private-read proof.

Disposable PostgreSQL only. JWT signature is cryptographically checked against
a pinned, externally supplied TEST IdP public key. No real OIDC issuer or
production tenancy is trusted/connected. Do not register as an HTTP route.
The session GUC/RLS here is a test defense, NOT production tenant auth.
No orders, NDSP service/database access, runtime migrations or real keys.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Mapping
from uuid import UUID

import asyncpg  # type: ignore[import-untyped]
import jwt

from nex_api.ndsp_contract_preview import NDSPContractRejected
from nex_api.ndsp_source_binding_preview import verify_test_only_source_binding

ISSUER = "ndsp-l5-test-idp"
AUDIENCE = "nex-l5-private-export-test"
SOURCE_ISSUER = "ndsp-l5-synthetic-only"
_SOURCE_ID = re.compile(r"CD-[A-Z0-9-]{5,64}\Z", re.ASCII)
_MAX_TOKEN_BYTES = 8192
_STATUS = Literal["STORED", "IDEMPOTENT"]


@dataclass(frozen=True, slots=True)
class SourceReceipt:
    result: _STATUS
    source_decision_id: str
    decision_version: int
    execution_authorized: bool = False


@dataclass(frozen=True, slots=True)
class PublishedSyntheticEnvelope:
    document: bytes
    execution_authorized: bool = False


def _trusted_tenant(token: str, public_key_pem: bytes, scope: str) -> UUID:
    """Explicitly test-only signed-claim check: never use client tenant params."""
    if (not isinstance(token, str)
            or not 0 < len(token.encode("utf-8")) <= _MAX_TOKEN_BYTES
            or not isinstance(public_key_pem, bytes)
            or b"BEGIN PUBLIC KEY" not in public_key_pem):
        raise NDSPContractRejected("NDSP_L5_TRUST_CONTEXT_INVALID")
    try:
        claims = jwt.decode(
            token, public_key_pem,
            algorithms=["EdDSA"],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require": [
                "iss", "aud", "sub", "iat", "nbf", "exp",
                "tenant_id", "scope", "source_environment",
            ]},
            leeway=0,
        )
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise NDSPContractRejected("NDSP_L5_UNTRUSTED_IDENTITY") from exc
    if (not isinstance(claims, dict)
            or not isinstance(claims.get("sub"), str)
            or not claims["sub"].startswith("test-principal-")
            or claims.get("source_environment") != "test"
            or not isinstance(claims.get("scope"), str)
            or scope not in claims["scope"].split()):
        raise NDSPContractRejected("NDSP_L5_SCOPE_OR_ENVIRONMENT_DENIED")
    try:
        tenant = UUID(claims["tenant_id"])
    except (TypeError, ValueError, KeyError, AttributeError) as exc:
        raise NDSPContractRejected("NDSP_L5_TENANT_INVALID") from exc
    if tenant.int == 0 or str(tenant) != claims["tenant_id"]:
        raise NDSPContractRejected("NDSP_L5_TENANT_INVALID")
    return tenant


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _utc_clock(value: datetime) -> None:
    if (not isinstance(value, datetime) or value.tzinfo is None
            or value.utcoffset() != timezone.utc.utcoffset(value)):
        raise NDSPContractRejected("NDSP_L5_CLOCK_INVALID")


async def append_synthetic_source_event(
    pool: asyncpg.Pool, *, token: str, idp_public_key_pem: bytes,
    raw_signed: bytes, source: Mapping[str, object],
    source_public_keys: Mapping[str, bytes],
    trusted_source_owners: Mapping[str, UUID], now_utc: datetime,
) -> SourceReceipt:
    """Append issuer-signed version to isolated DB; DB enforces no gaps/rewrite.

    Signed synthetic fixture versions are pre-issued for cross-language proof.
    Production CDS must issue its own versions *transactionally* before signing.
    This test validates ordering; it does not establish that issuer authority.
    """
    _utc_clock(now_utc)
    tenant = _trusted_tenant(token, idp_public_key_pem, "ndsp.source.append")
    verified = verify_test_only_source_binding(
        raw_signed, source=source, public_keys=source_public_keys,
        now_utc=now_utc,
    )
    if verified.source_environment != "test" or verified.execution_authorized:
        raise NDSPContractRejected("NDSP_L5_REAL_SOURCE_DENIED")
    source_id = source["decision_id"]
    if not isinstance(source_id, str) or not _SOURCE_ID.fullmatch(source_id):
        raise NDSPContractRejected("NDSP_L5_SOURCE_ID_INVALID")
    # A valid caller identity is NOT evidence the caller owns this decision.
    # Trusted server-side CDS ownership is independently required. This map
    # is a synthetic authority fixture, never a client-provided request field.
    if (not isinstance(trusted_source_owners, Mapping)
            or trusted_source_owners.get(source_id) != tenant):
        raise NDSPContractRejected("NDSP_L5_SOURCE_OWNER_MISMATCH")
    if not isinstance(raw_signed, bytes) or not 100 <= len(raw_signed) <= 16384:
        raise NDSPContractRejected("NDSP_L5_SIGNED_BYTES_INVALID")
    envelope = json.loads(raw_signed)
    key_id = envelope["key_id"]
    evidence_hash = verified.evidence_hash
    digest = _sha(raw_signed)
    published_at = datetime.fromisoformat(str(source["published_at"]).replace("Z", "+00:00"))
    expires_at = verified.valid_until

    async with pool.acquire() as conn, conn.transaction():
        await conn.execute("SELECT set_config('m2b_l5.tenant_id',$1,true)", str(tenant))
        await conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended($1,0))",
            str(tenant) + ":" + SOURCE_ISSUER + ":" + source_id,
        )
        latest = await conn.fetchrow(
            "SELECT decision_version,signed_payload_hash,evidence_hash,key_id "
            "FROM m2b_l5_preview.source_issuance_events "
            "WHERE tenant_id=$1 AND source_decision_id=$2 "
            "ORDER BY decision_version DESC LIMIT 1",
            tenant, source_id,
        )
        if latest is None and verified.decision_version != 1:
            raise NDSPContractRejected("NDSP_L5_FIRST_VERSION_MUST_BE_ONE")
        if latest is not None:
            if verified.decision_version < latest["decision_version"]:
                raise NDSPContractRejected("NDSP_L5_STALE_VERSION")
            if verified.decision_version == latest["decision_version"]:
                if (digest != latest["signed_payload_hash"]
                        or evidence_hash != latest["evidence_hash"]
                        or key_id != latest["key_id"]):
                    raise NDSPContractRejected("NDSP_L5_CONFLICTING_VERSION")
                return SourceReceipt("IDEMPOTENT", source_id, verified.decision_version)
            if verified.decision_version != latest["decision_version"] + 1:
                raise NDSPContractRejected("NDSP_L5_VERSION_GAP")
        await conn.execute(
            "INSERT INTO m2b_l5_preview.source_issuance_events ("
            "tenant_id,source_decision_id,decision_version,issuer_id,"
            "source_environment,decision_state,visibility,published_at,"
            "expires_at,signed_bytes,evidence_hash,signed_payload_hash,key_id"
            ") VALUES ($1,$2,$3,$4,'test','Published','public',"
            "$5,$6,$7,$8,$9,$10)",
            tenant, source_id, verified.decision_version, SOURCE_ISSUER,
            published_at, expires_at, raw_signed, evidence_hash, digest, key_id,
        )
        return SourceReceipt("STORED", source_id, verified.decision_version)


async def private_read_synthetic_envelope(
    pool: asyncpg.Pool, *, token: str, idp_public_key_pem: bytes,
    source_decision_id: str, now_utc: datetime,
) -> PublishedSyntheticEnvelope:
    """Read latest tenant-authorized Published/public test envelope only.

    The contract is not an order instruction. No payload/PII/tenant is included.
    """
    _utc_clock(now_utc)
    tenant = _trusted_tenant(token, idp_public_key_pem, "ndsp.source.read")
    if not isinstance(source_decision_id, str) or not _SOURCE_ID.fullmatch(source_decision_id):
        raise NDSPContractRejected("NDSP_L5_SOURCE_ID_INVALID")
    async with pool.acquire() as conn, conn.transaction(readonly=True):
        await conn.execute("SELECT set_config('m2b_l5.tenant_id',$1,true)", str(tenant))
        row = await conn.fetchrow(
            "SELECT decision_version,signed_bytes,expires_at "
            "FROM m2b_l5_preview.source_issuance_events "
            "WHERE tenant_id=$1 AND source_decision_id=$2 "
            "AND issuer_id=$3 AND source_environment='test' "
            "AND decision_state='Published' AND visibility='public' "
            "ORDER BY decision_version DESC LIMIT 1",
            tenant, source_decision_id, SOURCE_ISSUER,
        )
        if row is None:
            raise NDSPContractRejected("NDSP_L5_NOT_FOUND_OR_UNAUTHORIZED")
        if row["expires_at"] <= now_utc:
            raise NDSPContractRejected("NDSP_L5_SOURCE_EXPIRED")
        return PublishedSyntheticEnvelope(document=bytes(row["signed_bytes"]))
