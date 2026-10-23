"""Isolated Binance USD-M Futures testnet connectivity checker.

No live exchange origin, order route, withdrawal, key persistence or background worker.
Call explicitly from trusted server-side code; do not mount as a public API.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

TESTNET_ORIGIN = "https://demo-fapi.binance.com"
_KEY = re.compile(r"^[A-Za-z0-9_-]{10,256}$")


class ExchangeConnectivityError(RuntimeError):
    """Sanitized connectivity error; never includes credentials or response bodies."""


@dataclass(frozen=True)
class AccountProbe:
    reachable: bool
    authenticated: bool
    mode: str = "USD_M_FUTURES_TESTNET"
    can_place_orders: bool = False


def _sign(secret: str, query: str) -> str:
    return hmac.new(secret.encode("utf-8"), query.encode("ascii"), hashlib.sha256).hexdigest()


async def probe_testnet_account(
    api_key: str,
    api_secret: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout: float = 8.0,
    timestamp_ms: int | None = None,
) -> AccountProbe:
    """Perform a signed, read-only account query against the *testnet* host.

    Requires testnet-only credentials supplied in server memory. No logging of
    secrets, HTTP response bodies, or account balances.
    """
    if not _KEY.fullmatch(api_key) or not api_secret or len(api_secret) > 512:
        raise ExchangeConnectivityError("INVALID_TESTNET_CREDENTIAL_FORMAT")
    if timeout <= 0 or timeout > 30:
        raise ExchangeConnectivityError("INVALID_TIMEOUT")
    ts = int(time.time() * 1000) if timestamp_ms is None else timestamp_ms
    if ts <= 0:
        raise ExchangeConnectivityError("INVALID_TIMESTAMP")
    query = urlencode({"timestamp": ts, "recvWindow": 5000})
    signature = _sign(api_secret, query)
    url = f"{TESTNET_ORIGIN}/fapi/v2/account?{query}&signature={signature}"
    try:
        async with httpx.AsyncClient(
            timeout=timeout, follow_redirects=False, transport=transport,
            trust_env=False,
        ) as client:
            response = await client.get(url, headers={"X-MBX-APIKEY": api_key})
    except httpx.HTTPError as exc:
        raise ExchangeConnectivityError("TESTNET_NETWORK_UNAVAILABLE") from None
    if response.status_code in (401, 403):
        raise ExchangeConnectivityError("TESTNET_AUTH_REJECTED")
    if response.status_code != 200:
        raise ExchangeConnectivityError("TESTNET_ACCOUNT_CHECK_FAILED")
    try:
        payload = response.json()
    except ValueError:
        raise ExchangeConnectivityError("TESTNET_INVALID_RESPONSE") from None
    if not isinstance(payload, dict) or "assets" not in payload:
        raise ExchangeConnectivityError("TESTNET_INVALID_RESPONSE")
    return AccountProbe(reachable=True, authenticated=True)
