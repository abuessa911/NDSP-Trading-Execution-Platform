"""Detached NDSP-NEX-1.0 consumer contract candidate: review ONLY.

Not imported by NEX M1 FastAPI, no background worker, no order endpoint,
no positions, no broker libraries, and no live/paper execution.  This is
prospective M2 trust-boundary work in an isolated source branch only.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Collection, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

DOMAIN = b"NDSP-NEX-1.0:completed-decision\n"
EXPECTED_FIELDS = frozenset({
    "contract_version", "issuer", "audience", "decision_id", "asset_id",
    "market", "timeframe", "analysis_mode", "state", "l15_state", "l15_blocked",
    "l16_state", "l16_allowed", "actual_layers_executed", "evidence_sha256",
    "source_revision", "issued_at_utc", "expires_at_utc", "nonce",
    "no_execution_authority", "not_recommendation",
})


def canonical_payload_bytes(payload: Mapping[str, Any]) -> bytes:
    """Signed bytes. Reject NaN/Infinity and avoid ambiguous serializers."""
    return DOMAIN + json.dumps(
        dict(payload), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def _time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OverflowError):
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def _result(code: str, *, accepted: bool = False) -> dict[str, Any]:
    return {
        "status": "CANDIDATE_STUDY_ONLY" if accepted else "REJECTED",
        "reason_code": code, "signed_contract_valid": accepted,
        "new_entry_allowed": False, "broker_send_allowed": False,
        "modify_existing_positions": False, "execution_authority": False,
        "runtime_integration_enabled": False,
    }


def review_signed_decision(
    envelope: Mapping[str, Any] | None,
    *,
    trusted_public_keys: Mapping[str, bytes],
    expected_asset_id: str,
    seen_decision_ids: Collection[str],
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Strictly validate a detached signature, then stop at study-only.

    This cannot grant execution. The caller must independently provision
    public keys and durable replay protection before any future integration.
    """
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        return _result("CLOCK_NOT_UTC_AWARE")
    if not isinstance(envelope, Mapping) or set(envelope) != {
        "key_id", "signature_base64", "payload",
    }:
        return _result("ENVELOPE_SHAPE_INVALID")
    key_id = envelope.get("key_id")
    signature_text = envelope.get("signature_base64")
    payload = envelope.get("payload")
    if not isinstance(key_id, str) or not key_id or key_id not in trusted_public_keys:
        return _result("UNTRUSTED_SIGNER")
    if not isinstance(signature_text, str) or not isinstance(payload, Mapping):
        return _result("INVALID_SIGNATURE_OR_PAYLOAD")
    if set(payload) != EXPECTED_FIELDS:
        return _result("PAYLOAD_SCHEMA_MISMATCH")
    try:
        raw_signature = base64.b64decode(signature_text, validate=True)
        if len(raw_signature) != 64:
            return _result("SIGNATURE_LENGTH_INVALID")
        public_key = trusted_public_keys[key_id]
        if not isinstance(public_key, bytes) or len(public_key) != 32:
            return _result("PUBLIC_KEY_INVALID")
        message = canonical_payload_bytes(payload)
        Ed25519PublicKey.from_public_bytes(public_key).verify(raw_signature, message)
    except (ValueError, TypeError, binascii.Error, InvalidSignature):
        return _result("SIGNATURE_INVALID")
    if (payload.get("contract_version") != "NDSP-NEX-1.0"
            or payload.get("issuer") != "NDSP"
            or payload.get("audience") != "NEX"):
        return _result("CONTRACT_IDENTITY_MISMATCH")
    asset = payload.get("asset_id")
    if (not isinstance(asset, str) or not asset or not expected_asset_id
            or asset != expected_asset_id):
        return _result("ASSET_MISMATCH")
    decision_id = payload.get("decision_id")
    nonce = payload.get("nonce")
    if (not isinstance(decision_id, str) or not re.fullmatch(r"CD-[A-Z0-9]{16,32}", decision_id)
            or not isinstance(nonce, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,96}", nonce)):
        return _result("DECISION_IDENTITY_INVALID")
    if decision_id in seen_decision_ids:
        return _result("REPLAY_DETECTED")
    if not (isinstance(payload.get("source_revision"), str)
            and re.fullmatch(r"[0-9a-f]{40}", payload["source_revision"])
            and isinstance(payload.get("evidence_sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", payload["evidence_sha256"])):
        return _result("SOURCE_EVIDENCE_ID_INVALID")
    issued = _time(payload.get("issued_at_utc"))
    expires = _time(payload.get("expires_at_utc"))
    if issued is None or expires is None or expires <= issued:
        return _result("DECISION_CLOCK_INVALID")
    if expires - issued > timedelta(seconds=300):
        return _result("DECISION_TTL_EXCESSIVE")
    if issued > now.astimezone(timezone.utc) + timedelta(seconds=30):
        return _result("DECISION_FUTURE_DATED")
    if expires <= now.astimezone(timezone.utc):
        return _result("DECISION_STALE")
    if (payload.get("state") != "READY"
            or payload.get("l15_state") != "PASSED"
            or payload.get("l15_blocked") is not False
            or payload.get("l16_state") != "READY"
            or payload.get("l16_allowed") is not True):
        return _result("DECISION_MONITORING_OR_BLOCKED")
    if (payload.get("actual_layers_executed") != 16
            or isinstance(payload.get("actual_layers_executed"), bool)):
        return _result("LAYER_CHAIN_INCOMPLETE")
    if (payload.get("no_execution_authority") is not True
            or payload.get("not_recommendation") is not True):
        return _result("EXECUTION_AUTHORITY_FORBIDDEN")
    for key in ("market", "timeframe", "analysis_mode"):
        if not isinstance(payload.get(key), str) or not payload[key].strip():
            return _result("DECISION_CONTEXT_INCOMPLETE")
    # Even a valid signed READY decision is NOT an order in NEX M1.
    return _result("M1_NO_EXECUTION_ALLOWED", accepted=True)
