# Approved M1 console migration

## Authority and scope

The user explicitly approved migrating the existing NEX console from React/Vite
to Next.js after inspection of Master Spec sections 2.1, 12 and 19 and the frozen
M0/M1 scope. The existing artifact, API and data boundaries are retained.

**Overall M1 NOT ACCEPTED.** This work implements an M1 console and the specified
V1 navigation inventory, not functional later-milestone modules. A blocked or
deferred route is not evidence that the corresponding V1 capability is complete.
The full operational V1 frontend and all independent blockers remain gated.

## Architecture decision

Next.js App Router and TypeScript produce a static export. FastAPI remains the
sole owner of OIDC Authorization Code/PKCE, encrypted Redis sessions, identity
provisioning, tenant/role authorization, CSRF and provider logout. Generated
OpenAPI functions are reused without changing API contracts.

**Why:** Next.js is required by the Master Spec, but introducing another identity
server or moving the proven OIDC implementation would widen security scope.
Static HTML contains no identity, session, CSRF or protected data. Identity is
loaded only through same-origin `/api` requests in the browser.

All pages use no-referrer metadata. The portable gateway and static serve command
also send no-store and nosniff headers. There is no service worker or token
storage. Authentication state is in memory and rechecked on load, focus,
visibility and every 30 seconds. Identity is cleared on refresh failure, logout,
failed revalidation and cross-tab logout. A request generation guard prevents
older requests from restoring identity after logout. No browser role claim
unlocks administrative views.

## Functional M1 routes

| Route | Implemented behavior |
| --- | --- |
| `/` | Command Center: protected identity, public liveness/readiness, explicit safety baseline and milestone boundaries |
| `/health/` | Live public health, readiness component states including HTTP 503, manual/30-second refresh |
| `/settings/` | Protected user/tenant/role/status; display locale/timezone saved locally; session security explanation |
| `/subscription/` | Real `/api/v1/me` entitlements; no invented plan, subscription or purchase flow |
| Global session controls | Real generated-client sign-in, refresh, logout and identity check; disabled when unconfigured |

Display preferences are explicitly **browser-local formatting**, not translated
UI, synchronized account settings, notification preferences or a security
control. Only locale/timezone values enter localStorage.

## Specified routes unavailable in M1

Trading, Strategies, Positions, Orders, Trade History, Performance, Risk Center,
NDSP Decisions, Execution Trace / Why?, Replay Lab, Binance Connection and
Notifications have individually titled navigable routes with explicit milestone
gates. They do not fetch unimplemented APIs, simulate activity, accept
credentials, expose order/arming controls, or display invented zero metrics.

The MFA-guarded administrator console exposes read-only service readiness,
tenant users, tenant audit, and an internal `/api/v1/admin/operations`
projection. The projection reports the validated M1 safety configuration and
the existing `live_trading=false` entitlement. Billing, worker queues,
notifications and incidents explicitly report `NOT_IMPLEMENTED`; exchange and
NDSP connectors report `NOT_CONFIGURED`. No health is inferred for absent data
sources and no mutation control is mounted. `/audit/` remains blocked for
ordinary users; the existing tenant audit API is not repurposed as a user feed.

The API artifact registers `/api` and `/admin/v1` separately from the frontend
`/admin` routes. This preserves native admin API contracts and **does not alter
their authorization**. Existing backend role/tenant/MFA checks remain unchanged.
Frontend denial is not a replacement for backend enforcement.

## Build and portable packaging

```bash
pnpm install --frozen-lockfile
BASE_PATH=/ NEXT_TELEMETRY_DISABLED=1 pnpm --filter @workspace/ndsp-console run build
pnpm --filter @workspace/ndsp-console run typecheck
pnpm --filter @workspace/ndsp-console run test
```

Output is `artifacts/ndsp-console/out`, including separate HTML for every route,
Next client assets and a real 404 document. Unknown paths are not rewritten to
the Command Center. Preview runs the existing managed console workflow.

The original API-only Compose file and historical portable startup evidence are
unchanged. Opt-in frontend packaging uses:

```bash
docker compose -f docker-compose.yml -f infra/console/compose.console.yml build gateway
```

This new overlay has not been container-built or started in this workspace.
Local static delivery checks establish exported HTML/asset delivery, not clean
Docker startup or a fresh hosted provider result. The CI console job registers
the build and route checks; it has not been published or executed remotely here.

Starting/deploying this overlay still requires the existing authorized NEX-only
configuration, provisioning, migrations and TLS requirements. No production
deployment was performed. The gateway serves exported HTML/JS/CSS with correct
MIME types, routes `/api/*` and `/admin/v1/*` to FastAPI, and never converts API
errors into HTML successes. No Replit services or frontend secrets are required.

The isolated Keycloak verification harness now copies Next's `out` directory and
uses per-route static lookup. Its existing real-provider acceptance checks
remain intact. Historical provider verification is evidence for the previously
tested source, **not** a new provider acceptance claim for this migration.

## Acceptance boundaries

Local build/typecheck, five export/static-delivery tests, unchanged API
regressions and the targeted browser client-contract checks passed. The latter
used synthetic browser-only responses for identity, refresh and logout because
the actual workspace provider is unconfigured. They verify frontend state/CSRF
wiring, not genuine provider acceptance. No real identities were provisioned.
The existing browser run confirmed real anonymous hydration and 404 handling;
mobile interactions were not independently exercised.

No MFA implementation, default administrator, tenant provisioning, production
identity configuration, deployment, NDSP access, Binance integration, M2,
execution engine, risk engine, billing or trading work is authorized here.
Independent administrator MFA, production/provider assurance, policy drift and
other operational evidence remain separate blockers. M1 is NOT ACCEPTED until
all independent blockers have been resolved with measured evidence.
