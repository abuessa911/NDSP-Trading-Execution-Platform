"""M2-B L7: offline, dependency-injected NDSP canonical identity/owner read gate.

PROTOTYPE ONLY. Does NOT connect to real 9020/9001/9091, CDS, or an IdP;
does not register any API route. Accepts exclusively ephemeral synthetic
signature fixtures, and always returns execution_authorized=False.

Source fact: real 9091 entitlement authority checks 9020 session UUID itself
but its outbound JSON does not include a proof of bound subject. Thus this
prototype must NOT be interpreted as production identity certification.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable, Mapping, NoReturn
from uuid import UUID

from nex_api.ndsp_contract_preview import (
    NDSPContractRejected,
    VerifiedSyntheticDecision,
    verify_synthetic_ndsp_contract,
)

_SOURCE_ID = re.compile(r"CD-[A-Z0-9-]{5,64}\Z", re.ASCII)
_ENTITLEMENT_AUTHORITY = "NDSP_CANONICAL_ENTITLEMENT_9091_V1"


class CanonicalGateDenied(Exception):
    """Stable, non-sensitive gate errors, without leaking protected records."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class TestCanonicalAuthorities:
    # Each function is a sandbox-only, trust-domain boundary simulation.
    session: Callable[[str], Awaitable[Mapping[str, object]]]
    entitlement: Callable[[str], Awaitable[Mapping[str, object]]]
    ownership: Callable[[str], Awaitable[Mapping[str, object]]]
    sealed_reader: Callable[[UUID, str], Awaitable[bytes]]
    source_test_public_keys: Mapping[str, bytes]
    synthetic_only: bool = True


@dataclass(frozen=True, slots=True)
class ReadOnlySourceDecision:
    document: bytes
    source_decision_id: str
    tenant_id: UUID
    decision_version: int
    execution_authorized: bool = False


def _deny(code: str) -> NoReturn:
    raise CanonicalGateDenied(code)


def _canonical_uuid(value: object, code: str) -> UUID:
    if not isinstance(value, str) or len(value) != 36:
        _deny(code)
    try:
        candidate = UUID(value)
    except ValueError as exc:
        raise CanonicalGateDenied(code) from exc
    if candidate.int == 0 or str(candidate) != value:
        _deny(code)
    return candidate


def _verified_subject(session: Mapping[str, object]) -> UUID:
    if session.get("ok") is not True:
        _deny("L7_AUTH_REQUIRED")
    user = session.get("user")
    if not isinstance(user, dict):
        _deny("L7_AUTH_SUBJECT_UNVERIFIED")
    return _canonical_uuid(user.get("id"), "L7_AUTH_SUBJECT_UNVERIFIED")


def _verified_entitlement(authority: Mapping[str, object]) -> Mapping[str, object]:
    if (authority.get("ok") is not True
            or authority.get("authority") != _ENTITLEMENT_AUTHORITY):
        _deny("L7_ENTITLEMENT_AUTHORITY_UNVERIFIED")
    e = authority.get("entitlement")
    if not isinstance(e, dict) or e.get("allowed") is not True:
        _deny("L7_ENTITLEMENT_NOT_ALLOWED")
    return e


def _owner_record(
    source_id: str, subject: UUID, record: Mapping[str, object],
) -> tuple[UUID, str, str]:
    # Exact, server-owned metadata only. A CD-* is not a tenant or user ID.
    expected = frozenset({
        "source_decision_id", "owner_user_id", "tenant_id",
        "decision_state", "visibility", "symbol", "timeframe",
        "source_environment",
    })
    if set(record) != expected:
        _deny("L7_OWNER_PROVENANCE_UNAVAILABLE")
    if (record.get("source_decision_id") != source_id
            or record.get("decision_state") != "Published"
            or record.get("visibility") != "public"
            or record.get("source_environment") != "test"):
        _deny("L7_SOURCE_NOT_PUBLIC_OR_UNTRUSTED")
    owner = _canonical_uuid(record.get("owner_user_id"), "L7_OWNER_UNVERIFIED")
    if owner != subject:
        _deny("L7_SOURCE_OWNER_MISMATCH")
    tenant = _canonical_uuid(record.get("tenant_id"), "L7_TENANT_UNVERIFIED")
    symbol, timeframe = record.get("symbol"), record.get("timeframe")
    if (not isinstance(symbol, str) or not re.fullmatch(r"[A-Z0-9]{5,20}", symbol)
            or not isinstance(timeframe, str)
            or timeframe not in {"5m", "15m", "4H"}):
        _deny("L7_SOURCE_CONTEXT_UNVERIFIED")
    return tenant, symbol, timeframe


