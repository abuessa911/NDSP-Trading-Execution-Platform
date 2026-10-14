# M1 — security review checkpoint (2026-10-14)

**Verdict: HOSTED ACCEPTANCE TESTS PASS; production security acceptance PENDING.**

Verified against private draft PR #1 at commit
`7ceb434ae3d1c751a23f66014b07bbab362b8aa6`, hosted run
`38453727829`: `api-static`, `console`, `postgres-redis`, and `keycloak-mfa`
all completed successfully. The source currently enforces:

- `TRADING_MODE=paper`, `LIVE_TRADING_ENABLED=false`, `GLOBAL_KILL_SWITCH=true`,
  `BINANCE_ALLOW_WITHDRAW=false` at configuration validation time.
- Server-side identity checks and tenant lookup; admin routes use
  `get_administrator` and the administrator MFA dependency.
- Dedicated test-only Keycloak policy, including real disposable MFA exercises.
- M1 operations screens report absent services as unavailable/not implemented,
  without fabricating live exchange connectivity.
- Current draft has no live exchange keys or execution endpoints.

The green hosted CI is **not** proof of all deployment/security gates:

- The only explicitly verified administrator MFA provider policy in M1 config
  is **test-scoped**. Production identity provider, MFA policy and recovery
  must undergo separate authorization, hands-on testing and audit evidence.
- Perform deployment-specific OWASP threat review, secret scan, dependency
  vulnerability/SBOM review, user-role segregation and backup/restore drill.
- Verify real ingress TLS, session/CSRF/logout properties, RLS against the
  actual tenant configuration, alerting and incident runbooks.
- No merges, NDSP production deployment, exchange account/API key attachment,
  billing activation, real orders, or unlock of global kill switch are approved.

**Authorized next work:** M2-A read-only Binance public market-data adapter on
an independent *stacked draft branch* based on PR #1, without integrating
NDSP or enabling automated/live trading. This document is a checkpoint, not
an operational compliance certification or launch approval.
