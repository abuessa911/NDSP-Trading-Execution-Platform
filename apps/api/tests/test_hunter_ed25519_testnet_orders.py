from urllib.parse import parse_qs

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from nex_api.hunter_ed25519_testnet_orders import (
    Ed25519TestnetOrderValidator,
    ExecutionBlocked,
)


def inputs():
    return {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": "0.001",
        "client_order_id": "hunter-test-001",
        "risk_approved": True,
    }


def test_signed_testnet_validation_only():
    key = Ed25519PrivateKey.generate()
    observed = []

    def handler(request):
        observed.append(request)

        assert request.method == "POST"
        assert request.url.host == "demo-fapi.binance.com"
        assert request.url.path == "/fapi/v1/order/test"

        fields = parse_qs(request.content.decode())
        assert fields["newClientOrderId"] == ["hunter-test-001"]

        import base64
        from urllib.parse import urlencode

        pairs = [
            ("symbol", fields["symbol"][0]),
            ("side", fields["side"][0]),
            ("type", fields["type"][0]),
            ("quantity", fields["quantity"][0]),
            ("newClientOrderId", fields["newClientOrderId"][0]),
            ("recvWindow", fields["recvWindow"][0]),
            ("timestamp", fields["timestamp"][0]),
        ]

        key.public_key().verify(
            base64.b64decode(fields["signature"][0]),
            urlencode(pairs).encode("ascii"),
        )

        return httpx.Response(200, json={})

    validator = Ed25519TestnetOrderValidator(
        "test-api-key",
        key,
        transport=httpx.MockTransport(handler),
    )

    result = validator.validate_order(**inputs())

    assert result["validated"] is True
    assert result["order_submitted"] is False
    assert len(observed) == 1


def test_mainnet_blocked_before_network():
    key = Ed25519PrivateKey.generate()

    def forbidden(request):
        pytest.fail("Network must not be reached")

    validator = Ed25519TestnetOrderValidator(
        "test-api-key",
        key,
        transport=httpx.MockTransport(forbidden),
    )

    with pytest.raises(ExecutionBlocked, match="MAINNET"):
        validator.validate_order(
            **inputs(),
            market="mainnet",
        )


def test_risk_required_before_network():
    key = Ed25519PrivateKey.generate()

    def forbidden(request):
        pytest.fail("Network must not be reached")

    validator = Ed25519TestnetOrderValidator(
        "test-api-key",
        key,
        transport=httpx.MockTransport(forbidden),
    )

    args = inputs()
    args["risk_approved"] = False

    with pytest.raises(ExecutionBlocked, match="RISK"):
        validator.validate_order(**args)


def test_invalid_quantity_blocked():
    key = Ed25519PrivateKey.generate()

    validator = Ed25519TestnetOrderValidator(
        "test-api-key",
        key,
    )

    args = inputs()
    args["quantity"] = "-1"

    with pytest.raises(ExecutionBlocked, match="QUANTITY"):
        validator.validate_order(**args)


def test_invalid_side_blocked():
    key = Ed25519PrivateKey.generate()

    validator = Ed25519TestnetOrderValidator(
        "test-api-key",
        key,
    )

    args = inputs()
    args["side"] = "INVALID"

    with pytest.raises(ExecutionBlocked, match="SIDE"):
        validator.validate_order(**args)
