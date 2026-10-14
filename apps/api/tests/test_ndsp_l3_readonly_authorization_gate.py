"""M2-B L3: hard rejection of real source data until approval.

No NDSP production service, key, user record, HTTP route or order is touched.
Every test fixture is synthetic and private keys are ephemeral in memory.
"""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from nex_api.ndsp_contract_preview import (
    NDSPContractRejected,
    verify_synthetic_ndsp_contract,
)
from nex_api.ndsp_source_binding_preview import verify_test_only_source_binding

FIXTURE = (Path(__file__).parent / "fixtures" / "ndsp_source_slice"
           / "signed_synthetic_decision.json")
NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)


def resign(overrides: dict[str, object]) -> tuple[bytes, dict[str, bytes]]:
    """Resign a synthetic document to distinguish policy rejection from tampering."""
    doc = json.loads(FIXTURE.read_text())
    assert isinstance(doc, dict)
    doc.update(overrides)
    doc.pop("signature")
    signer = Ed25519PrivateKey.generate()
    key_id = "ephemeral-l3-only"
    doc["key_id"] = key_id
    canonical = json.dumps(
        doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    doc["signature"] = base64.b64encode(signer.sign(canonical)).decode("ascii")
    public_key = signer.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return json.dumps(doc).encode(), {key_id: public_key}


def test_re_signed_production_source_still_rejected() -> None:
    raw, keys = resign({"source_environment": "production"})
    with pytest.raises(NDSPContractRejected, match="NDSP_SOURCE_NOT_APPROVED"):
        verify_synthetic_ndsp_contract(raw, public_keys=keys, now_utc=NOW)


def test_published_signed_source_never_authorizes_orders() -> None:
    raw, keys = resign({})
    verified = verify_synthetic_ndsp_contract(raw, public_keys=keys, now_utc=NOW)
    assert verified.execution_authorized is False
    assert verified.decision_state == "BLOCKED"
    assert verified.direction == "FLAT"


@pytest.mark.parametrize("extra", ["tenant_id", "source_decision_id", "tdl_formula"])
def test_extra_tenant_or_protected_payload_rejected(extra: str) -> None:
    raw, keys = resign({extra: "test-only-untrusted-metadata"})
    with pytest.raises(NDSPContractRejected, match="NDSP_FIELD_SET_INVALID"):
        verify_synthetic_ndsp_contract(raw, public_keys=keys, now_utc=NOW)


def test_unapproved_version_not_invented_from_updated_at() -> None:
    raw, keys = resign({"decision_version": None})
    with pytest.raises(NDSPContractRejected, match="NDSP_DECISION_VERSION_INVALID"):
        verify_synthetic_ndsp_contract(raw, public_keys=keys, now_utc=NOW)


def test_source_binding_requires_explicit_version_and_publication() -> None:
    raw, keys = resign({})
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
    source.pop("version")
    with pytest.raises(NDSPContractRejected, match="NDSP_SOURCE_FIELD_SET_INVALID"):
        verify_test_only_source_binding(
            raw, public_keys=keys, source=source, now_utc=NOW,
        )


def test_all_test_only_modules_have_no_real_http_or_order_adapter() -> None:
    from nex_api import (
        ndsp_contract_preview,
        ndsp_identity_ledger_l2_preview,
        ndsp_source_binding_preview,
    )

    for module in (
        ndsp_contract_preview,
        ndsp_identity_ledger_l2_preview,
        ndsp_source_binding_preview,
    ):
        for forbidden in ("place_order", "submit_order", "fetch_real_ndsp_decision"):
            assert not hasattr(module, forbidden)
