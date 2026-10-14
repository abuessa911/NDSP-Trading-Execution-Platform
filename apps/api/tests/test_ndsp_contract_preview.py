"""Only synthetic NDSP-NEX-1.0 vectors: no actual NDSP contract or live use."""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from uuid import UUID

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from nex_api.ndsp_contract_preview import (
    NDSPContractRejected,
    verify_synthetic_ndsp_contract,
)

NOW = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)


def sample() -> dict[str, object]:
    return {
        "contract_version": "NDSP-NEX-1.0",
        "decision_id": "f6e4e33e-7096-4a6b-9e2a-47e0b05af003",
        "decision_version": 17,
        "asset": "BTCUSDT",
        "market": "CRYPTO",
        "timeframe": "4H",
        "direction": "LONG",
        "decision_state": "BLOCKED",
        "scenario_state": "UNDER_MONITORING",
        "risk_class": "BLOCKED",
        "valid_from": "2026-10-14T11:00:00Z",
        "valid_until": "2026-10-14T13:00:00Z",
        "issued_at": "2026-10-14T11:00:00Z",
        "source_system": "NDSP",
        "source_environment": "test",
        "evidence_hash": "sha256:" + "a" * 64,
        "key_id": "synthetic-fixture-1",
        "signature": "",
    }


def signed(
    private: Ed25519PrivateKey, doc: dict[str, object] | None = None,
) -> bytes:
    decision = sample() if doc is None else dict(doc)
    to_sign = {key: value for key, value in decision.items() if key != "signature"}
    canonical = json.dumps(
        to_sign, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    ).encode()
    decision["signature"] = base64.b64encode(private.sign(canonical)).decode()
    return json.dumps(decision, separators=(",", ":"), ensure_ascii=False).encode()


@pytest.fixture
def keys():
    signer = Ed25519PrivateKey.generate()
    public = signer.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return signer, {"synthetic-fixture-1": public}


def accepted(raw: bytes, keys) -> object:
    return verify_synthetic_ndsp_contract(raw, public_keys=keys[1], now_utc=NOW)


def test_synthetic_signed_preview_is_verified_but_never_execution_authority(keys):
    result = accepted(signed(keys[0]), keys)
    assert result.decision_id == UUID(sample()["decision_id"])
    assert result.decision_version == 17
    assert result.asset == "BTCUSDT"
    assert result.direction == "LONG"
    assert result.decision_state == "BLOCKED"
    assert result.source_environment == "test"
    assert result.execution_authorized is False


def test_json_field_order_does_not_change_proposed_canonical_signature(keys):
    fields = sample()
    reordered = dict(reversed(list(fields.items())))
    assert accepted(signed(keys[0], reordered), keys).decision_version == 17


def test_changed_field_without_resigning_is_rejected(keys):
    doc = json.loads(signed(keys[0]))
    doc["direction"] = "SHORT"
    raw = json.dumps(doc).encode()
    with pytest.raises(NDSPContractRejected, match="NDSP_SIGNATURE_INVALID"):
        accepted(raw, keys)


def test_untrusted_public_signer_is_denied(keys):
    another = Ed25519PrivateKey.generate()
    with pytest.raises(NDSPContractRejected, match="NDSP_SIGNATURE_INVALID"):
        accepted(signed(another), keys)


def test_unknown_key_id_is_rejected_even_if_signed(keys):
    doc = sample()
    doc["key_id"] = "untrusted"
    with pytest.raises(NDSPContractRejected, match="NDSP_KEY_NOT_APPROVED"):
        accepted(signed(keys[0], doc), keys)


