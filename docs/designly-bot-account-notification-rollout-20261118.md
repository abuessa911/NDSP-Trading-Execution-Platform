# Bot personal settings and notifications — Designly guarded rollout

Status: **source-stage only**; not a production deployment or milestone promotion.

## Current ground truth
The M1 backend implements OIDC browser BFF, revocable sessions, tenant and role boundaries, and audited control endpoints. The console settings store *display-only* locale/time zone in the current browser; this is not server-synced account state. The previous Notifications navigation was a preview, not a live private notification engine.

## Implemented in this change
- Replace synthetic notification preview on `/notifications` with an identity-gated, bilingual AR/EN state page.
- Show clearly that in-app ledger, email and Telegram delivery have not been enabled; do not present inert toggles or invented delivery records.
- Preserve the existing logout/MFA, tenant, operator roles, and trading safety controls.

## Required next implementation gates
1. Migrate a **tenant_id + user_id** keyed preferences table and notification outbox with PostgreSQL row-level security and server-owned entitlements; separate audit trail.
2. GET/PATCH authenticated preferences with same-origin CSRF in cookie session mode; enforce exact provisioned identity and tenant on all reads/writes. Verify with two-tenant tests; no client-supplied user ID.
3. In-app notification feed with read/unread, durable event idempotency, per-tenant quota, and explicit event source.
4. Email verification and private Telegram /start link with 10-minute one-time code; separate user opt-in and unlink. Never accept raw chat ID, bot token or any credentials from the browser.
5. Dedicated send worker with retry-uncertainty handling and isolated secrets; do not reuse Radar/NDSP accounts or bots implicitly.
6. Notifications may show risk blocks or execution evidence **only** when official signed events exist. They NEVER become execution commands, arm Live mode, bypass MFA, or create API keys.
7. Real backend integration tests, stale/unauthorized/multi-tenant cases, genuine messaging smoke, and browser checks at 390/768/1920 before release.

Keep Bot independent of NDSP analysis; it may consume finalized decisions later under a reviewed contract. No live trading in M1.
