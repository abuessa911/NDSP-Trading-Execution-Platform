# hunter_ksa1 bot — safe launch readiness

**Request:** owner wants to use hunter_ksa1 bot as soon as reasonably possible.

## Proven current status

- The bot's GitHub source repository is private. Branding is accepted by the owner, but underlying implementation still has Draft PRs, no approved production release, and M1 NOT ACCEPTED.
- A static Next.js UI is available in source and can be built for a preview.
- Real identity, tenants and browser authentication still need independent provider and persistence tests. Future pages use synthetic/demo data.
- NDSP is separate. Signed-source/CDS read-only bridge remains NO-GO until authoritative decision ownership, secure subject-entitlement binding and production KMS versions are approved.
- Existing console displays Simulation/Testnet/Live as appearance-only. It cannot execute trades.

## Safe preview scope

- Build static Next.js console from source using pinned pnpm lock.
- Static browsing only, with explicit DEMO and NO TRADING notices.
- The existing safety flags remain: TRADING_MODE=paper; LIVE_TRADING_ENABLED=false; GLOBAL_KILL_SWITCH=true; BINANCE_ALLOW_WITHDRAW=false.
- No customer data, exchange account keys, real NEX orders, live NDSP decisions, database migrations, or production source edits.
- A green CI proves build and UI tests; it is NOT a release approval for backend execution.

## Before authenticated access

- Verify OIDC IdP, genuine user login/logout and MFA gates, PostgreSQL+Redis connection and secrets under least privilege, tenant/role RLS and network authentication.
- Approve a protected ingress and domain with TLS, CSRF/rate limits, audit, backup, monitoring and rollback.
- Validate the bot's own M1 acceptance as an independent gate.

## Before demo orders or live trading

- Exchange sandbox/testnet with segregated secrets, withdrawal disabled, independent signing and strict risk budget.
- Actual order/risk/position engine with stops, notional/leverage limits, exposure caps, loss suspension, idempotency, fill reconciliation, disconnect recovery, kill switch.
- Independently approved NDSP source identity and signed decision handling; Published never means executable.
- Explicit owner approval of live execution once paper/shadow reliability is validated.

**Decision: UI PREVIEW MAY PROCEED AFTER TESTS. Authenticated full bot and all trading remain NO-GO.**