@pytest.mark.parametrize(("field", "replacement", "reason"), [
    ("contract_version", "NDSP-NEX-2.0", "NDSP_CONTRACT_VERSION_REJECTED"),
    ("source_system", "OTHER", "NDSP_SOURCE_NOT_APPROVED"),
    ("source_environment", "production", "NDSP_SOURCE_NOT_APPROVED"),
    ("decision_id", "bad", "NDSP_DECISION_ID_INVALID"),
    ("decision_version", 0, "NDSP_DECISION_VERSION_INVALID"),
    ("decision_version", True, "NDSP_DECISION_VERSION_INVALID"),
    ("asset", "btc/usdt", "NDSP_ASSET_INVALID"),
    ("market", "STOCKS", "NDSP_MARKET_NOT_APPROVED"),
    ("timeframe", "1m", "NDSP_SCHEMA_INVALID"),
    ("direction", "BUY", "NDSP_SCHEMA_INVALID"),
    ("decision_state", "READY", "NDSP_SCHEMA_INVALID"),
    ("scenario_state", "UNKNOWN", "NDSP_SCHEMA_INVALID"),
    ("risk_class", "UNDEFINED", "NDSP_SCHEMA_INVALID"),
    ("evidence_hash", "sha256:bad", "NDSP_EVIDENCE_HASH_INVALID"),
    ("issued_at", "2026-10-14T12:30:00Z", "NDSP_OUTSIDE_VALIDITY"),
    ("valid_until", "2026-10-14T11:00:00Z", "NDSP_OUTSIDE_VALIDITY"),
    ("valid_from", "2026-10-14T13:00:00Z", "NDSP_OUTSIDE_VALIDITY"),
    ("valid_until", "2026-10-14T13:00:00+01:00", "NDSP_TIME_INVALID"),
])
def test_signed_but_unapproved_values_are_blocked(keys, field, replacement, reason):
    payload = sample()
    payload[field] = replacement
    with pytest.raises(NDSPContractRejected, match=reason):
        accepted(signed(keys[0], payload), keys)


def test_duplicated_fields_cannot_be_masked_by_signature(keys):
    raw = signed(keys[0])
    text = raw.decode().replace('"contract_version":', '"contract_version":"NDSP-NEX-1.0","contract_version":', 1)
    with pytest.raises(NDSPContractRejected, match="NDSP_DUPLICATE_FIELD"):
        accepted(text.encode(), keys)


@pytest.mark.parametrize("mutation", ["additional", "missing"])
def test_additional_or_missing_fields_blocked(keys, mutation):
    doc = sample()
    if mutation == "additional":
        doc["protected_tdl_threshold"] = "not permitted"
    else:
        del doc["risk_class"]
    with pytest.raises(NDSPContractRejected, match="NDSP_FIELD_SET_INVALID"):
        accepted(signed(keys[0], doc), keys)


def test_empty_gigantic_and_malformed_documents_blocked(keys):
    for raw in (b"", b"{" + b" " * 17_000 + b"}"):
        with pytest.raises(NDSPContractRejected, match="NDSP_PAYLOAD_SIZE"):
            accepted(raw, keys)
    with pytest.raises(NDSPContractRejected, match="NDSP_MALFORMED_JSON"):
        accepted(b"not-json", keys)


def test_malformed_base64_and_signature_length_rejected(keys):
    doc = json.loads(signed(keys[0]))
    for bad in ("@@@", base64.b64encode(b"short").decode()):
        doc["signature"] = bad
        with pytest.raises(NDSPContractRejected, match="NDSP_SIGNATURE_INVALID"):
            accepted(json.dumps(doc).encode(), keys)


def test_unaware_host_clock_rejected_even_on_signed_message(keys):
    with pytest.raises(NDSPContractRejected, match="NDSP_CLOCK_NOT_UTC"):
        verify_synthetic_ndsp_contract(
            signed(keys[0]), public_keys=keys[1],
            now_utc=datetime(2026, 10, 14, 12, 0, 0),
        )


def test_valid_signature_does_not_expose_a_trade_api(keys):
    import nex_api.ndsp_contract_preview as module

    assert not any(name for name in ("submit_order", "execute", "place_trade")
                   if hasattr(module, name))
    result = accepted(signed(keys[0]), keys)
    assert result.execution_authorized is False
