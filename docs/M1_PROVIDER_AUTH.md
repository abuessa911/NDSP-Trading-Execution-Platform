# M1 provider authentication — isolated Keycloak verification

## Authority and scope

The Master Spec and existing M1 source did not designate or configure an
operational provider. The user explicitly approved a dedicated, isolated,
non-production Keycloak test provider. This is not a production identity
configuration and does not invent historical user mappings.

The committed realm import uses **Keycloak 26.6.3**, a public OIDC client
`nex-m1-browser`, Authorization Code only, enforced PKCE S256, rotating refresh
tokens, no implicit/password/direct-access/service-account grants, and a clearly
synthetic test identity. Realm/user IDs are explicit test fixtures. The identity
is separately provisioned into the new disposable NEX PostgreSQL database
through the existing trusted bootstrap procedure.

- Provider issuer: `https://localhost:18443/oidc/realms/nex-m1-test`
- Exact callback: `https://localhost:18443/api/v1/auth/callback`
- Exact post-logout URI/frontend: `https://localhost:18443/`
- Configuration: `infra/testing/keycloak-realm.json`, `compose.auth.yml`,
  `nginx.auth.conf` and the allowlisted synthetic test harness environment.
- Production remains unconfigured; no production deployment, credentials or
  databases are used. No NDSP access, MFA implementation, M2 or trading work.

## Runtime contract

`POST /api/v1/auth/login` requires the exact configured Origin. It persists a
five-minute encrypted login transaction with independent high-entropy state,
nonce, PKCE verifier and an HttpOnly browser binding. The verifier never reaches
the browser. The callback consumes the binding-matched transaction atomically,
uses the exact configured redirect, exchanges the code over TLS, and verifies
the ID token against the pinned issuer, client/audience/authorized party,
provider JWKS, algorithm, expiration, issued-at, optional not-before and nonce.
The existing verifier retains its bounded 30-second clock-skew allowance.

Discovery must advertise authorization code/S256 and match the configured issuer
and JWKS. Provider endpoints are restricted to that issuer's HTTPS origin;
redirect-following is disabled. Provider requests have bounded timeouts and
response sizes; JWKS keeps the existing streaming size/key limits.

Issuer+subject is mapped to the existing provisioned NEX user. Every protected
request rechecks active user, active tenant and recognized role. No provider
tenant/role claim becomes authority. ADMIN/SUPER_ADMIN remain fail-closed pending
independently verified administrative MFA.

Browser mode accepts only opaque server-side sessions, **not bearer JWTs**, even
when a provider access JWT is correctly signed and unexpired. The previous
bearer-only mode is preserved when browser login is explicitly disabled; its
login/logout endpoints still fail explicitly with 501.

## Sessions, CSRF, refresh and logout

Redis stores encrypted records, never plaintext provider tokens. Redis keys hash
opaque identifiers. The session key is a dedicated Fernet key delivered through
the existing environment/mounted-file secret-provider interface. There is no
production in-memory fallback. Redis must be healthy.

`__Secure-nex_session` and the temporary `__Secure-nex_oidc` cookie are Secure,
HttpOnly, host-only, Path=/api and SameSite=Lax for the top-level OIDC callback.
Sessions default to 1,800 seconds, configurable only between 60 and 3,600 seconds;
refresh does not extend the original total lifetime. Callback success/failure
redirects to a clean application URL. Tokens are not returned to JS or persisted
in browser storage; the session CSRF value is held only in component memory.
Authentication/protected responses use no-store and no-referrer.

Refresh/logout require exact Origin plus the session-specific X-NEX-CSRF header.
Refresh uses the provider's real refresh token, validates any refreshed ID token
against the same identity, and commits through a Redis compare-and-swap. A
concurrent logout wins; refresh cannot recreate a deleted session. Tokens issued
in a lost race are submitted for revocation.

