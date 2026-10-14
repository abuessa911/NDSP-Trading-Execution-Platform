"""M2-B isolated test-only binding of a synthetic CDS source record to NEX.

This is not a production source attestation, tenant-authorization or trading
capability. It must never be registered as an API/consumer or used with real
NDSP decisions without a separately approved issuer binding contract.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Mapping
from uuid import UUID, uuid5

from nex_api.ndsp_contract_preview import (
    NDSPContractRejected,
    VerifiedSyntheticDecision,
    verify_synthetic_ndsp_contract,
)

# Matches the independent development-only Node test issuer's UUID namespace.
# NOT a production-approved CD-* -> UUID mapping.
TEST_NAMESPACE = UUID("52b3b8b4-c8d6-4e11-b5aa-1bb93e21f5ad")
SOURCE_KEYS = frozenset({
    "decision_id", "decision_state", "visibility", "market", "symbol",
    "timeframe", "version", "completed_at", "published_at", "expires_at",
})
SOURCE_ID_PATTERN = re.compile(r"CD-[A-Z0-9-]{5,64}\Z", flags=re.ASCII)
SYMBOL_PATTERN = re.compile(r"[A-Z0-9]{5,20}\Z", flags=re.ASCII)
TIME_PATTERN = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ\Z", flags=re.ASCII)


def _time(value: object) -> datetime:
    if not isinstance(value, str) or not TIME_PATTERN.fullmatch(value):
        raise NDSPContractRejected("NDSP_SOURCE_TIME_INVALID")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NDSPContractRejected("NDSP_SOURCE_TIME_INVALID") from exc
    if parsed.isoformat(timespec="seconds") != value.replace("Z", "+00:00"):
        raise NDSPContractRejected("NDSP_SOURCE_TIME_INVALID")
    return parsed


def verify_test_only_source_binding(
    raw: bytes, *,
    public_keys: Mapping[str, bytes],
    source: Mapping[str, object],
    now_utc: datetime,
) -> VerifiedSyntheticDecision:
    """Require both independently pinned signature and exact synthetic source.

    Never return execution authority. No real NDSP CDS rows can satisfy the
    issuer's explicit synthetic provenance/approved version requirements.
    """
    verified = verify_synthetic_ndsp_contract(
        raw, public_keys=public_keys, now_utc=now_utc,
    )
    if not isinstance(source, Mapping) or set(source) != SOURCE_KEYS:
        raise NDSPContractRejected("NDSP_SOURCE_FIELD_SET_INVALID")
    source_id = source["decision_id"]
    symbol = source["symbol"]
    version = source["version"]
    if not isinstance(source_id, str) or not SOURCE_ID_PATTERN.fullmatch(source_id):
        raise NDSPContractRejected("NDSP_SOURCE_ID_INVALID")
    if not isinstance(symbol, str) or not SYMBOL_PATTERN.fullmatch(symbol):
        raise NDSPContractRejected("NDSP_SOURCE_ASSET_INVALID")
    if type(version) is not int or not 1 <= version <= 2**53 - 1:
        raise NDSPContractRejected("NDSP_SOURCE_VERSION_INVALID")
    if (source["decision_state"] != "Published"
            or source["visibility"] != "public"
            or source["market"] != "CRYPTO"
            or source["timeframe"] not in ("5m", "15m", "4H")):
        raise NDSPContractRejected("NDSP_SOURCE_NOT_ELIGIBLE")
    completed = _time(source["completed_at"])
    published = _time(source["published_at"])
    expires = _time(source["expires_at"])
    if not completed <= published < expires:
        raise NDSPContractRejected("NDSP_SOURCE_VALIDITY_INVALID")
    canonical = json.dumps(
        dict(source), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    expected_hash = "sha256:" + hashlib.sha256(canonical).hexdigest()
    if (verified.decision_id != uuid5(TEST_NAMESPACE, source_id)
            or verified.decision_version != version
            or verified.asset != symbol
            or verified.timeframe != source["timeframe"]
            or verified.evidence_hash != expected_hash
            or verified.valid_until != expires
            or verified.source_environment != "test"
            or verified.decision_state != "BLOCKED"
            or verified.direction != "FLAT"
            or verified.scenario_state != "UNDER_MONITORING"
            or verified.risk_class != "BLOCKED"):
        raise NDSPContractRejected("NDSP_SYNTHETIC_SOURCE_BINDING_MISMATCH")
    if verified.execution_authorized:
        raise NDSPContractRejected("NDSP_PREVIEW_EXECUTION_DENIED")
    return verified
