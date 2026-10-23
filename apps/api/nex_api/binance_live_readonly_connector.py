"""Binance mainnet USD-M account binding: signed GET requests only.

Production credentials may authenticate but can never place orders through this module.
Only accepts a separately created, IP-restricted, read-only API key.
No credentials, response bodies, or balances are logged/returned to callers.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

FUTURES_ORIGIN = "https://fapi.binance.com"
WALLET_ORIGIN = "https://api.binance.com"
_KEY = re.compile(r"^[A-Za-z0-9_-]{10,256}$")


class LiveConnectivityError(RuntimeError):
    """Non-sensitive outcome code, never contains HTTP bodies or credentials."""


@dataclass(frozen=True)
class LiveAccountProbe:
    authenticated: bool
    read_only_permission_verified: bool
    ip_restricted: bool
    can_place_orders: bool = False
    mode: str = "BINANCE_USDM_MAINNET_READ_ONLY"


def _signed_url(origin: str, path: str, secret: str, timestamp_ms: int) -> str:
    query = urlencode({"timestamp": timestamp_ms, "recvWindow": 5000})
    signature = hmac.new(
        secret.encode("utf-8"), query.encode("ascii"), hashlib.sha256
    ).hexdigest()
    return f"{origin}{path}?{query}&signature={signature}"


async def _get_json(
    client: httpx.AsyncClient, url: str, api_key: str,
) -> dict:
    try:
        response = await client.get(url, headers={"X-MBX-APIKEY": api_key})
    except httpx.HTTPError:
        raise LiveConnectivityError("LIVE_NETWORK_UNAVAILABLE") from None
    if response.status_code in (401, 403):
        raise LiveConnectivityError("LIVE_AUTH_REJECTED")
    if response.status_code != 200:
        raise LiveConnectivityError("LIVE_ACCOUNT_CHECK_FAILED")
    try:
        result = response.json()
    except ValueError:
        raise LiveConnectivityError("LIVE_INVALID_RESPONSE") from None
    if not isinstance(result, dict):
        raise LiveConnectivityError("LIVE_INVALID_RESPONSE")
    return result


async def probe_live_readonly_account(
    api_key: str,
    api_secret: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout: float = 8.0,
    timestamp_ms: int | None = None,
) -> LiveAccountProbe:
    """Verify real Binance credentials without changing anything on Binance.

    Fail closed unless Binance confirms read-only, IP-restricted key permissions.
    An additional signed read-only USD-M account check verifies futures access.
    """
    if not _KEY.fullmatch(api_key) or not api_secret or len(api_secret) > 512:
        raise LiveConnectivityError("INVALID_LIVE_CREDENTIAL_FORMAT")
    if not 0 < timeout <= 30:
        raise LiveConnectivityError("INVALID_TIMEOUT")
    ts = int(time.time() * 1000) if timestamp_ms is None else timestamp_ms
    if ts <= 0:
        raise LiveConnectivityError("INVALID_TIMESTAMP")

    permissions_url = _signed_url(
        WALLET_ORIGIN, "/sapi/v1/account/apiRestrictions", api_secret, ts
    )
    futures_url = _signed_url(
        FUTURES_ORIGIN, "/fapi/v3/account", api_secret, ts
    )
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=False, transport=transport,
        trust_env=False,
    ) as client:
        permissions = await _get_json(client, permissions_url, api_key)
        # Require explicit positive proof; omitted or ambiguous permissions fail.
        forbidden = (
            "enableWithdrawals", "enableSpotAndMarginTrading", "enableFutures",
            "enableMargin", "enableInternalTransfer", "permitsUniversalTransfer",
            "enablePortfolioMarginTrading", "enableVanillaOptions",
            "enableFixApiTrade",
        )
        if permissions.get("enableReading") is not True:
            raise LiveConnectivityError("LIVE_READ_ACCESS_REQUIRED")
        if permissions.get("ipRestrict") is not True:
            raise LiveConnectivityError("LIVE_IP_ALLOWLIST_REQUIRED")
        if any(permissions.get(name) is not False for name in forbidden):
            raise LiveConnectivityError("LIVE_PRIVILEGED_KEY_REJECTED")
        account = await _get_json(client, futures_url, api_key)
    if not isinstance(account.get("assets"), list):
        raise LiveConnectivityError("LIVE_INVALID_RESPONSE")

    return LiveAccountProbe(
        authenticated=True, read_only_permission_verified=True, ip_restricted=True
    )
