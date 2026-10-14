"""M2-B L7 NDSP canonical auth/entitlement/ownership gateway simulation.

All dependencies are test-only and injected in memory; no real NDSP
sessions, customer identities, HTTP, trading or database calls.
"""
from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest

from nex_api.ndsp_canonical_read_gate_l7_preview import (
    CanonicalGateDenied,
    TestCanonicalAuthorities,
    read_only_test_decision,
)

NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)
ROOT = Path(__file__).parent / "fixtures" / "ndsp_l4_source_publisher"
SOURCE_ID = "CD-TEST-L4-20261014"
SUBJECT = UUID("354fb5d9-ed8c-42a7-b397-01febeaeb8f6")
OTHER_SUBJECT = UUID("8d3a36a0-cb13-4c07-a7d5-bcd7e0f7e8ec")
TENANT = UUID("a6ecf885-0adc-4453-b292-158598db215f")
OTHER_TENANT = UUID("7c4f1ef5-81b1-4d1e-8f04-99f2a2811d3d")


def _source_raw(version: int = 2) -> bytes:
    return (ROOT / f"signed_decision_v{version}.json").read_bytes()


def _trust_keys() -> dict[str, bytes]:
    t = json.loads((ROOT / "trusted_test_public_key.json").read_text())
    assert t["private_key_persisted"] is False
    return {
        t["key_id"]: base64.b64decode(t["public_key_base64"], validate=True),
    }


def _services(
    *, session: dict[str, object] | None = None,
    ent: dict[str, object] | None = None,
    owner: dict[str, object] | None = None,
    signed: bytes | None = None,
    errors: frozenset[str] = frozenset(),
) -> tuple[TestCanonicalAuthorities, list[str]]:
    calls: list[str] = []
    session_data = session if session is not None else {
        "ok": True, "user": {"id": str(SUBJECT)},
    }
    entitlement = ent if ent is not None else {
        "ok": True,
        "authority": "NDSP_CANONICAL_ENTITLEMENT_9091_V1",
        "commercial_plan": "elite",
        "entitlement": {
            "allowed": True, "asset_mode": "all_supported",
            "timeframes": ["4h"], "fixed_asset": None, "asset_slots": 0,
        },
    }
    ownership = owner if owner is not None else {
        "source_decision_id": SOURCE_ID,
        "owner_user_id": str(SUBJECT),
        "tenant_id": str(TENANT),
        "decision_state": "Published",
        "visibility": "public",
        "symbol": "BTCUSDT", "timeframe": "4H",
        "source_environment": "test",
    }
    raw = signed if signed is not None else _source_raw()

    async def session_authority(credentials: str) -> dict[str, object]:
        calls.append("session:" + credentials)
        if "session" in errors:
            raise TimeoutError("test")
        return session_data

    async def ent_authority(credentials: str) -> dict[str, object]:
        calls.append("entitlement:" + credentials)
        if "entitlement" in errors:
            raise TimeoutError("test")
        return entitlement

    async def owner_authority(source_id: str) -> dict[str, object]:
        calls.append("ownership:" + source_id)
        if "ownership" in errors:
            raise TimeoutError("test")
        return ownership

    async def signed_reader(tenant_id: UUID, source_id: str) -> bytes:
        calls.append("sealed_reader")
        if tenant_id != TENANT or source_id != SOURCE_ID or "reader" in errors:
            raise LookupError("test")
        return raw

    return TestCanonicalAuthorities(
        session=session_authority,
        entitlement=ent_authority,
        ownership=owner_authority,
        sealed_reader=signed_reader,
        source_test_public_keys=_trust_keys(),
    ), calls


def _run(services: TestCanonicalAuthorities, now: datetime = NOW):
    return asyncio.run(read_only_test_decision(
        credentials="synthetic-session-fixture", source_decision_id=SOURCE_ID,
        authorities=services, now_utc=now,
    ))


def test_source_signed_fixture_valid_but_order_execution_never_authorized() -> None:
    services, called = _services()
    result = _run(services)
    assert result.document == _source_raw()
    assert result.source_decision_id == SOURCE_ID
    assert result.tenant_id == TENANT
    assert result.decision_version == 2
    assert result.execution_authorized is False
    assert called == [
        "session:synthetic-session-fixture",
        "entitlement:synthetic-session-fixture",
        "ownership:" + SOURCE_ID,
        "sealed_reader",
    ]


def test_older_signed_version_is_read_only_and_not_an_order() -> None:
    services, _ = _services(signed=_source_raw(1))
    result = _run(services)
    assert result.decision_version == 1
    assert result.execution_authorized is False