Logout deletes local Redis state **before** contacting the provider. It revokes
the refresh and access tokens through RFC 7009 when advertised, clears the
session cookie and returns the supported RP-initiated logout endpoint. The
browser completes provider logout, including provider confirmation when required.
Only client_id and the exact registered post_logout_redirect_uri occur in this
URL; there is no id_token_hint in history/query strings. Non-standard legacy
refresh-token logout and privileged provider Admin REST calls are not used.

Provider failure does not restore a terminated local session. Logout returns
explicit failure if supported revocation fails. A public provider may lack a
revocation/end-session endpoint; those capabilities are reported honestly, never
represented as performed. The selected Keycloak fixture supports both.

**Access-token limitation:** RFC 7009 acceptance and provider session termination
do not erase a signed JWT's mathematical validity at unrelated resource servers
that validate it statelessly until expiry. NEX browser mode does not trust that
token after local logout; captured session IDs and direct bearer replay are
rejected, and the provider refresh token must fail with invalid_grant.

## Audit and verification

Authentication routes use the existing independent, bounded durable Appendix B
writer. LOGIN_STARTED/SUCCESS/DENIED/FAILED, LOGOUT_SUCCESS/FAILED,
SESSION_REVOKED and TOKEN_REFRESH_SUCCESS/DENIED have stable reason codes.
No tokens, codes, credentials, IPs, user agents or arbitrary provider payloads
enter audit metadata. Required audit failure blocks authentication-sensitive
success. Other M1 routes retain their existing middleware audit contract.

Deterministic tests are explicitly not provider acceptance. The separate hosted
`m1-auth` job runs actual Chromium against actual Keycloak and the delivered NEX
frontend/API, with a fresh test-only PostgreSQL/Redis stack and exact committed
source from git archive. It checks login, protected access, secure cookies,
encrypted storage, real refresh rotation, logout/revocation, provider SSO logout,
session/bearer/refresh rejection, active identity boundaries, nonce/PKCE failure,
invalid-role constraints, durable sanitized audit, and outage readiness.

The test-only loopback TLS certificate is trusted explicitly by the API; TLS
verification is not disabled there. Chromium accepts this ephemeral self-signed
test certificate. Test resources bind to loopback on a fresh hosted Linux VM.
Original portable Docker checks run separately, unchanged in their own job.
Historical Docker evidence for ee34ce97d4f0869d327c1601b37dd8456446045f is preserved.

Evidence contains commit identity, sanitized startup/runtime/audit records,
checks, screenshots, image identities, health and scoped cleanup. No tokens,
browser profiles, TLS private keys or session encryption key are retained.
Until a successful hosted run is inspected, authentication status is
**IMPLEMENTED_BUT_PROVIDER_VERIFICATION_PENDING**, not PASS. Overall M1 remains
**NOT ACCEPTED** regardless of authentication results because administrative MFA
is outside this task.

Official provider references:
- https://www.keycloak.org/securing-apps/oidc-layers
- https://www.keycloak.org/server/containers
- https://www.keycloak.org/docs/latest/server_admin/#rp-initiated-logout

## Inspected verification — 2026-10-05 UTC

**PASS for the approved isolated provider configuration; overall M1 NOT ACCEPTED.**
Exact tested source: `4d60f189a1e3ef521c1c899c5f4726433ea821fc`.
Hosted run https://github.com/abuessa911/nex/actions/runs/37260289579 passed all
three jobs, including **31 actual browser/provider checks** and all seven
unchanged real PostgreSQL regressions. **40 durable audit records** cover every
required authentication action. Both uploaded evidence ZIP digests were
independently verified after download.

See `docs/evidence/m1-auth-20261005-run37260289579/README.md` and
`M1_FINAL_EVIDENCE_REPORT.md` section 12 for measured proof, retained failures
and precise JWT revocation limitations. This is neither a production identity
configuration nor administrator MFA verification. The disposable provider
was removed; workspace sign-in remains explicitly unconfigured. Broader
Next.js console divergence remains outside this authentication-only change.