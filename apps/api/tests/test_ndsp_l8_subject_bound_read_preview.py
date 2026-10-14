"""M2-B L8: synthetic signed binding of session+9091 entitlement+source.

No real session/user, customer content, production IdP, gateway or orders.
Mocks are local; test EdDSA keys are generated and held in memory only.
"""
from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from nex_api.ndsp_canonical_read_gate_l7_preview import (
    CanonicalGateDenied, SyntheticCanonicalAuthorities,
)
from nex_api.ndsp_subject_bound_read_l8_preview import (
    SyntheticSubjectBindingAuthorities, _PROOF_AUDIENCE, _PROOF_ISSUER,
    _PROOF_VERSION, _sha, read_subject_bound_test_only,
)

NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)
SOURCE = "CD-TEST-L4-20261014"
SUBJECT = UUID("6ecde438-ffcf-4653-adea-e33dd7dd82a8")
ANOTHER = UUID("a7e5e877-dbc5-4417-a6dc-69dc129f8b3f")
TENANT = UUID("95680f3f-a749-4f1a-b8f5-f83e2f28a090")
ROOT = Path(__file__).parent / "fixtures" / "ndsp_l4_source_publisher"
RAW = (ROOT / "signed_decision_v2.json").read_bytes()


def fixture(
    *,
    changes: dict[str, object] | None = None,
    session_changes: dict[str, object] | None = None,
    entitlement_changes: dict[str, object] | None = None,
    owner_changes: dict[str, object] | None = None,
    attester_key_valid: bool = True,
    error_at: str = "",
    test_mode: bool = True,
) -> tuple[SyntheticSubjectBindingAuthorities, list[str]]:
    caller_session: dict[str, object] = {
        "ok": True, "user": {"id": str(SUBJECT), "status": "active"},
    }
    if session_changes:
        caller_session.update(session_changes)
    caller_entitlement: dict[str, object] = {
        "ok": True, "authority": "NDSP_CANONICAL_ENTITLEMENT_9091_V1",
        "entitlement": {
            "allowed": True, "asset_mode": "all_supported", "asset_slots": 0,
            "fixed_asset": None, "timeframes": ["4H"],
        },
    }
    if entitlement_changes:
        caller_entitlement.update(entitlement_changes)
    owner: dict[str, object] = {
        "source_decision_id": SOURCE, "owner_user_id": str(SUBJECT),
        "tenant_id": str(TENANT), "decision_state": "Published",
        "visibility": "public", "symbol": "BTCUSDT", "timeframe": "4H",
        "source_environment": "test",
    }
    if owner_changes:
        owner.update(owner_changes)
    trust = json.loads((ROOT / "trusted_test_public_key.json").read_text())
    public_keys = {
        trust["key_id"]: base64.b64decode(trust["public_key_base64"], validate=True),
    }
    private = Ed25519PrivateKey.generate()
    trusted_key = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    bad = Ed25519PrivateKey.generate()
    trace: list[str] = []

    async def session(credentials: str) -> dict[str, object]:
        trace.append("session")
        if error_at == "session":
            raise TimeoutError("unavailable")
        return caller_session

    async def entitlement(credentials: str) -> dict[str, object]:
        trace.append("entitlement")
        if error_at == "entitlement":
            raise TimeoutError("unavailable")
        return caller_entitlement

    async def attest(credentials: str, nonce: str) -> str:
        trace.append("attest")
        if error_at == "attest":
            raise TimeoutError("unavailable")
        issued = int(NOW.timestamp())
        claims: dict[str, object] = {
            "iss": _PROOF_ISSUER,
            "aud": _PROOF_AUDIENCE,
            "sub": str(SUBJECT),
            "iat": issued, "nbf": issued, "exp": issued + 20,
            "jti": "synthetic-jti-1234567890",
            "version": _PROOF_VERSION,
            "source_environment": "test",
            "session_authority": "canonical-auth-session-9020",
            "entitlement_authority": "canonical-entitlement-9091",
            "session_digest": _sha(caller_session),
            "entitlement_digest": _sha(caller_entitlement),
            "source_decision_id": SOURCE,
            "scope": "ndsp.source.read.synthetic",
            "request_nonce": nonce,
        }
        if changes:
            claims.update(changes)
        return jwt.encode(
            claims, private if attester_key_valid else bad, algorithm="EdDSA",
        )

    async def ownership(source_id: str) -> dict[str, object]:
        trace.append("owner")
        if error_at == "owner":
            raise TimeoutError("unavailable")
        return owner

    async def reader(tenant: UUID, source_id: str) -> bytes:
        trace.append("signed_source")
        if tenant != TENANT or source_id != SOURCE or error_at == "reader":
            raise LookupError("no-raw-customer-data")
        return RAW

    gate = SyntheticCanonicalAuthorities(
        session=session, entitlement=entitlement,
        ownership=ownership, sealed_reader=reader,
        source_test_public_keys=public_keys, synthetic_only=True,
    )
    return SyntheticSubjectBindingAuthorities(
        gate=gate, attest=attest, attester_public_key_pem=trusted_key,
        synthetic_only=test_mode,
    ), trace


def run(
    source: SyntheticSubjectBindingAuthorities, *,
    now: datetime = NOW, decision_id: str = SOURCE,
) -> object:
    return asyncio.run(read_subject_bound_test_only(
        credentials="test-only-opaque-credential",
        source_decision_id=decision_id,
        authorities=source, now_utc=now,
    ))


def test_valid_attestation_reuses_l7_verified_signed_source_only() -> None:
    source, trace = fixture()
    result = run(source)
    assert result.decision_version == 2
    assert result.document == RAW
    assert result.execution_authorized is False
    assert trace == ["session", "entitlement", "attest", "owner", "signed_source"]


