"""Real cryptographic interoperability: isolated NDSP source-slice test publisher -> NEX.

Both endpoints are test-only. This is not a real NDSP production decision.
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from nex_api.ndsp_contract_preview import (
    NDSPContractRejected,
    verify_synthetic_ndsp_contract,
)

ROOT = Path(__file__).parent / "fixtures" / "ndsp_source_slice"
NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)
TEST_KEY_ID = "ndsp-source-slice-test-20261014"


def load_fixture():
    doc = (ROOT / "signed_synthetic_decision.json").read_bytes()
    bundle = json.loads((ROOT / "trusted_test_public_key.json").read_text())
    parsed = json.loads(doc)
    assert bundle["private_key_persisted"] is False
    assert bundle["profile_status"] == "PROPOSED_SYNTHETIC_TEST_ONLY"
    assert bundle["canonicalization"] == "ASCII_SORTED_COMPACT_JSON_UTF8_PROPOSED_TEST_ONLY"
    assert bundle["key_id"] == parsed["key_id"] == TEST_KEY_ID
    unsigned = {k: v for k, v in parsed.items() if k != "signature"}
    canonical = json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    assert hashlib.sha256(canonical).hexdigest() == bundle["signed_bytes_sha256"]
    key = base64.b64decode(bundle["public_key_base64"], validate=True)
    assert len(key) == 32
    return doc, key


def verify(raw: bytes, pub: bytes, now=NOW):
    return verify_synthetic_ndsp_contract(
        raw, public_keys={TEST_KEY_ID: pub}, now_utc=now,
    )


def test_source_slice_publisher_signature_verified_by_independent_nex():
    raw, pub = load_fixture()
    result = verify(raw, pub)
    assert result.decision_state == "BLOCKED"
    assert result.scenario_state == "UNDER_MONITORING"
    assert result.direction == "FLAT"
    assert result.source_environment == "test"
    assert result.execution_authorized is False


def test_changed_issued_envelope_fails_signature():
    raw, pub = load_fixture()
    doc = json.loads(raw)
    doc["decision_state"] = "EXECUTABLE"
    with pytest.raises(NDSPContractRejected, match="NDSP_SIGNATURE_INVALID"):
        verify(json.dumps(doc).encode(), pub)


def test_unknown_signing_key_and_invalid_public_key_are_denied():
    raw, pub = load_fixture()
    with pytest.raises(NDSPContractRejected, match="NDSP_KEY_NOT_APPROVED"):
        verify_synthetic_ndsp_contract(raw, public_keys={"unknown": pub}, now_utc=NOW)
    with pytest.raises(NDSPContractRejected, match="NDSP_KEY_NOT_APPROVED"):
        verify(raw, pub[:-1])


def test_expired_source_completed_decision_is_not_accepted():
    raw, pub = load_fixture()
    expired = datetime(2026, 10, 15, 10, tzinfo=timezone.utc)
    with pytest.raises(NDSPContractRejected, match="NDSP_OUTSIDE_VALIDITY"):
        verify(raw, pub, expired)


def test_only_allowlisted_contract_no_private_payload_or_source_id():
    raw, pub = load_fixture()
    doc = json.loads(raw)
    assert "CD-TEST-20261014" not in raw.decode()
    assert "DO_NOT_EXPORT" not in raw.decode()
    assert "TDL" not in raw.decode()
    assert "NMP" not in raw.decode()
    assert "no-export@example.test" not in raw.decode()
    assert doc["source_environment"] == "test"
    assert doc["decision_state"] == "BLOCKED"
    assert not verify(raw, pub).execution_authorized
