"""Binance USD-M Testnet order-validation client.

Never submits live orders. Only /fapi/v1/order/test is allowed.
"""

import base64
import time
from urllib.parse import urlencode, quote

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)


class ExecutionBlocked(RuntimeError):
    pass


TESTNET_ORIGIN = "https://demo-fapi.binance.com"
TEST_ORDER_PATH = "/fapi/v1/order/test"


class Ed25519TestnetOrderValidator:
    def __init__(self, api_key, private_key, transport=None):
        if not isinstance(api_key, str) or not api_key:
            raise ExecutionBlocked("API_KEY_REQUIRED")

        if not isinstance(private_key, Ed25519PrivateKey):
            raise ExecutionBlocked("ED25519_KEY_REQUIRED")

        self.api_key = api_key
        self.private_key = private_key
        self.transport = transport

    def validate_order(
        self,
        *,
        symbol,
        side,
        quantity,
        client_order_id,
        risk_approved=False,
        market="testnet",
    ):
        if market != "testnet":
            raise ExecutionBlocked("MAINNET_ORDER_WRITES_NOT_RELEASED")

        if risk_approved is not True:
            raise ExecutionBlocked("RISK_APPROVAL_REQUIRED")

        if side not in ("BUY", "SELL"):
            raise ExecutionBlocked("INVALID_SIDE")

        if not isinstance(symbol, str) or not symbol.isalnum():
            raise ExecutionBlocked("INVALID_SYMBOL")

        if not isinstance(client_order_id, str) or not (
            1 <= len(client_order_id) <= 36
        ):
            raise ExecutionBlocked("INVALID_ORDER_ID")

        from decimal import Decimal, InvalidOperation

        try:
            qty = Decimal(str(quantity))
        except (InvalidOperation, ValueError, TypeError):
            raise ExecutionBlocked("INVALID_QUANTITY") from None

        if not qty.is_finite() or qty <= 0:
            raise ExecutionBlocked("INVALID_QUANTITY")

        fields = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": str(qty),
            "newClientOrderId": client_order_id,
            "recvWindow": 5000,
            "timestamp": int(time.time() * 1000),
        }

        query = urlencode(fields)
        signature = base64.b64encode(
            self.private_key.sign(query.encode("ascii"))
        ).decode("ascii")

        body = query + "&signature=" + quote(signature, safe="")

        try:
            with httpx.Client(
                timeout=8,
                transport=self.transport,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                response = client.post(
                    TESTNET_ORIGIN + TEST_ORDER_PATH,
                    content=body,
                    headers={
                        "X-MBX-APIKEY": self.api_key,
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
        except httpx.HTTPError:
            raise ExecutionBlocked(
                "TESTNET_VALIDATION_NETWORK_ERROR"
            ) from None

        if response.status_code != 200:
            raise ExecutionBlocked(
                "TESTNET_VALIDATION_REJECTED"
            )

        return {
            "validated": True,
            "order_submitted": False,
            "execution_enabled": False,
            "market": "testnet",
        }
