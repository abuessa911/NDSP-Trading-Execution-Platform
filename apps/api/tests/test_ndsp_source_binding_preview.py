"""Test-only source identity/version/evidence binding for CDS -> NEX.

All input is explicitly synthetic and independent of actual NDSP databases.
Signature test vector is from the isolated Contabo source-derived Node issuer.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from nex_api.ndsp_contract_preview import NDSPContractRejected
from nex_api.ndsp_source_binding_preview import (
    TEST_NAMESPACE,
    verify_test_only_source_binding,
)
from uuid import uuid5

ROOT = Path(__file__).parent / "fixtures" / "ndsp_source_slice"
NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)


def inputs() -> tuple[bytes, dict[str, bytes], dict[str, object]]:
    import base64

    document = (ROOT / "signed_synthetic_decision.json").read_bytes()
    bundle = json.loads((ROOT / "trusted_test_public_key.json").read_text())
    assert bundle["profile_status"] == "PROPOSED_SYNTHETIC_TEST_ONLY"
    keys = {bundle["key_id"]: base64.b64decode(bundle["public_key_base64"], validate=True)}
    # Explicit synthetic CDS-001 fixture in the isolated development emitter.
    # This is NOT a real NDSP completed decision or signed source attestation.
    source: dict[str, object] = {
        "completed_at": "2026-10-14T09:00:00Z",
        "decision_id": "CD-TEST-20261014",
        "decision_state": "Published",
        "expires_at": "2026-10-15T10:00:00Z",
        "market": "CRYPTO",
        "published_at": "2026-10-14T10:00:00Z",
        "symbol": "BTCUSDT",
        "timeframe": "4H",
        "version": 1,
        "visibility": "public",
    }
    return document, keys, source


def bound(source: dict[str, object]):
    doc, keys, _ = inputs()
    return verify_test_only_source_binding(
        doc, public_keys=keys, source=source, now_utc=NOW,
    )


def test_signed_ndsp_cds_fixture_is_tied_to_stable_source_id_and_evidence():
    _, _, source = inputs()
    result = bound(source)
    assert result.decision_id == uuid5(TEST_NAMESPACE, "CD-TEST-20261014")
    assert result.decision_version == 1
    assert result.asset == "BTCUSDT"
    assert result.source_environment == "test"
    assert result.execution_authorized is False


@pytest.mark.parametrize(("field", "value", "reason"), [
    ("decision_id", "CD-TEST-ANOTHER", "NDSP_SYNTHETIC_SOURCE_BINDING_MISMATCH"),
    ("decision_id", "bad/id", "NDSP_SOURCE_ID_INVALID"),
    ("version", 2, "NDSP_SYNTHETIC_SOURCE_BINDING_MISMATCH"),
    ("version", None, "NDSP_SOURCE_VERSION_INVALID"),
    ("version", True, "NDSP_SOURCE_VERSION_INVALID"),
    ("version", 9007199254740992, "NDSP_SOURCE_VERSION_INVALID"),
    ("symbol", "ETHUSDT", "NDSP_SYNTHETIC_SOURCE_BINDING_MISMATCH"),
    ("symbol", "ethusdt", "NDSP_SOURCE_ASSET_INVALID"),
    ("timeframe", "15m", "NDSP_SYNTHETIC_SOURCE_BINDING_MISMATCH"),
    ("timeframe", "1m", "NDSP_SOURCE_NOT_ELIGIBLE"),
    ("decision_state", "Completed", "NDSP_SOURCE_NOT_ELIGIBLE"),
    ("visibility", "private", "NDSP_SOURCE_NOT_ELIGIBLE"),
    ("market", "FX", "NDSP_SOURCE_NOT_ELIGIBLE"),
    ("expires_at", "2026-10-15T11:00:00Z", "NDSP_SYNTHETIC_SOURCE_BINDING_MISMATCH"),
    ("published_at", "2026-10-14T11:00:00Z", "NDSP_SYNTHETIC_SOURCE_BINDING_MISMATCH"),
    ("published_at", "2026-10-16T10:00:00Z", "NDSP_SOURCE_VALIDITY_INVALID"),
    ("published_at", "2026-10-14T10:00:00+00:00", "NDSP_SOURCE_TIME_INVALID"),
])
def test_mutated_source_binding_is_denied(field, value, reason):
    _, _, source = inputs()
    source[field] = value
    with pytest.raises(NDSPContractRejected, match=reason):
        bound(source)


def test_missing_source_metadata_never_creates_a_version():
    _, _, source = inputs()
    del source["version"]
    with pytest.raises(NDSPContractRejected, match="NDSP_SOURCE_FIELD_SET_INVALID"):
        bound(source)


def test_source_additional_protected_payload_not_accepted():
    _, _, source = inputs()
    source["tdl_formula"] = "should never cross contract"
    with pytest.raises(NDSPContractRejected, match="NDSP_SOURCE_FIELD_SET_INVALID"):
        bound(source)


def test_signature_verification_must_succeed_before_source_binding():
    doc, keys, source = inputs()
    changed = json.loads(doc)
    changed["decision_state"] = "EXECUTABLE"
    with pytest.raises(NDSPContractRejected, match="NDSP_SIGNATURE_INVALID"):
        verify_test_only_source_binding(
            json.dumps(changed).encode(), public_keys=keys,
            source=source, now_utc=NOW,
        )


def test_source_binding_module_has_no_real_ndsp_client_or_order_api():
    import nex_api.ndsp_source_binding_preview as preview

    for name in ("fetch_decision", "place_order", "submit_order", "publish_to_ndsp"):
        assert not hasattr(preview, name)
