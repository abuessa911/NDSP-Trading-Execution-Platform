import asyncio
from types import SimpleNamespace

import httpx
import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from nex_api import hunter_testnet_cycle_v1 as mod
from nex_api.hunter_execution_safety_v1 import (
    RiskSnapshot,
    SafetyHalt,
)


def risk():
    return RiskSnapshot(
        opening_equity="100",
        current_equity="95",
        daily_limit_pct="10",
        account_verified=True,
        utc_day="2026-10-19",
    )


def make_info():
    return {
        "symbols": [{
            "symbol": "DOGEUSDT",
            "status": "TRADING",
            "contractType": "PERPETUAL",
            "quoteAsset": "USDT",
            "filters": [
                {
                    "filterType": "LOT_SIZE",
                    "minQty": "1",
                    "maxQty": "100000",
                    "stepSize": "1",
                },
                {
                    "filterType": "PRICE_FILTER",
                    "minPrice": "0.001",
                    "maxPrice": "100",
                    "tickSize": "0.001",
                },
                {
                    "filterType": "MIN_NOTIONAL",
                    "notional": "5",
                },
            ],
        }],
    }


def setup(tmp_path, monkeypatch, *, timeout=False):
    async def fake_risk(request, user):
        return risk()

    monkeypatch.setattr(
        mod, "build_verified_snapshot", fake_risk
    )

    requests = []
    status = {"value": "NEW"}

    def handler(request):
        requests.append(
            (request.method, request.url.path)
        )

        assert request.url.host == (
            "demo-fapi.binance.com"
        )

        path = request.url.path

        if path.endswith("/exchangeInfo"):
            return httpx.Response(
                200, json=make_info()
            )

        if path.endswith("/premiumIndex"):
            return httpx.Response(
                200,
                json={
                    "symbol": "DOGEUSDT",
                    "markPrice": "0.100",
                },
            )

        if path == "/fapi/v1/order":
            if request.method == "POST":
                if timeout:
                    raise httpx.ReadTimeout(
                        "simulated interruption"
                    )
                return httpx.Response(
                    200,
                    json={"status": "NEW"},
                )

            if request.method == "DELETE":
                status["value"] = "CANCELED"
                return httpx.Response(
                    200,
                    json={"status": "CANCELED"},
                )

            if request.method == "GET":
                return httpx.Response(
                    200,
                    json={
                        "status": status["value"]
                    },
                )

        return httpx.Response(404)

    client = mod.TestnetClient(
        "testnet-fake-api-key",
        Ed25519PrivateKey.generate(),
        transport=httpx.MockTransport(handler),
        approved=True,
    )

    ledger = mod.TestnetLedger(
        tmp_path / "orders.db"
    )

    return client, ledger, requests


def run(client, ledger):
    return asyncio.run(
        mod.guarded_testnet_cycle(
            request=object(),
            user=object(),
            client=client,
            ledger=ledger,
            symbol="DOGEUSDT",
            side="BUY",
            quantity="100",
            price="0.098",
            client_id="hunter-testnet-001",
            max_notional="20",
        )
    )


def test_order_create_query_cancel(
    tmp_path, monkeypatch
):
    client, ledger, requests = setup(
        tmp_path, monkeypatch
    )

    result = run(client, ledger)

    assert result["final_status"] == "CANCELED"
    assert ledger.state(
        "hunter-testnet-001"
    ) == "CANCELED"

    assert (
        "POST", "/fapi/v1/order"
    ) in requests

    assert (
        "DELETE", "/fapi/v1/order"
    ) in requests


def test_duplicate_never_resubmits(
    tmp_path, monkeypatch
):
    client, ledger, requests = setup(
        tmp_path, monkeypatch
    )

    run(client, ledger)

    original_post_count = requests.count(
        ("POST", "/fapi/v1/order")
    )

    with pytest.raises(
        SafetyHalt,
        match="DUPLICATE_ORDER_BLOCKED",
    ):
        run(client, mod.TestnetLedger(
            tmp_path / "orders.db"
        ))

    assert requests.count(
        ("POST", "/fapi/v1/order")
    ) == original_post_count


def test_timeout_keeps_order_reserved(
    tmp_path, monkeypatch
):
    client, ledger, requests = setup(
        tmp_path, monkeypatch, timeout=True
    )

    with pytest.raises(
        SafetyHalt,
        match="EXCHANGE_RESPONSE_UNKNOWN",
    ):
        run(client, ledger)

    assert ledger.state(
        "hunter-testnet-001"
    ) == "SUBMISSION_UNKNOWN"

    with pytest.raises(
        SafetyHalt,
        match="DUPLICATE_ORDER_BLOCKED",
    ):
        run(client, ledger)


def test_risk_limit_blocks_network(
    tmp_path, monkeypatch
):
    client, ledger, requests = setup(
        tmp_path, monkeypatch
    )

    async def failed_risk(request, user):
        return RiskSnapshot(
            opening_equity="100",
            current_equity="90",
            daily_limit_pct="10",
            account_verified=True,
            utc_day="2026-10-19",
        )

    monkeypatch.setattr(
        mod, "build_verified_snapshot", failed_risk
    )

    with pytest.raises(
        SafetyHalt,
        match="DAILY_LOSS_LIMIT_REACHED",
    ):
        run(client, ledger)

    assert requests == []


def test_exchange_filters_block_bad_step():
    filters = {
        "LOT_SIZE": {
            "minQty": "1",
            "maxQty": "1000",
            "stepSize": "1",
        },
        "PRICE_FILTER": {
            "minPrice": "0.001",
            "maxPrice": "100",
            "tickSize": "0.001",
        },
    }

    with pytest.raises(
        SafetyHalt,
        match="QUANTITY_STEP_INVALID",
    ):
        mod.validate_limit_order(
            filters,
            quantity="1.5",
            price="0.098",
            mark_price="0.100",
            max_notional="20",
        )


def test_mainnet_route_is_forbidden():
    assert mod.ORIGIN == (
        "https://demo-fapi.binance.com"
    )

    assert (
        "POST", "/fapi/v1/order/test"
    ) not in mod.SIGNED_PATHS

    with pytest.raises(
        SafetyHalt,
        match="TESTNET_ORDER_APPROVAL_REQUIRED",
    ):
        mod.TestnetClient(
            "fake",
            Ed25519PrivateKey.generate(),
            approved=False,
        )
