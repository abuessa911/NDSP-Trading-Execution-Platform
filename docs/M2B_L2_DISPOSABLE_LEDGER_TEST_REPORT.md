# M2-B L2 — disposable identity/version ledger proof

STATUS: DEVELOPMENT TEST ONLY. No production migrations, releases, connectors, trade authority, NDSP edits or public M1 contract changes.

This branch is stacked on Draft PR #4; PR #4 is stacked on Draft #3, #2, #1.

## What is implemented
- Creates a fresh, separate local PostgreSQL schema m2b_l2_preview under ONLY nex_m2b_preview; create/drop is confined to a guarded disposable CI database.
- Retains the original synthetic CDS CD-... source identity. Creates a distinct random NEX-owned UUIDv4 binding scoped to a trusted fixture tenant + fixed synthetic issuer + test environment.
- Validates Ed25519 issuer test signatures and source/evidence fields using preexisting synthetic-only verifier BEFORE touching the database.
- Appends signed versions with a per-binding monotonic check, idempotent exact newest replay, rejection of old/conflicting versions, transactional source identity lock and unique constraints.
- Restricts test application role to SELECT/INSERT; enables FORCE RLS on both tables and has anti-update/delete triggers. Tests isolation, concurrent replay, read-after-restart and tamper rejection.
- Does NOT use NEX UUID as a substitute for the signed NDSP-NEX-1.0 decision_id: the exact signed source UUID remains separate; final contract mapping is still unapproved.
- All test credentials are fake and fixed; CI must have a fresh loopback PostgreSQL 16 container. No network call to real NDSP is made.

## Important limitations
- This code accepts only synthetic source_environment=test. No real NDSP metadata is eligible.
- The test fixture's trusted tenant ID and public key dictionary are NOT real administrator authentication, real tenant provenance, signed issuer registry or live key rotation. PostgreSQL session GUC tenant scope cannot by itself establish production tenant authority.
- The synthetic source UUIDv5 namespace, source version, publication and expiry metadata remain UNAPPROVED for production use.
- No snapshot/key lifecycle, KMS integration, independent production signed vectors or server-side trusted exporter exists yet.
- PostgreSQL role/schema testing is not a safe production database migration. Never promote the SQL or the Python consumer as-is.

## Acceptance
GitHub Actions m2b-l2-isolated.yml runs test-only lint, mypy, disposable PostgreSQL acceptance and the frozen public M1 OpenAPI check. The PR must remain Draft even after green CI. Independent NDSP governance, contract, issuer signing/tenant-authorization and NEX security reviews precede any real data or execution work.
