"""Isolated Binance Ed25519 read-only connector. Never submits orders."""

import base64
import time
from pathlib import Path
from urllib.parse import quote, urlencode

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ENDPOINTS = {
    "permissions": (
        "https://api.binance.com",
        "/sapi/v1/account/apiRestrictions",
    ),
    "spot": (
        "https://api.binance.com",
        "/api/v3/account",
    ),
    "futures": (
        "https://fapi.binance.com",
        "/fapi/v3/account",
    ),
}


class BinanceReadError(RuntimeError):
    pass


class BinanceEd25519ReadOnly:
    def __init__(self, api_key, pem_path, transport=None):
        if not api_key or not api_key.strip():
            raise BinanceReadError("MISSING_API_KEY")

        path = Path(pem_path)
        mode = path.stat().st_mode & 0o777
        if mode not in (0o400, 0o440, 0o600):
            raise BinanceReadError("UNSAFE_KEY_PERMISSIONS")

        key = serialization.load_pem_private_key(
            path.read_bytes(), password=None
        )
        if not isinstance(key, Ed25519PrivateKey):
            raise BinanceReadError("NOT_ED25519")

        self._key = key
        self._api_key = api_key.strip()
        self._transport = transport

    def read(self, market):
        if market not in ENDPOINTS:
            raise BinanceReadError("ENDPOINT_NOT_ALLOWED")

        origin, path = ENDPOINTS[market]
        query = urlencode({
            "timestamp": int(time.time() * 1000),
            "recvWindow": 5000,
        })

        signature = base64.b64encode(
            self._key.sign(query.encode("ascii"))
        ).decode("ascii")

        url = (
            origin + path + "?" + query
            + "&signature=" + quote(signature, safe="")
        )

        try:
            with httpx.Client(
                timeout=10,
                transport=self._transport,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                response = client.get(
                    url,
                    headers={"X-MBX-APIKEY": self._api_key},
                )
        except httpx.HTTPError:
            raise BinanceReadError("NETWORK_ERROR") from None

        if response.status_code != 200:
            raise BinanceReadError(
                f"BINANCE_HTTP_{response.status_code}"
            )

        try:
            data = response.json()
        except ValueError:
            raise BinanceReadError("INVALID_JSON") from None

        if not isinstance(data, dict):
            raise BinanceReadError("INVALID_RESPONSE")

        return data
