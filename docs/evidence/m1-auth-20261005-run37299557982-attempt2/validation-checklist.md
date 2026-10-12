# Administrator MFA validation-only acceptance

Date: 2026-10-05 UTC. The earlier task-completion bypass is not acceptance evidence.
This is a fresh execution of the existing genuine-provider harness, not a
redesign, mock authentication run, or relabeling of attempt 1.

## Provenance

- Provider: disposable isolated Keycloak 26.6.3, synthetic identities only.
- Exact tested source: `993305fc72f4e3e1b7726d5ef148c1cd1061a798`.
- Hosted run: `37299557982`, attempt **2**, authentication job `111736924942`.
- Fresh execution: 11:18:24–11:25:12 UTC; job conclusion **success**.
- URL: https://github.com/abuessa911/nex/actions/runs/37299557982/attempts/2
- Artifact: `m1-auth-37299557982-2`, GitHub artifact ID `11342455607`.
- Verified SHA-256: `731cd77cff06022d6074721c12055b454827edb3ec690ecaaf6da0c30faf4574`.
- Evidence directory: `docs/evidence/m1-auth-20261005-run37299557982-attempt2/`.
- Core checks: **31/31 PASS**. Administrator MFA checks: **48/48 PASS**.
- No runtime, provider-policy, workflow, or test-harness changes were made.

## Required acceptance checklist

The entries below map to actual assertions in `artifact/mfa-browser-checks.json`,
with core logout assertions additionally in `artifact/browser-checks.json`.
The tested harness is retained in Git at the exact source SHA above.

| Required behavior | Result | Actual evidence |
|---|---|---|
| ADMIN password + valid TOTP | PASS | Fresh genuine provider flow; bound ADMIN session; signed issuer/client/subject and `pwd` + `otp`; server health allowed |
| SUPER_ADMIN password + valid TOTP | PASS | Separate fresh genuine provider flow; bound SUPER_ADMIN session; signed factor and subject checks; server health allowed |
| Correct password without MFA | DENIED / PASS | Password-only ADMIN remains at required TOTP challenge/enrollment with no NEX session; ordinary client cannot grant administrative assurance even after real OTP |
| Wrong/expired/invalid TOTP | DENIED / PASS | Actual provider rejects a code generated 20 time windows in the past, retains TOTP challenge and issues no NEX session. This one deliberately invalid/expired-code test covers both requested labels; they are not counted as independent tests |
| Replayed TOTP | DENIED / PASS | Previously accepted ADMIN TOTP is resubmitted in the same time window and rejected without a NEX session |
| Disabled ADMIN | DENIED / PASS | Local disabled identity returns USER_DISABLED; separately, actual Keycloak disablement causes MFA_REVOKED despite a previously valid MFA session |
| Disabled SUPER_ADMIN | DENIED / PASS | Same local and actual provider disablement checks independently pass for SUPER_ADMIN |
| USER privileged access | DENIED / PASS | Real USER denied privileged health; no administrator assurance, including after refresh. USER audit-route denial is not separately exercised in this suite |
| OPERATOR privileged access | DENIED / PASS | Real OPERATOR denied both privileged health and audit routes; no administrator assurance |
| Disabled tenant | DENIED / PASS | Both administrative roles denied audit access with TENANT_DISABLED while their tenant is disabled |
| Revoked session | DENIED / PASS | Real provider revocation denies privileged access with MFA_REVOKED and deletes the local session |
| Logged-out session | DENIED / PASS | Real MFA ADMIN logout reports provider revocation, deletes stored opaque session, and old cookie receives 401 on privileged health |
| Stale session after role/status change | DENIED / PASS | Both roles denied after server-side downgrade to USER; local/provider disabled-status cases also deny existing sessions |
| Refresh cannot manufacture assurance | PASS | Real USER refresh does not create administrator assurance |
| Refresh cannot preserve invalid assurance | PASS | Revoked ADMIN session cannot refresh; real elapsed SUPER_ADMIN assurance expiry cannot be extended by refresh; successful ADMIN refresh preserves the original verified assurance/auth_time |
| Server-side enforcement | PASS | Direct privileged HTTP requests and signed-token verification; bearer token cannot bypass required opaque MFA session; missing cookie and provider outage fail closed |
| Tenant isolation | PASS | Both administrative roles receive cross-tenant audit 404; returned admin audit rows are constrained to the active tenant |
| Logout/revocation | PASS | MFA-specific checks above plus genuine core provider logout, refresh revocation and denial of reuse of terminated sessions |
| Durable sanitized audit | PASS | Database-read audit contains 148 rows, required auth actions, MFA verification success, privileged health success and denial, and MFA_REQUIRED denial |
| Sensitive data in new retained evidence | PASS for performed checks | Archive scanned before extraction for credential assignments, JWTs, OTP enrollment URIs and private keys; no detections. Audit metadata permits only numeric/boolean returned/status_code. MFA screenshots visually checked; no codes/seeds/tokens. This is not a universal absence proof for all historical Git objects |
| Isolated cleanup | PASS | Owned container, network and volume inventories are empty after cleanup |

## Independent evidence validation

The downloaded archive was hashed and matched to GitHub's advertised digest.
Its source/provider identity, successful job metadata, all 79 check booleans,
required audit action/outcome assertions, audit field/value allowlists, and
empty cleanup inventories were independently checked. Results are in
`independent-validation.json`. Historical attempts and reports remain unchanged;
this attempt is stored separately. No raw provider credentials were copied
into new committed evidence. The authentication archive is the only new bundle
downloaded for this attempt.

## Limits and acceptance

**ADMINISTRATOR_MFA = PASS** for this isolated provider and exact source.
**Task #15 = UNBLOCKED with respect to its MFA prerequisite; not started.**
**M1 OVERALL = NOT ACCEPTED.**

No requested fail-closed checklist item remains failed or unverified within
the scoped coverage described above. The suite does not claim an exhaustive
role-by-route-by-negative-case Cartesian test matrix.

The overall workflow remains failure because the separate Docker-readiness
failure from attempt 1 is carried forward. API and Next.js success results are
also carried forward; their timestamps show they did not execute fresh in
attempt 2. Docker readiness remains with the existing separate task.

Administrator audit usability is not accepted: an RLS-filtered empty result can
pass the isolation assertion without proving useful administrator audit rows.
That remains administrator-view work, not this MFA validation.

No production/provider readiness, deployment, NDSP access, authenticator
recovery/replacement, administrator-view implementation, M2 or trading work
was performed or authorized. Platform task state must be distinguished from
these evidence conclusions; no completion-validation bypass is used here.
