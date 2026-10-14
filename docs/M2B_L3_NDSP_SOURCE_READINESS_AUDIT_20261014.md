# M2-B L3 — Scoped canonical NDSP source readiness audit
STATUS: AUDIT PASS; REAL PRODUCTION LINK NO-GO; M1/M2-A/M2-B/L1/L2 drafts unmerged.

## Audited evidence — 2026-10-14
Remote Desktop Commander on authorized Contabo device vmi2934783 inspected ONLY source files, not user decisions or database:
- Canonical: /home/ndsp/empire-core-v5-1-1-clean/backend/services/completed_decision/main.cjs
- Isolated source snapshot: /home/ndsp/ndsp-nex-signing-dev-20261014/backend/services/completed_decision/main.cjs
- Both SHA256: 2fea7f5e00193fb49ac5e6b74fce83bc443716d6acd02cc9689f6c26ea54f09e
- Canonical completed decision contract SHA256: 70c0cdd430b31e27e2e15e8e4fea35af07c7fef76e652f3d7bd642786c0f3e57 (matched isolated snapshot).
- Isolated source script: tests/ndsp-nex-l3-source-readiness-audit.sh, commit 02e63d635414ee75b213ec15b237e95cc0a551b0 in LOCAL branch dev/ndsp-nex-l3-source-readiness-20261014; this sandbox has no remote.
- Script reported PASS_SOURCE_INSPECTION_ONLY, real_link=BLOCKED, databases_connected=0, records_read=0, production_files_modified=0.
- Runtime launch policy in canonical governance: PUBLIC_LAUNCH=NO. No production host source writes, service restarts, HTTP requests, DB connection, order or production NEX actions were performed.

## Verified blockers in CDS source
1. Existing decision table stores decision_id TEXT UNIQUE, but declares no decision_version BIGINT and no tenant_id UUID. The static table definition alone does not certify actual deployed schema or rule out independent identity services; authoritative source version/tenancy remain unproven. Never derive a version from updated_at or sequence guesses.
2. expires_at is nullable in the source bootstrap; signing requires a finite issuer-approved expiry and authoritative valid_from/timeframe/market/direction.
3. GET /api/completed/id/:decision_id uses SELECT * WHERE decision_id=$1 LIMIT 1 with no Published/public filter in that query. External gateway authentication may exist but was not verified here. Do not use this route as the new exporter.
4. Existing ingest uses ON CONFLICT(decision_id) DO UPDATE, which can mutate source fields. A separate append-only authoritative issuer version/event log requires governance and ownership review, not a consumer-inferred revision.
5. Published is a visibility/publication state, NOT trading authorization. No direct NEX orders or conversion to EXECUTABLE.
6. Data minimization: never export raw payload, TDL/NMP formulas, thresholds, user identity, protected layers, or private evidence in the signed contract.
7. Ed25519 is still a TEST PROPOSAL: official issuer canonical bytes, KMS/HSM custody, trust distribution and revocation, signed independent vectors must be approved before real use.

## Next needed NDSP-side decisions (not silently implemented)
- Source owner approves immutable source revision/append-only journal and historical compatibility.
- Identity owner approves authenticated tenant/issuer mapping independently of client parameters.
- Security owner approves Published/public read-only projection through private gateway with authorizer, rate limits, deny-by-default and audit, not direct CDS by-ID route.
- Both parties approve signed contract mapping or a versioned contract change that retains the CD source id; verify immutable source-to-NEX mapping and timestamp windows.
- Keys require independent approval and rotation/revocation semantics.
- Full isolated end-to-end integration with real non-sensitive approved staging decision data may follow only after separate authorization. A signed decision can NEVER directly trigger an order.

## Scope of GitHub L3 tests
CI independently asserts synthetic attempts to claim source_environment=production are refused even with a valid re-signed test signature; missing source version/extra protected data are rejected; verified Published test data remains BLOCKED and execution_authorized=False; M1 public OpenAPI contract unchanged. It does not assert that a real CDS issuer/exporter exists, that the production DB has tenant/versions or that a real NDSP decision has been processed.

Recommendation: HOLD all real-read integrations. Keep this PR and upstream PR #1-5 Draft.
