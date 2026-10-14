"""Cross-project conformance: isolated NDSP-side test issuer -> NEX test verifier.

The stored public key is an explicitly pinned TEST TRUST ANCHOR.
This is NOT an approved NDSP production signing key or production decision.
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

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ndsp_publisher_preview"
CLOCK = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
KEY_ID = "ndsp-dev-preview-20261014"


def fixture() -> tuple[bytes, bytes]:
    publisher_public_bundle = json.loads(
        (FIXTURES / "trusted_test_public_key.json").read_text(),
    )
    # Never read a public key from the decision itself.
    assert publisher_public_bundle["profile_status"] == "PROPOSED_SYNTHETIC_TEST_ONLY"
    assert publisher_public_bundle["contract_version"] == "NDSP-NEX-1.0"
    assert publisher_public_bundle["key_id"] == KEY_ID
    assert publisher_public_bundle["algorithm"] == "Ed25519"
    assert publisher_public_bundle["private_key_persisted"] is False
    trust_key = base64.b64decode(publisher_public_bundle["public_key_base64"], validate=True)
    assert len(trust_key) == 32
    signed_payload = (FIXTURES / "signed_synthetic_decision.json").read_bytes()
    document = json.loads(signed_payload)
    unsigned = {name: value for name, value in document.items() if name != "signature"}
    canonical = json.dumps(
        unsigned, ensure_ascii=False, separators=(",", ":"), sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
    assert hashlib.sha256(canonical).hexdigest() == publisher_public_bundle[
        "signed_bytes_sha256"
    ]
    return signed_payload, trust_key


def verify(blob: bytes, test_key: bytes, *, now: datetime = CLOCK):
    return verify_synthetic_ndsp_contract(
        blob, public_keys={KEY_ID: test_key}, now_utc=now,
    )


def test_isolated_ndsp_side_publisher_golden_signature_verifies_in_nex():
    raw, test_key = fixture()
    result = verify(raw, test_key)
    assert result.source_environment == "test"
    assert result.decision_version == 1
    assert result.asset == "BTCUSDT"
    assert result.timeframe == "4H"
    assert result.direction == "FLAT"
    assert result.decision_state == "BLOCKED"
    assert result.execution_authorized is False


def test_golden_fixture_tampering_breaks_cross_boundary_signature():
    raw, test_key = fixture()
    document = json.loads(raw)
    document["direction"] = "LONG"
    with pytest.raises(NDSPContractRejected, match="NDSP_SIGNATURE_INVALID"):
        verify(json.dumps(document).encode("utf-8"), test_key)


def test_golden_fixture_unknown_signing_key_rejected():
    raw, key = fixture()
    with pytest.raises(NDSPContractRejected, match="NDSP_KEY_NOT_APPROVED"):
        verify_synthetic_ndsp_contract(raw, public_keys={"wrong-key": key}, now_utc=CLOCK)


def test_golden_fixture_expired_after_valid_until():
    raw, key = fixture()
    with pytest.raises(NDSPContractRejected, match="NDSP_OUTSIDE_VALIDITY"):
        verify(raw, key, now=datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc))


def test_golden_fixture_never_claims_or_grants_production_execution():
    raw, key = fixture()
    document = json.loads(raw)
    assert document["source_environment"] == "test"
    assert document["risk_class"] == "BLOCKED"
    assert document["scenario_state"] == "UNDER_MONITORING"
    assert "tdl_thresholds" not in document
    assert "nmp_formula" not in document
    document["source_environment"] = "production"
    # Re-signing is not permitted and must not be simulated with a test key.
    with pytest.raises(NDSPContractRejected, match="NDSP_SIGNATURE_INVALID"):
        verify(json.dumps(document).encode(), key)
