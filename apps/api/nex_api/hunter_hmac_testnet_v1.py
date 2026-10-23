"""Isolated HMAC-SHA256 Binance USD-M Futures Testnet client.

Only signed account GET and order/test validation POST.
Real order creation, modification and cancellation are forbidden.
"""

import hashlib
import hmac
import time
from urllib.parse import urlencode

import httpx

ORIGIN = "https://demo-fapi.binance.com"

ALLOWED = {
    ("GET", "/fapi/v2/account"),
    ("POST", "/fapi/v1/order/test"),
}


class HMACError(RuntimeError):
    def __init__(self, reason, code=None):
        super().__init__(reason)
        self.code = code


class HMACTestnetClient:
    def __init__(self, api_key, secret, transport=None):
        if not isinstance(api_key, str) or not api_key:
            raise HMACError("API_KEY_REQUIRED")

        if not isinstance(secret, str) or not secret:
            raise HMACError("SECRET_REQUIRED")

        self.api_key = api_key
        self.secret = secret
        self.transport = transport

    def signed_request(self, method, path, params=None):
        if (method, path) not in ALLOWED:
            raise HMACError("ROUTE_FORBIDDEN")

        values = dict(params or {})

        if "timestamp" in values or "signature" in values:
            raise HMACError("RESERVED_PARAMETER")

        values["recvWindow"] = 5000
        values["timestamp"] = int(time.time() * 1000)

        query = urlencode(values)

        signature = hmac.new(
            self.secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        signed_query = query + "&signature=" + signature

        kwargs = {
            "headers": {
                "X-MBX-APIKEY": self.api_key,
            },
        }

        if method == "GET":
            kwargs["params"] = signed_query
        else:
            kwargs["content"] = signed_query
            kwargs["headers"]["Content-Type"] = (
                "application/x-www-form-urlencoded"
            )

        try:
            with httpx.Client(
                timeout=12,
                transport=self.transport,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                response = client.request(
                    method,
                    ORIGIN + path,
                    **kwargs,
                )
        except httpx.HTTPError:
            raise HMACError("NETWORK_ERROR") from None

        try:
            body = response.json()
        except ValueError:
            raise HMACError(
                "NON_JSON_RESPONSE",
                response.status_code,
            ) from None

        if response.status_code != 200:
            code = (
                body.get("code")
                if isinstance(body, dict)
                else None
            )
            raise HMACError(
                "BINANCE_REJECTED_HTTP_" +
                str(response.status_code),
                code,
            )

        return body

    def account(self):
        return self.signed_request(
            "GET",
            "/fapi/v2/account",
        )

    def validate_order(self, fields):
        """POST /order/test validates an order without creating it."""
        return self.signed_request(
            "POST",
            "/fapi/v1/order/test",
            fields,
        )
