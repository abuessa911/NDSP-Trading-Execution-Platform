# Genuine M1 authentication — isolated Keycloak PASS

**Authentication: PASS on this approved non-production test configuration.**
**Overall M1: NOT ACCEPTED. Administrator MFA: UNVERIFIED; access fail-closed.**

## Identity and configuration

- Repository: `abuessa911/nex`.
- Exact tested source: `4d60f189a1e3ef521c1c899c5f4726433ea821fc`.
- Branch: `m1-keycloak-auth-20261005`; remote main unchanged, no force push.
- Run: https://github.com/abuessa911/nex/actions/runs/37260289579
- Attempt 1; all three jobs successful.
- Provider: actual Keycloak 26.6.3, synthetic isolated realm/client/identity.
- Issuer: `https://localhost:18443/oidc/realms/nex-m1-test`.
- Exact callback: `https://localhost:18443/api/v1/auth/callback`.
- Exact post-logout URI: `https://localhost:18443/`.
- Source configuration: committed realm import and test-only Compose/TLS
  gateway; allowlisted synthetic inputs, not ambient credentials or databases.
- Architecture: browser Authorization Code/PKCE S256, pinned signed ID token,
  encrypted Redis BFF session and Secure/HttpOnly host-only cookie.

The user explicitly approved this dedicated isolated provider. The hosted
fixture used a fresh Linux VM and a git archive of the exact source. API TLS
verification remained enabled against the ephemeral test certificate; browser
certificate-error acceptance was limited to that disposable test origin.

## Actual observed results

`artifact/result.json` records **31/31 real browser acceptance checks PASS**.
Actual Keycloak authentication/callback created a NEX session; protected identity
returned HTTP 200; refresh rotated real provider credentials. Logout deleted
server state, removed the scoped cookie, invoked real token revocation and
provider end-session navigation, and returned to the registered URI.

Old session and refresh calls were denied. A cryptographically valid, unexpired
provider access JWT could not bypass terminated NEX browser-session state.
Keycloak rejected the revoked refresh token with `invalid_grant`; fresh provider
credentials were required. Live disabled-user/tenant, nonce/PKCE, role-constraint,
second-logout and provider-outage checks passed.

`artifact/sanitized-audit.json` retains **40 durable records**, including
LOGIN_STARTED, LOGIN_SUCCESS, LOGIN_DENIED, LOGIN_FAILED, LOGOUT_SUCCESS,
LOGOUT_FAILED, SESSION_REVOKED, TOKEN_REFRESH_SUCCESS and TOKEN_REFRESH_DENIED.
Only allowlisted audit fields/status metadata are exported.

Local deterministic verification: 74 tests passed, seven PostgreSQL tests
skipped locally. `docker-artifact/postgres-tests.txt` proves those **seven real
PostgreSQL tests passed on the hosted VM**. The unchanged original Docker
verification also passed. Both projects had empty scoped inventories afterward.

## Evidence map and integrity

| Path | Proof |
| --- | --- |
| `artifact/source.json` | Exact source/provider/configuration identity |
| `artifact/result.json`, `browser-checks.json` | Complete live acceptance verdict/checks |
| `artifact/cookie-properties.json` | Cookie security/scope/lifetime, without its value |
| `artifact/authenticated.png`, `logged-out.png` | Actual NEX browser state after clean redirects |
| `artifact/sanitized-audit.json` | Durable authentication successes/denials/failures |
| `artifact/sanitized-logs.json` | Allowlisted genuine provider startup/API operational events |
| `artifact/frontend-delivery.json` | Static/JSON delivery status and MIME types |
| `artifact/healthy-services.json` | Real image IDs, service state, non-root API and health |
| `artifact/resources-before.json`, `resources-after.json` | Fresh/empty scoped inventories |
| `docker-artifact/` | Original independent Docker/health/migration/safety/regression proof |
| `run.json`, `jobs.json`, `artifacts.json`, `hosted-job.log` | Genuine hosted run/job identities |
| `verified-digests.json` and ZIPs | Downloaded artifact integrity |

- Auth artifact ID **11324024490**, 358,679 bytes.
  SHA-256 **25baf1479ae19e4ecbf575c21443cb8995482b58cb249edfbb32737ce44b67ee**,
  verified against GitHub metadata; hosted expiry 2026-10-19 03:41:28 UTC.
- Docker artifact ID **11323954431**, 37,602 bytes.
  SHA-256 **4a9c4884fa0c2148ac71a92e054a29042e45073cbd6c1ff3758527614385c2f3**,
  also digest-verified; hosted expiry 2026-10-19 03:40:14 UTC.
- Downloaded copies remain retained independently of hosted artifact expiry.
- Raw JWT-string scan of retained text evidence found none. Token/cookie values,
  authorization codes, private keys, encryption keys and browser profiles are
  not retained. Normal request access logs and raw OAuth exception traces are
  excluded. Anonymous HTTP 401 console diagnostics are not authenticated grants.

## Retained unsuccessful attempts

Sibling directories preserve actual failures, never relabeled as acceptance:

| Run | Disposition |
| --- | --- |
| `../m1-auth-20261005-run37258251110/` | Unavailable Python verifier-tool version; no provider acceptance attempted |
| `../m1-auth-20261005-run37258733327/` | Healthy provider/API stack; static gateway MIME defect blocked frontend |
| `../m1-auth-20261005-run37259369563/` | Same delivery defect, with anonymous diagnostic evidence |
| `../m1-auth-20261005-run37259651235/` | Real login/session checks passed; sync/async verifier conflict stopped further checks |
| `../m1-auth-20261005-run37259950284/` | Real login/refresh and durable logout events; browser response-body retrieval failed after navigation, so acceptance was still FAIL |

The final verifier captures a clone of the unchanged real logout response before
UI navigation. It never substitutes fabricated responses or provider claims.
Original Docker evidence for `ee34ce97d4f0869d327c1601b37dd8456446045f`
and all older evidence remain unchanged.

## Limitations and scope

Revocation does not invalidate a stateless JWT's cryptographic signature or
expiration claim. Unrelated resource servers without revocation-aware validation
may accept an unexpired token. NEX browser mode instead requires live local
session state and refuses bearer JWTs, providing immediate denial after logout;
this was proved using a real independently verified unexpired access JWT.

Only this test provider/client configuration was verified. No production issuer,
administrator MFA, other-provider interoperability, enterprise SSO or long-term
provider hardening is established. API/gateway/provider/database/Redis resources
were deliberately cleaned up; no persistent provider is enabled in the workspace.

Minimal auth controls/generated-client integration were completed without a UI
redesign. Full specified Next.js user/admin-console divergence and existing
production/policy/operational M1 blockers remain. No production deployment,
NDSP/database access, M2, Binance, trading/execution, Paper Trading engine,
NMP/TDL or protected NDSP logic was introduced. Stop after authentication.