@pytest.mark.parametrize(
    ("claim", "replacement", "expected"),
    [
        ("sub", str(ANOTHER), "L8_PROOF_SUBJECT_MISMATCH"),
        ("session_authority", "alternate-session-9001", "L8_SUBJECT_BOUND_AUTHORITY_MISMATCH"),
        ("entitlement_authority", "unverified-9091", "L8_SUBJECT_BOUND_AUTHORITY_MISMATCH"),
        ("session_digest", "sha256:" + "a" * 64, "L8_SUBJECT_BOUND_AUTHORITY_MISMATCH"),
        ("entitlement_digest", "sha256:" + "b" * 64, "L8_SUBJECT_BOUND_AUTHORITY_MISMATCH"),
        ("source_decision_id", "CD-TEST-UNOWNED-2", "L8_SUBJECT_BOUND_AUTHORITY_MISMATCH"),
        ("source_environment", "production", "L8_SUBJECT_BOUND_AUTHORITY_MISMATCH"),
        ("version", "forged", "L8_SUBJECT_BOUND_AUTHORITY_MISMATCH"),
        ("scope", "ndsp.source.trade", "L8_SUBJECT_BOUND_AUTHORITY_MISMATCH"),
        ("request_nonce", "replay-nonce", "L8_SUBJECT_BOUND_AUTHORITY_MISMATCH"),
        ("aud", "different-audience", "L8_BINDING_SIGNATURE_INVALID"),
        ("iss", "other-test-issuer", "L8_BINDING_SIGNATURE_INVALID"),
        ("iat", int(NOW.timestamp()) - 60, "L8_BINDING_EXPIRED_OR_FUTURE"),
        ("exp", int(NOW.timestamp()), "L8_BINDING_EXPIRED_OR_FUTURE"),
        ("exp", int(NOW.timestamp()) + 120, "L8_BINDING_EXPIRED_OR_FUTURE"),
        ("iat", int(NOW.timestamp()) + 15, "L8_BINDING_EXPIRED_OR_FUTURE"),
    ],
)
def test_wrong_subject_route_nonce_scope_or_expiration_denied_before_owner(
    claim: str, replacement: object, expected: str,
) -> None:
    authorities, trace = fixture(changes={claim: replacement})
    with pytest.raises(CanonicalGateDenied, match=expected):
        run(authorities)
    assert trace == ["session", "entitlement", "attest"]


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("invalid_test_attester_key", "L8_BINDING_SIGNATURE_INVALID"),
        ("extra_field", "L8_BINDING_FIELDS_INVALID"),
        ("inactive_session", "L8_SESSION_INACTIVE_OR_UNVERIFIED"),
        ("missing_status", "L8_SESSION_INACTIVE_OR_UNVERIFIED"),
        ("changed_subject", "L8_PROOF_SUBJECT_MISMATCH"),
        ("entitlement_authority", "L8_ENTITLEMENT_UNVERIFIED"),
    ],
)
def test_untrusted_authority_and_inactive_user_refused(
    case: str, expected: str,
) -> None:
    if case == "invalid_test_attester_key":
        authorities, trace = fixture(attester_key_valid=False)
    elif case == "extra_field":
        authorities, trace = fixture(changes={"extra": "customer-secret"})
    elif case == "inactive_session":
        authorities, trace = fixture(session_changes={
            "user": {"id": str(SUBJECT), "status": "suspended"},
        })
    elif case == "missing_status":
        authorities, trace = fixture(session_changes={
            "user": {"id": str(SUBJECT)},
        })
    elif case == "changed_subject":
        authorities, trace = fixture(session_changes={
            "user": {"id": str(ANOTHER), "status": "active"},
        })
    else:
        authorities, trace = fixture(entitlement_changes={"authority": "unknown"})
    with pytest.raises(CanonicalGateDenied, match=expected):
        run(authorities)
    assert trace == ["session", "entitlement", "attest"]


@pytest.mark.parametrize("service", ["session", "entitlement", "attest", "owner", "reader"])
def test_unavailable_authority_does_not_fail_open(service: str) -> None:
    authorities, trace = fixture(error_at=service)
    with pytest.raises(CanonicalGateDenied):
        run(authorities)
    assert trace[-1] == {
        "session": "session", "entitlement": "entitlement",
        "attest": "attest", "owner": "owner", "reader": "signed_source",
    }[service]


def test_owner_is_required_independent_of_valid_signed_authorities() -> None:
    authorities, trace = fixture(owner_changes={"owner_user_id": str(ANOTHER)})
    with pytest.raises(CanonicalGateDenied, match="L7_SOURCE_OWNER_MISMATCH"):
        run(authorities)
    assert trace == ["session", "entitlement", "attest", "owner"]


def test_unverified_real_production_context_denied_without_services() -> None:
    authorities, trace = fixture(test_mode=False)
    with pytest.raises(CanonicalGateDenied, match="L8_ONLY_SYNTHETIC_CONTEXT_ALLOWED"):
        run(authorities)
    assert not trace
    authorities, trace = fixture()
    with pytest.raises(CanonicalGateDenied, match="L8_ONLY_SYNTHETIC_CONTEXT_ALLOWED"):
        run(replace(authorities, gate=replace(authorities.gate, synthetic_only=False)))
    assert not trace


def test_module_contains_no_production_route_or_execution_surface() -> None:
    import nex_api.ndsp_subject_bound_read_l8_preview as module

    for forbidden in ("place_order", "submit_order", "create_app", "connect_real_ndsp"):
        assert not hasattr(module, forbidden)
