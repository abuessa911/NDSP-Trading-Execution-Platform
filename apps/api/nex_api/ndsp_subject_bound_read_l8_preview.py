"""M2-B L8 — TEST-ONLY authority SUBJECT binding and read orchestration.

All service authorities are locally dependency-injected synthetic mocks.
No real NDSP 9020/9001/9091/CDS traffic, HTTP runtime, accounts, or orders.
The existing real 9091 response is NOT signed or subject-bound; this code
models the MISSING explicit authoritative contract, not its deployment.

The test attester is a dedicated, ephemeral EdDSA issuer. Do NOT infer that
its acceptance certifies a real NDSP production authority or route.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable, Mapping, NoReturn

import jwt

from nex_api.ndsp_canonical_read_gate_l7_preview import (
    CanonicalGateDenied,
    ReadOnlySourceDecision,
    SyntheticCanonicalAuthorities,
    _canonical_uuid,
    read_only_test_decision,
)

_PROOF_ISSUER = "ndsp-l8-ephemeral-test-authority"
_PROOF_AUDIENCE = "nex-l8-read-only-test"
_PROOF_VERSION = "NDSP-NEX-L8-TEST-SUBJECT-BINDING-V1"
_ROUTE_SESSION = "canonical-auth-session-9020"
_ROUTE_ENTITLEMENT = "canonical-entitlement-9091"
_MAX_PROOF_SIZE = 8192
_MAX_TTL_SECONDS = 30
_EXACT_CLAIMS = frozenset({
    "iss", "aud", "sub", "iat", "nbf", "exp", "jti",
    "version", "source_environment", "session_authority",
    "entitlement_authority", "session_digest", "entitlement_digest",
    "source_decision_id", "scope", "request_nonce",
})


@dataclass(frozen=True, slots=True)
class SyntheticSubjectBindingAuthorities:
    """Test-only services. No production transports or trust roots."""
    gate: SyntheticCanonicalAuthorities
    attest: Callable[[str, str], Awaitable[str]]
    attester_public_key_pem: bytes
    synthetic_only: bool = True


def _deny(reason: str) -> NoReturn:
    raise CanonicalGateDenied(reason)


def _sha(value: Mapping[str, object]) -> str:
    if not isinstance(value, dict):
        _deny("L8_AUTHORITY_DATA_INVALID")
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise CanonicalGateDenied("L8_AUTHORITY_DATA_INVALID") from exc
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _verify_binding(
    token: str, *,
    pinned_public_key_pem: bytes,
    source_id: str, nonce: str, now_utc: datetime,
    session: Mapping[str, object], entitlement: Mapping[str, object],
) -> None:
    if (not isinstance(token, str)
            or not 0 < len(token.encode("utf-8")) <= _MAX_PROOF_SIZE
            or not isinstance(pinned_public_key_pem, bytes)
            or b"BEGIN PUBLIC KEY" not in pinned_public_key_pem):
        _deny("L8_TRUST_PROOF_UNAVAILABLE")
    try:
        claims = jwt.decode(
            token, pinned_public_key_pem, algorithms=["EdDSA"],
            issuer=_PROOF_ISSUER, audience=_PROOF_AUDIENCE,
            options={
                "verify_exp": False, "verify_nbf": False,
                "verify_iat": False, "require": sorted(_EXACT_CLAIMS),
            },
        )
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise CanonicalGateDenied("L8_BINDING_SIGNATURE_INVALID") from exc
    if not isinstance(claims, dict) or set(claims) != _EXACT_CLAIMS:
        _deny("L8_BINDING_FIELDS_INVALID")
    user = session.get("user")
    if (session.get("ok") is not True or not isinstance(user, dict)
            or user.get("status") not in ("active", "approved", "verified")):
        _deny("L8_SESSION_INACTIVE_OR_UNVERIFIED")
    subject = _canonical_uuid(user.get("id"), "L8_SESSION_SUBJECT_INVALID")
    signed_subject = _canonical_uuid(claims["sub"], "L8_PROOF_SUBJECT_INVALID")
    if subject != signed_subject:
        _deny("L8_PROOF_SUBJECT_MISMATCH")
    if (entitlement.get("ok") is not True
            or entitlement.get("authority") != "NDSP_CANONICAL_ENTITLEMENT_9091_V1"):
        _deny("L8_ENTITLEMENT_UNVERIFIED")
    if (claims["version"] != _PROOF_VERSION
            or claims["source_environment"] != "test"
            or claims["session_authority"] != _ROUTE_SESSION
            or claims["entitlement_authority"] != _ROUTE_ENTITLEMENT
            or claims["scope"] != "ndsp.source.read.synthetic"
            or claims["source_decision_id"] != source_id
            or claims["request_nonce"] != nonce
            or claims["session_digest"] != _sha(session)
            or claims["entitlement_digest"] != _sha(entitlement)):
        _deny("L8_SUBJECT_BOUND_AUTHORITY_MISMATCH")

    for name in ("iat", "nbf", "exp"):
        if type(claims[name]) is not int:
            _deny("L8_TIME_CLAIMS_INVALID")
    now = int(now_utc.timestamp())
    issued = claims["iat"]
    not_before = claims["nbf"]
    expires = claims["exp"]
    if (not issued <= now < expires
            or not_before > now or not_before < issued
            or expires - issued > _MAX_TTL_SECONDS
            or now - issued > _MAX_TTL_SECONDS):
        _deny("L8_BINDING_EXPIRED_OR_FUTURE")
    if not isinstance(claims["jti"], str) or len(claims["jti"]) < 16:
        _deny("L8_JTI_INVALID")


async def read_subject_bound_test_only(
    *, credentials: str, source_decision_id: str,
    authorities: SyntheticSubjectBindingAuthorities,
    now_utc: datetime,
) -> ReadOnlySourceDecision:
    """Require a TEST attestation before invoking the existing L7 sealed reader.

    Provisional design: the real 9091 JSON has no bound subject field and must
    NOT be substituted for a verified test attestation. No real adapter exists.
    """
    if (not isinstance(authorities, SyntheticSubjectBindingAuthorities)
            or not authorities.synthetic_only or not authorities.gate.synthetic_only
            or not isinstance(credentials, str)
            or not 0 < len(credentials) <= 4096
            or not isinstance(source_decision_id, str)
            or not isinstance(now_utc, datetime) or now_utc.tzinfo is None
            or now_utc.utcoffset() != timezone.utc.utcoffset(now_utc)):
        _deny("L8_ONLY_SYNTHETIC_CONTEXT_ALLOWED")

    nonce = secrets.token_urlsafe(24)
    try:
        session = await authorities.gate.session(credentials)
    except Exception as exc:
        raise CanonicalGateDenied("L8_SESSION_AUTHORITY_UNAVAILABLE") from exc
    if not isinstance(session, dict):
        _deny("L8_SESSION_UNVERIFIED")
    try:
        entitlement = await authorities.gate.entitlement(credentials)
    except Exception as exc:
        raise CanonicalGateDenied("L8_ENTITLEMENT_AUTHORITY_UNAVAILABLE") from exc
    if not isinstance(entitlement, dict):
        _deny("L8_ENTITLEMENT_UNVERIFIED")
    try:
        signed_proof = await authorities.attest(credentials, nonce)
    except Exception as exc:
        raise CanonicalGateDenied("L8_BINDING_AUTHORITY_UNAVAILABLE") from exc
    _verify_binding(
        signed_proof, pinned_public_key_pem=authorities.attester_public_key_pem,
        source_id=source_decision_id, nonce=nonce, now_utc=now_utc,
        session=session, entitlement=entitlement,
    )

    async def _cached_session(_credentials: str) -> Mapping[str, object]:
        if _credentials != credentials:
            _deny("L8_CREDENTIAL_REUSE_DENIED")
        return session

    async def _cached_entitlement(_credentials: str) -> Mapping[str, object]:
        if _credentials != credentials:
            _deny("L8_CREDENTIAL_REUSE_DENIED")
        return entitlement

    # Avoid a TOCTOU refetch after signing: L7 operates against the very
    # same snapshots proven by the test authority before source access.
    secured_gate = SyntheticCanonicalAuthorities(
        session=_cached_session, entitlement=_cached_entitlement,
        ownership=authorities.gate.ownership,
        sealed_reader=authorities.gate.sealed_reader,
        source_test_public_keys=authorities.gate.source_test_public_keys,
        synthetic_only=True,
    )
    return await read_only_test_decision(
        credentials=credentials, source_decision_id=source_decision_id,
        authorities=secured_gate, now_utc=now_utc,
    )
