"""M2-B synthetic-test-only verification for proposed NDSP-NEX-1.0 envelope.

No production NDSP data, HTTP endpoint, key loading, persistence, orders, or
decision normalization. The proposed Ed25519/canonical-JSON signing profile
requires explicit bilateral NDSP approval and golden test vectors.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

CONTRACT_VERSION = "NDSP-NEX-1.0"
MAX_DOCUMENT_BYTES = 16_384
MANDATORY_KEYS = frozenset({
    "contract_version", "decision_id", "decision_version", "asset", "market",
    "timeframe", "direction", "decision_state", "scenario_state", "risk_class",
    "valid_from", "valid_until", "issued_at", "source_system",
    "source_environment", "evidence_hash", "key_id", "signature",
})
_UTC = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z\Z", re.ASCII)
_ASSET = re.compile(r"[A-Z0-9]{5,20}\Z", re.ASCII)
_KEY = re.compile(r"[A-Za-z0-9_.-]{1,80}\Z", re.ASCII)
_HASH = re.compile(r"sha256:[a-f0-9]{64}\Z", re.ASCII)
_TIMEFRAMES = frozenset({"5m", "15m", "4H"})
_DIRECTIONS = frozenset({"LONG", "SHORT", "FLAT"})
_DECISION_STATES = frozenset({"EXECUTABLE", "BLOCKED", "EXPIRED"})
_SCENARIO_STATES = frozenset({"ACTIVE", "UNDER_MONITORING", "CLOSED"})
_RISK_CLASSES = frozenset({"LOW", "MODERATE", "HIGH", "BLOCKED"})


class NDSPContractRejected(Exception):
    """Bounded non-sensitive failure code; no raw payload or signed data in errors."""

    def __init__(self, reason_code: str):
        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True, slots=True)
class VerifiedSyntheticDecision:
    decision_id: UUID
    decision_version: int
    asset: str
    timeframe: str
    direction: str
    decision_state: str
    scenario_state: str
    risk_class: str
    valid_until: datetime
    evidence_hash: str
    source_environment: str = "test"
    # Verification does not grant execution permission or create an intent.
    execution_authorized: bool = False


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    obj: dict[str, object] = {}
    for key, value in pairs:
        if key in obj:
            raise NDSPContractRejected("NDSP_DUPLICATE_FIELD")
        obj[key] = value
    return obj


def _decode(raw: bytes) -> dict[str, object]:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_DOCUMENT_BYTES:
        raise NDSPContractRejected("NDSP_PAYLOAD_SIZE")
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
    except (UnicodeDecodeError, ValueError, TypeError) as exc:
        raise NDSPContractRejected("NDSP_MALFORMED_JSON") from exc
    if not isinstance(document, dict):
        raise NDSPContractRejected("NDSP_SCHEMA_INVALID")
    if set(document) != MANDATORY_KEYS:
        raise NDSPContractRejected("NDSP_FIELD_SET_INVALID")
    return document


def _utc(value: object) -> datetime:
    if not isinstance(value, str) or _UTC.fullmatch(value) is None:
        raise NDSPContractRejected("NDSP_TIME_INVALID")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NDSPContractRejected("NDSP_TIME_INVALID") from exc
    return result


def _one_of(document: dict[str, object], field: str, allowed: frozenset[str]) -> str:
    value = document[field]
    if not isinstance(value, str) or value not in allowed:
        raise NDSPContractRejected("NDSP_SCHEMA_INVALID")
    return value


def _validated(document: dict[str, object], now: datetime) -> tuple[UUID, int, datetime]:
    if document["contract_version"] != CONTRACT_VERSION:
        raise NDSPContractRejected("NDSP_CONTRACT_VERSION_REJECTED")
    if document["source_system"] != "NDSP" or document["source_environment"] != "test":
        # The actual NDSP production publisher and signer are NOT connected.
        raise NDSPContractRejected("NDSP_SOURCE_NOT_APPROVED")
    decision_id = document["decision_id"]
    if not isinstance(decision_id, str):
        raise NDSPContractRejected("NDSP_DECISION_ID_INVALID")
    try:
        identifier = UUID(decision_id)
    except ValueError as exc:
        raise NDSPContractRejected("NDSP_DECISION_ID_INVALID") from exc
    if str(identifier) != decision_id:
        raise NDSPContractRejected("NDSP_DECISION_ID_INVALID")
    version = document["decision_version"]
    if type(version) is not int or not 1 <= version <= 2**63 - 1:
        raise NDSPContractRejected("NDSP_DECISION_VERSION_INVALID")
    asset = document["asset"]
    if not isinstance(asset, str) or _ASSET.fullmatch(asset) is None:
        raise NDSPContractRejected("NDSP_ASSET_INVALID")
    if document["market"] != "CRYPTO":
        raise NDSPContractRejected("NDSP_MARKET_NOT_APPROVED")
    _one_of(document, "timeframe", _TIMEFRAMES)
    _one_of(document, "direction", _DIRECTIONS)
    _one_of(document, "decision_state", _DECISION_STATES)
    _one_of(document, "scenario_state", _SCENARIO_STATES)
    _one_of(document, "risk_class", _RISK_CLASSES)
    proof = document["evidence_hash"]
    if not isinstance(proof, str) or _HASH.fullmatch(proof) is None:
        raise NDSPContractRejected("NDSP_EVIDENCE_HASH_INVALID")
    issued, beginning, end = (
        _utc(document["issued_at"]), _utc(document["valid_from"]),
        _utc(document["valid_until"]),
    )
    if issued > now or beginning > now or now >= end or issued > end:
        raise NDSPContractRejected("NDSP_OUTSIDE_VALIDITY")
    return identifier, version, end


def verify_synthetic_ndsp_contract(
    raw: bytes, *,
    public_keys: Mapping[str, bytes],
    now_utc: datetime,
) -> VerifiedSyntheticDecision:
    """Verify proposed synthetic Ed25519 profile only; NEVER production signal intake.

    The trusted key registry must be provided by a test fixture, not by NDSP
    payloads or an unauthenticated network response. Replay and tenancy remain
    unimplemented and are separate mandatory acceptance gates.
    """
    if now_utc.tzinfo is None or now_utc.utcoffset() != timezone.utc.utcoffset(now_utc):
        raise NDSPContractRejected("NDSP_CLOCK_NOT_UTC")
    document = _decode(raw)
    key_id = document["key_id"]
    if not isinstance(key_id, str) or _KEY.fullmatch(key_id) is None:
        raise NDSPContractRejected("NDSP_KEY_NOT_APPROVED")
    key = public_keys.get(key_id)
    if not isinstance(key, bytes) or len(key) != 32:
        raise NDSPContractRejected("NDSP_KEY_NOT_APPROVED")
    signature_text = document["signature"]
    if not isinstance(signature_text, str) or len(signature_text) > 100:
        raise NDSPContractRejected("NDSP_SIGNATURE_INVALID")
    try:
        signature = base64.b64decode(signature_text, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise NDSPContractRejected("NDSP_SIGNATURE_INVALID") from exc
    if len(signature) != 64:
        raise NDSPContractRejected("NDSP_SIGNATURE_INVALID")
    # A *proposed*, explicitly test-only profile. NDSP must approve matching
    # canonical bytes and submit independently signed golden vectors first.
    signing_payload = {k: v for k, v in document.items() if k != "signature"}
    signed = json.dumps(
        signing_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    try:
        Ed25519PublicKey.from_public_bytes(key).verify(signature, signed)
    except (InvalidSignature, ValueError) as exc:
        raise NDSPContractRejected("NDSP_SIGNATURE_INVALID") from exc
    decision_id, version, end = _validated(document, now_utc)
    return VerifiedSyntheticDecision(
        decision_id=decision_id, decision_version=version,
        asset=str(document["asset"]), timeframe=str(document["timeframe"]),
        direction=str(document["direction"]),
        decision_state=str(document["decision_state"]),
        scenario_state=str(document["scenario_state"]),
        risk_class=str(document["risk_class"]),
        valid_until=end, evidence_hash=str(document["evidence_hash"]),
    )