@pytest.mark.parametrize(
    ("kind", "code", "last_step"),
    [
        ("no_session", "L7_AUTH_REQUIRED", 1),
        ("email_only", "L7_AUTH_SUBJECT_UNVERIFIED", 1),
        ("subject_malformed", "L7_AUTH_SUBJECT_UNVERIFIED", 1),
        ("wrong_entitlement_authority", "L7_ENTITLEMENT_AUTHORITY_UNVERIFIED", 2),
        ("entitlement_denied", "L7_ENTITLEMENT_NOT_ALLOWED", 2),
        ("missing_owner", "L7_OWNER_PROVENANCE_UNAVAILABLE", 3),
        ("other_owner", "L7_SOURCE_OWNER_MISMATCH", 3),
        ("private_source", "L7_SOURCE_NOT_PUBLIC_OR_UNTRUSTED", 3),
        ("completed_only", "L7_SOURCE_NOT_PUBLIC_OR_UNTRUSTED", 3),
        ("real_environment", "L7_SOURCE_NOT_PUBLIC_OR_UNTRUSTED", 3),
        ("wrong_timeframe", "L7_TIMEFRAME_NOT_ENTITLED", 3),
        ("wrong_asset", "L7_ASSET_NOT_ENTITLED", 3),
        ("unverified_assignments", "L7_ASSET_ASSIGNMENT_AUTHORITY_MISSING", 3),
        ("wrong_source_symbol", "L7_SIGNED_SOURCE_CONTEXT_MISMATCH", 4),
        ("tampered_signed_payload", "L7_SIGNATURE_OR_CONTRACT_REJECTED", 4),
        ("untrusted_signer", "L7_SIGNATURE_OR_CONTRACT_REJECTED", 4),
    ],
)
def test_rejects_untrusted_or_unauthorized_data_before_disclosure(
    kind: str, code: str, last_step: int,
) -> None:
    session = {"ok": True, "user": {"id": str(SUBJECT)}}
    ent = {
        "ok": True,
        "authority": "NDSP_CANONICAL_ENTITLEMENT_9091_V1",
        "entitlement": {
            "allowed": True, "asset_mode": "all_supported", "fixed_asset": None,
            "asset_slots": 0, "timeframes": ["4H"],
        },
    }
    owner = {
        "source_decision_id": SOURCE_ID,
        "owner_user_id": str(SUBJECT),
        "tenant_id": str(TENANT),
        "decision_state": "Published", "visibility": "public",
        "symbol": "BTCUSDT", "timeframe": "4H",
        "source_environment": "test",
    }
    raw = _source_raw()
    if kind == "no_session":
        session["ok"] = False
    elif kind == "email_only":
        session["user"] = {"email": "sandbox@example.invalid"}
    elif kind == "subject_malformed":
        session["user"] = {"id": "forged"}
    elif kind == "wrong_entitlement_authority":
        ent["authority"] = "header-borrowed-authority"
    elif kind == "entitlement_denied":
        ent["entitlement"]["allowed"] = False
    elif kind == "missing_owner":
        owner.pop("owner_user_id")
    elif kind == "other_owner":
        owner["owner_user_id"] = str(OTHER_SUBJECT)
    elif kind == "private_source":
        owner["visibility"] = "private"
    elif kind == "completed_only":
        owner["decision_state"] = "Completed"
    elif kind == "real_environment":
        owner["source_environment"] = "production"
    elif kind == "wrong_timeframe":
        ent["entitlement"]["timeframes"] = ["15m"]
    elif kind == "wrong_asset":
        ent["entitlement"].update({
            "asset_mode": "fixed", "fixed_asset": "ETH",
        })
    elif kind == "unverified_assignments":
        ent["entitlement"].update({
            "asset_mode": "selected", "asset_slots": 2,
        })
    elif kind == "wrong_source_symbol":
        owner["symbol"] = "ETHUSDT"
    elif kind == "tampered_signed_payload":
        obj = json.loads(raw)
        obj["asset"] = "ETHUSDT"
        raw = json.dumps(obj).encode()
    services, called = _services(
        session=session, ent=ent, owner=owner, signed=raw,
    )
    if kind == "untrusted_signer":
        services = replace(services, source_test_public_keys={})
    with pytest.raises(CanonicalGateDenied, match=code):
        _run(services)
    assert len(called) == last_step


@pytest.mark.parametrize(
    ("service_name", "code", "count"),
    [
        ("session", "L7_SESSION_AUTHORITY_UNAVAILABLE", 1),
        ("entitlement", "L7_ENTITLEMENT_AUTHORITY_UNAVAILABLE", 2),
        ("ownership", "L7_OWNER_AUTHORITY_UNAVAILABLE", 3),
        ("reader", "L7_SIGNED_SOURCE_UNAVAILABLE", 4),
    ],
)
def test_unavailable_authority_fails_closed(
    service_name: str, code: str, count: int,
) -> None:
    services, called = _services(errors=frozenset({service_name}))
    with pytest.raises(CanonicalGateDenied, match=code):
        _run(services)
    assert len(called) == count


def test_expiry_fail_closed() -> None:
    services, _ = _services()
    with pytest.raises(CanonicalGateDenied, match="L7_SIGNATURE_OR_CONTRACT_REJECTED"):
        _run(services, datetime(2026, 10, 15, 10, tzinfo=timezone.utc))


def test_unapproved_real_source_or_invalid_credentials_block_before_auth() -> None:
    services, calls = _services()
    with pytest.raises(CanonicalGateDenied, match="L7_TEST_CONTEXT_REQUIRED"):
        _run(replace(services, synthetic_only=False))
    assert not calls
    with pytest.raises(CanonicalGateDenied, match="L7_TEST_CONTEXT_REQUIRED"):
        asyncio.run(read_only_test_decision(
            credentials="", source_decision_id=SOURCE_ID,
            authorities=services, now_utc=NOW,
        ))
    assert not calls


def test_no_api_runtime_import_or_execution_surface() -> None:
    import nex_api.ndsp_canonical_read_gate_l7_preview as module

    for name in ("create_app", "place_order", "submit_order", "fetch_real_ndsp"):
        assert not hasattr(module, name)
