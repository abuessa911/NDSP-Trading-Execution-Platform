"""Detached signed contract tests. Synthetic keys, no account, broker or network."""
import base64
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from nex_api.future_contracts.ndsp_nex_decision_review_v1 import (
    canonical_payload_bytes, review_signed_decision,
)

NOW = datetime(2026, 11, 18, 19, 1, tzinfo=timezone.utc)
KEY = Ed25519PrivateKey.generate()
PUB = KEY.public_key().public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw,
)
TRUST = {"isolated-test-key": PUB}


def payload():
    return {
        "contract_version": "NDSP-NEX-1.0", "issuer": "NDSP", "audience": "NEX",
        "decision_id": "CD-0123456789ABCDEF1234",
        "asset_id": "BTCUSDT", "market": "CRYPTO", "timeframe": "1h",
        "analysis_mode": "investment", "state": "READY",
        "l15_state": "PASSED", "l15_blocked": False,
        "l16_state": "READY", "l16_allowed": True,
        "actual_layers_executed": 16, "evidence_sha256": "a" * 64,
        "source_revision": "b" * 40,
        "issued_at_utc": "2026-11-18T19:00:00Z",
        "expires_at_utc": "2026-11-18T19:03:00Z",
        "nonce": "synthetic-nonce-123456",
        "no_execution_authority": True, "not_recommendation": True,
    }


def envelope(p=None):
    p = p or payload()
    return {
        "key_id": "isolated-test-key", "payload": p,
        "signature_base64": base64.b64encode(KEY.sign(canonical_payload_bytes(p))).decode(),
    }


def review(e, *, asset="BTCUSDT", now=NOW, seen=()):
    return review_signed_decision(
        e, trusted_public_keys=TRUST,
        expected_asset_id=asset, seen_decision_ids=seen, now_utc=now,
    )


def check_rejected(reason, e):
    r = review(e)
    assert r["status"] == "REJECTED", r
    assert r["reason_code"] == reason, r
    assert r["new_entry_allowed"] is False
    assert r["broker_send_allowed"] is False
    assert r["modify_existing_positions"] is False
    assert r["execution_authority"] is False


def test_valid_ed25519_decision_is_study_only_even_when_ready():
    r = review(envelope())
    assert r["status"] == "CANDIDATE_STUDY_ONLY"
    assert r["signed_contract_valid"] is True
    assert r["new_entry_allowed"] is False
    assert r["broker_send_allowed"] is False
    assert r["modify_existing_positions"] is False
    assert r["runtime_integration_enabled"] is False


def test_monitoring_only_and_blocked_are_rejected_even_with_valid_signature():
    for state in ("MONITORING_ONLY", "BLOCKED_BY_DEVILS_ADVOCATE", "DATA_BLOCKED"):
        p = payload()
        p["state"] = state
        check_rejected("DECISION_MONITORING_OR_BLOCKED", envelope(p))


def test_l15_or_l16_hold_rejected():
    for field, value in (("l15_blocked", True), ("l16_allowed", False),
                         ("l15_state", "BLOCKED"), ("l16_state", "MONITORING_ONLY")):
        p = payload()
        p[field] = value
        check_rejected("DECISION_MONITORING_OR_BLOCKED", envelope(p))


def test_tampered_asset_breaks_signature():
    e = envelope()
    e["payload"]["asset_id"] = "ETHUSDT"
    check_rejected("SIGNATURE_INVALID", e)


def test_valid_signed_wrong_asset_is_denied():
    assert review(envelope(), asset="ETHUSDT")["reason_code"] == "ASSET_MISMATCH"


def test_expired_or_future_payload_denied():
    assert review(envelope(), now=datetime(2026, 11, 18, 20, tzinfo=timezone.utc))[
        "reason_code"] == "DECISION_STALE"
    p = payload()
    p["issued_at_utc"] = "2026-11-18T20:00:00Z"
    p["expires_at_utc"] = "2026-11-18T20:02:00Z"
    check_rejected("DECISION_FUTURE_DATED", envelope(p))


def test_replay_and_duplicate_nonce_guard():
    assert review(envelope(), seen=("CD-0123456789ABCDEF1234",))[
        "reason_code"] == "REPLAY_DETECTED"


def test_invalid_public_key_unknown_kid_and_signature():
    e = envelope()
    e["key_id"] = "untrusted"
    check_rejected("UNTRUSTED_SIGNER", e)
    e = envelope()
    e["signature_base64"] = "xxxx"
    check_rejected("SIGNATURE_LENGTH_INVALID", e)


def test_nonpositive_ttl_and_gt_5min_rejected():
    p = payload()
    p["expires_at_utc"] = p["issued_at_utc"]
    check_rejected("DECISION_CLOCK_INVALID", envelope(p))
    p = payload()
    p["expires_at_utc"] = "2026-11-18T19:06:00Z"
    check_rejected("DECISION_TTL_EXCESSIVE", envelope(p))


def test_fifteen_layers_and_execution_authority_rejected():
    p = payload()
    p["actual_layers_executed"] = 15
    check_rejected("LAYER_CHAIN_INCOMPLETE", envelope(p))
    p = payload()
    p["no_execution_authority"] = False
    check_rejected("EXECUTION_AUTHORITY_FORBIDDEN", envelope(p))


def test_missing_evidence_id_and_contract_version_rejected():
    p = payload()
    p["evidence_sha256"] = "fake"
    check_rejected("SOURCE_EVIDENCE_ID_INVALID", envelope(p))
    p = payload()
    p["contract_version"] = "NDSP-NEX-0.1"
    check_rejected("CONTRACT_IDENTITY_MISMATCH", envelope(p))


def test_unknown_extra_payload_field_rejected():
    p = payload()
    p["client_supplied_entitlement"] = True
    check_rejected("PAYLOAD_SCHEMA_MISMATCH", envelope(p))


def test_actual_m1_app_routes_match_openapi_without_any_order_endpoint():
    # Actual FastAPI handler registry, after importing the exactly recovered
    # secrets provider from independent review PR #22. Still not a live deploy.
    import json
    from pathlib import Path

    from nex_api.config import Settings
    from nex_api.main import create_app

    app = create_app(Settings(_env_file=None))
    actual_paths = set(app.openapi()["paths"])
    stored_contract = json.loads(
        Path("lib/api-spec/openapi.yaml").read_text(encoding="utf-8")
    )
    assert actual_paths == set(stored_contract["paths"])
    assert not any("/order" in path or "/trade" in path for path in actual_paths)
    assert "NDSP-NEX-1.0" not in str(actual_paths)
