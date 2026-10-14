# M2-A — Internal NEX market-data integration (security-gated trial)

**Review-only. NOT deployed. M1 is not production-accepted. No trades, account API
keys, NDSP calls, background polling, or production feature activation.**

This extends the separate public Binance closed-candle adapter. NEX gets an
authenticated **administrator/MFA-only** experimental read API, intentionally
hidden from public OpenAPI. End-user API access, alerts, persistency, and an
always-on feed remain unimplemented until later acceptance gates.

## Switch and authorization

- `M2A_PUBLIC_MARKET_ENABLED=false` by default. Enabling it is rejected unless
  `ENVIRONMENT=test`; `development` and `production` both fail configuration
  validation. Never set this flag on NDSP or NEX production.
- All M2-A routes reuse `get_administrator`: active OIDC/session, active
  tenant, server-side ADMIN/SUPER_ADMIN role and genuine administrator MFA.
  Browser and bearer identities retain M1 validation and revocation rules.
- `GET /api/v1/admin/market-data/closed-candles?market=spot&symbol=BTCUSDT&interval=5m&limit=5`
  accepts only Spot or USDⓈ-M Futures, 5m/15m and limit 2–30. A permitted
  request fetches only Binance public `GET time` and `GET klines`; no
  account/trade endpoints or any other host.
- `GET /api/v1/admin/market-data/observation` with the same market/symbol/
  interval reports the **last attempt**, not a continuously monitored feed.
  `NOT_OBSERVED`, `READ_ONLY_OK` (source time and last closed bar),
  `BLOCKED` (sanitized reason code), or fail-closed 503 for unavailable
  monitoring. Observation is scoped to the authenticated tenant and expires
  after 15 minutes; no candle history is retained.

## Rate budgets and safety

- Redis atomically reserves capacity from **both** shared market-global and
  per-tenant limits with a Lua script. Each market permits at most **30 requests
  per 60-second window globally**, of which a tenant may use at most **6**.
  The two upstream GETs on a successful request count as one budget unit.
- Failed quota checks return 429 without touching Binance. Missing Redis,
  quota evaluation error, monitoring-write error, stale/open/gapped candles,
  malformed payload, upstream timeout, 418/429 or network restriction return
  sanitized fail-closed responses; **never substitute zero, old or sample data**.
- Counts are conservative experimental safety throttles, **not** a proof of
  Binance weight allocation. Exchange request-weight and IP-based limits,
  symbols' trading status and redistribution rights need separate review.
- The existing M1 audit middleware records control requests, deny/failure
  outcomes and a correlation id, without logging market query strings or
  credentials. No logging of upstream Binance response bodies.
- Local validation/test doubles only; real Binance smoke from the standalone
  reader is a different gate. NEX test environment must have genuinely
  provisioned admin MFA, PostgreSQL, an audit sink and Redis.

## Verified offline commands

```sh
uv run --frozen ruff check apps/api scripts/ci-m1-compose.py \
  scripts/verify-m1-compose.py scripts/tests scripts/m2a_binance_closed_candles.py
uv run --frozen mypy apps/api/nex_api
uv run --frozen python scripts/export-m1-openapi.py --check
uv run --frozen pytest -q apps/api/tests scripts/tests
```

## Still open

1. Production-specific M1 OIDC administrator MFA and operational/security
   sign-off; four hosted CI jobs alone are not final M1 certification.
2. Real isolated Keycloak+PostgreSQL+Redis integration tests for the new
   admin market route, not just deterministic unit fakes.
3. Autonomous connection monitoring, backoff after bans, metrics/alerts,
   caching for high-frequency consumers, symbol lifecycle and trade-status
   checks; observation alone is **not** ongoing monitoring.
4. Quota benchmarking and Binance terms review before any larger rollout.
5. Separate design approval and trust contract for M2-B signed/version-pinned
   **read-only** NDSP decisions (no production changes).

A successful GitHub Actions run does not authorize deploying, merging,
activating even paper orders, or starting a service daemon.
