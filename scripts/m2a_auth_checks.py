"""Real disposable Keycloak/PostgreSQL/Redis M2-A boundary acceptance.

The quota is pre-exhausted before exercising the read route, so tests cannot
send a real Binance request. Nothing here provides a token or auth override.
"""
from __future__ import annotations

from urllib.parse import urlencode

from redis.asyncio import Redis

from m1_auth_browser import isolated_async
from m1_auth_environment import ORIGIN

ROOT = ORIGIN + "/api/v1/admin/market-data"
QUERY = {
    "market": "spot", "symbol": "BTCUSDT", "interval": "5m",
}
FUTURES = {
    "market": "usdm_futures", "symbol": "BTCUSDT", "interval": "15m",
}


def url(path: str, query: dict[str, str]) -> str:
    return ROOT + path + "?" + urlencode(query)


def real_admin_checks(fixture, http, headers, tenant_id, role, check):
    """Use signed/real-MFA browser session on real API and Redis, never trade."""
    before = http.get(url("/observation", QUERY), headers=headers)
    check("M2A real Redis NOT_OBSERVED for freshly provisioned " + role,
          before.status_code == 200
          and before.json()["status"] == "NOT_OBSERVED")

    async def seed():
        redis = Redis.from_url(fixture.env["REDIS_URL"])
        try:
            key = f"nex:m2a:quota:tenant:{tenant_id}:spot"
            await redis.set(key, "6", ex=60)
            future_key = f"nex:m2a:quota:tenant:{tenant_id}:usdm_futures"
            await redis.set(future_key, "6", ex=60)
            # Synthetic observation is metadata only, never OHLCV or trade data.
            observation_key = f"nex:m2a:market:{tenant_id}:spot:BTCUSDT:5m"
            await redis.set(observation_key, "BLOCKED:EXCHANGE_RATE_LIMITED", ex=90)
        finally:
            await redis.aclose()

    isolated_async(seed())
    spot = http.get(url("/closed-candles", QUERY | {"limit": "5"}), headers=headers)
    futures = http.get(url("/closed-candles", FUTURES | {"limit": "5"}), headers=headers)
    check("M2A genuine " + role + " MFA reaches Redis quota denial before Binance",
          spot.status_code == 429 and futures.status_code == 429
          and spot.json()["reason_code"] == "M2A_RATE_BUDGET_EXHAUSTED"
          and futures.json()["reason_code"] == "M2A_RATE_BUDGET_EXHAUSTED")
    observed = http.get(url("/observation", QUERY), headers=headers)
    check("M2A real Redis tenant-bound last failed observation for " + role,
          observed.status_code == 200 and observed.json()["status"] == "BLOCKED"
          and observed.json()["reason_code"] == "EXCHANGE_RATE_LIMITED")
    reject = http.get(url("/closed-candles", QUERY | {"limit": "31"}), headers=headers)
    check("M2A genuine " + role + " MFA still rejects invalid limit",
          reject.status_code == 422)
    not_allowed = http.post(url("/closed-candles", QUERY), headers=headers)
    check("M2A API remains GET-only for genuine " + role + " session",
          not_allowed.status_code == 405)


def real_lower_role_checks(http, headers, role, check):
    for path in ("/observation", "/closed-candles"):
        query = QUERY if path == "/observation" else QUERY | {"limit": "5"}
        response = http.get(url(path, query), headers=headers)
        check("M2A actual " + role + " login denied admin " + path,
              response.status_code == 403
              and response.json()["reason_code"] == "ROLE_NOT_ALLOWED")
