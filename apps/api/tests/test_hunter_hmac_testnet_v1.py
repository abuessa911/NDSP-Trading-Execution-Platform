import hashlib
import hmac
from urllib.parse import parse_qs, urlencode

import httpx
import pytest

from nex_api.hunter_hmac_testnet_v1 import (
    HMACTestnetClient,
    HMACError,
)


def test_signed_get_account():
    def handler(request):
        assert request.url.host == "demo-fapi.binance.com"
        assert request.url.path == "/fapi/v2/account"
        assert request.method == "GET"

        fields = parse_qs(request.url.query.decode())
        signature = fields.pop("signature")[0]

        query = urlencode(
            [(key, value[0]) for key, value in fields.items()]
        )

        expected = hmac.new(
            b"demo-secret",
            query.encode(),
            hashlib.sha256,
        ).hexdigest()

        assert hmac.compare_digest(signature, expected)

        return httpx.Response(
            200,
            json={"assets": []},
        )

    client = HMACTestnetClient(
        "demo-key",
        "demo-secret",
        transport=httpx.MockTransport(handler),
    )

    assert client.account() == {"assets": []}


def test_order_test_only():
    def handler(request):
        assert request.url.path == "/fapi/v1/order/test"
        assert request.method == "POST"
        return httpx.Response(200, json={})

    client = HMACTestnetClient(
        "demo-key",
        "demo-secret",
        transport=httpx.MockTransport(handler),
    )

    assert client.validate_order({
        "symbol": "DOGEUSDT",
        "side": "BUY",
        "type": "LIMIT",
        "timeInForce": "GTC",
        "quantity": "100",
        "price": "0.1",
    }) == {}


def test_real_order_route_forbidden():
    client = HMACTestnetClient(
        "demo-key",
        "demo-secret",
    )

    with pytest.raises(HMACError, match="ROUTE_FORBIDDEN"):
        client.signed_request(
            "POST",
            "/fapi/v1/order",
            {},
        )


def test_mainnet_unavailable():
    from nex_api import hunter_hmac_testnet_v1

    assert (
        hunter_hmac_testnet_v1.ORIGIN
        == "https://demo-fapi.binance.com"
    )


def test_reserved_parameters_blocked():
    client = HMACTestnetClient(
        "demo-key",
        "demo-secret",
    )

    with pytest.raises(
        HMACError,
        match="RESERVED_PARAMETER",
    ):
        client.signed_request(
            "GET",
            "/fapi/v2/account",
            {"signature": "invalid"},
        )