def _plan_allows(
    entitlement: Mapping[str, object], symbol: str, timeframe: str,
) -> None:
    timeframes = entitlement.get("timeframes")
    if (not isinstance(timeframes, list)
            or timeframe.lower() not in {
                value.lower() for value in timeframes if isinstance(value, str)
            }):
        _deny("L7_TIMEFRAME_NOT_ENTITLED")
    mode = entitlement.get("asset_mode")
    slots = entitlement.get("asset_slots")
    if mode == "all_supported":
        if (entitlement.get("fixed_asset")
                or (isinstance(slots, int) and not isinstance(slots, bool)
                    and slots > 0)):
            _deny("L7_ENTITLEMENT_POLICY_CONFLICT")
        return
    fixed = entitlement.get("fixed_asset")
    if isinstance(fixed, str) and fixed.strip():
        if symbol not in {fixed.upper(), fixed.upper() + "USDT", fixed.upper() + "USD"}:
            _deny("L7_ASSET_NOT_ENTITLED")
        return
    # Selected slots MUST use independently verified assignment authority.
    # No assignment authority in L7, so fail closed.
    _deny("L7_ASSET_ASSIGNMENT_AUTHORITY_MISSING")


async def read_only_test_decision(
    *, credentials: str, source_decision_id: str,
    authorities: TestCanonicalAuthorities, now_utc: datetime,
) -> ReadOnlySourceDecision:
    """Simulate auth/session 9020 -> entitlement 9091 -> owner -> signed read.

    Session/entitlement are fed the *same* opaque transport credentials.
    The binding of 9091 authority to real subject depends on production
    deployment and remains an unverified, separately gated precondition.
    """
    if (not authorities.synthetic_only
            or not isinstance(credentials, str)
            or not 0 < len(credentials) <= 4096
            or not isinstance(source_decision_id, str)
            or _SOURCE_ID.fullmatch(source_decision_id) is None):
        _deny("L7_TEST_CONTEXT_REQUIRED")
    if (not isinstance(now_utc, datetime) or now_utc.tzinfo is None
            or now_utc.utcoffset() != timezone.utc.utcoffset(now_utc)):
        _deny("L7_CLOCK_INVALID")

    try:
        session = await authorities.session(credentials)
    except Exception as exc:
        raise CanonicalGateDenied("L7_SESSION_AUTHORITY_UNAVAILABLE") from exc
    if not isinstance(session, dict):
        _deny("L7_AUTH_REQUIRED")
    subject = _verified_subject(session)

    try:
        ent = await authorities.entitlement(credentials)
    except Exception as exc:
        raise CanonicalGateDenied("L7_ENTITLEMENT_AUTHORITY_UNAVAILABLE") from exc
    if not isinstance(ent, dict):
        _deny("L7_ENTITLEMENT_AUTHORITY_UNVERIFIED")
    granted = _verified_entitlement(ent)

    try:
        owned = await authorities.ownership(source_decision_id)
    except Exception as exc:
        raise CanonicalGateDenied("L7_OWNER_AUTHORITY_UNAVAILABLE") from exc
    if not isinstance(owned, dict):
        _deny("L7_OWNER_PROVENANCE_UNAVAILABLE")
    tenant, symbol, timeframe = _owner_record(source_decision_id, subject, owned)
    _plan_allows(granted, symbol, timeframe)

    try:
        raw = await authorities.sealed_reader(tenant, source_decision_id)
    except Exception as exc:
        raise CanonicalGateDenied("L7_SIGNED_SOURCE_UNAVAILABLE") from exc
    try:
        verified: VerifiedSyntheticDecision = verify_synthetic_ndsp_contract(
            raw, public_keys=authorities.source_test_public_keys, now_utc=now_utc,
        )
    except NDSPContractRejected as exc:
        raise CanonicalGateDenied("L7_SIGNATURE_OR_CONTRACT_REJECTED") from exc

    if (verified.source_environment != "test"
            or verified.asset != symbol or verified.timeframe != timeframe
            or verified.decision_state != "BLOCKED"
            or verified.direction != "FLAT"
            or verified.execution_authorized):
        _deny("L7_SIGNED_SOURCE_CONTEXT_MISMATCH")
    return ReadOnlySourceDecision(
        document=bytes(raw), source_decision_id=source_decision_id,
        tenant_id=tenant, decision_version=verified.decision_version,
    )
