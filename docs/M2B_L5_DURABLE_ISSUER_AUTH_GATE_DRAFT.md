# NDSP → NEX M2-B L5 — Durable source receipts and tenant claims (DRAFT)

**Classification:** synthetic-only test design and disposable CI execution.
**Production release authority:** NONE. PR remains Draft. No real customer data or trading.

## Scope and provenance
- Stacked upon PR #7 and the previously tested source-signed test-only NDSP CDS fixtures.
- Newly added: isolated PostgreSQL 16 source-side receipt schema, test-only Python source event consumer and permission-gated private-reader pure functions, pinned EdDSA verification of a disposable test IdP JWT, scoped tenant Row Level Security (RLS), and negative tests.
- Version 1 and version 2 are already signed by the isolated NDSP Node.js L4 publisher and checked against source metadata by the independent NEX verifier before being appended to a PostgreSQL preview database. The database enforces no missing first version, monotonic no-gap append, equal-version exact replay and stale/conflicting rejection.
- Read requires signed test identity with explicit ndsp.source.read scope and tenant claim, resolved from cryptographically verified token rather than a caller-supplied tenant parameter. Append requires separate ndsp.source.append scope **plus independent server-side fixture mapping between original CD-* decision ID and its authorized source owner**; a valid tenant B token cannot append a decision owned by tenant A. The only returned data are the already-verified NDSP-NEX-1.0 test envelope bytes. No decision is executable.
- Each CI job uses a fresh localhost nex_m2b_preview, creates dedicated no-superuser/no-BYPASSRLS m2b_l5_preview_app role, uses FORCE RLS, SELECT/INSERT-only grants and append-only triggers, then drops the temporary schema and role. The test ensures data persist across an application connection pool restart.

## Explicit limitations / production blockers
1. The L4 NDSP issuer is still a non-durable, memory-backed preview. This L5 database demonstrates durable receipts for signed source events in a disposable test only; it DOES NOT install a database ledger inside live CDS or authorize production version issuance. A real issuer must allocate and seal monotonic source revisions in an approved CDS transaction and solve signing/retry/recovery across failures.
2. The cryptographically valid JWT represents a synthetic IdP, not authentication against production Supabase/Keycloak or an existing NDSP membership table. Tenant claims must later be mapped from an authorized production identity provider and rechecked against issuer-owned decision ownership. RLS with a changeable session GUC is not alone production authorization.
3. There is no network interface and no live read-only gateway; private-read behavior is a guarded pure function. The existing GET /api/completed/id/:decision_id must not be treated as an authorized publisher.
4. Ed25519 trust uses ephemeral test keys, pinned test fixtures and test-only canonicalization, not a KMS/HSM production trust root, rotation/revocation policy or approved real signed decision.
5. NEX decision_id UUID and NDSP textual CD-... IDs remain separately governed; no schema or trading permission is inferred from successful synthetic tests.
6. Source evidence digest is synthetic metadata only; PII, NMP/TDL internals, secret keys, raw CDS payloads and execution instructions are excluded.
7. M1/M2-A security/operations and source owner governance gates remain pending; no merge/deployment/production data handling may occur without explicit separate review.

**Intended outcome:** prove test-only cryptographic permission enforcement, transactional receipt persistence and negative security behavior. Do not claim a production NDSP publisher, real authenticated tenancy, or approved release.
