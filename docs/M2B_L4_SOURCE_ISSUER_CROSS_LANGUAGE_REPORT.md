# M2-B L4 — Isolated CDS publisher and independent NEX consumer proof

STATUS: SYNTHETIC TEST ONLY. No real source intake, no approved signing authority, no production DB or service changes; no trading.

## Source-side implementation
Authoritative live CDS-001 and its public API were NOT changed. The source-derived sandbox is a separate local Git tree on Contabo:
- Source: /home/ndsp/ndsp-nex-signing-dev-20261014
- New branch: dev/ndsp-nex-l4-isolated-issuer-20261014
- Prototype: backend/services/completed_decision/publisher/ndsp_nex_l4_isolated_issuer.cjs
- Reuses existing ndsp_nex_test_signer.cjs (a test-only overload permits one volatile test key pair per synthetic issuer instance)
- Source-bound version journal is **in memory only**: it appends versions, retains snapshots without a public mutation API, caches exact signed bytes for replay; this is NOT durable, crash-safe, transactional with authoritative CDS, or approved production versioning.
- Synthetic tenant scopes come from an in-memory fixture session map, not client tenant parameters. This is NOT real OIDC, account ownership or production tenant authentication.
- Synthetic source records require explicit test marker and no protected input. Published/public only, finite UTC expiry, supported market and timeframe, no public payload/PII/TDL/NMP internals. All emitted NDSP-NEX-1.0 decisions remain BLOCKED/FLAT and execution_authorized=false.
- Ephemeral Ed25519 test key is stable within an issuer instance. Its test key_id is tied to a public-key fingerprint; no private key is stored. Process restart rotates ephemeral test key and resets in-memory journal, so this MUST NOT be used for production signing/version authority.

## NEX cross-language evidence
Two versions of one synthetic source ID were issued by isolated Node.js CDS source module. Their independent public Ed25519 test key and allowlisted source metadata are stored under apps/api/tests/fixtures/ndsp_l4_source_publisher (5 JSON files). Python NEX independently verifies both signature/canonical JSON, source UUIDv5 test mapping, source ID, hash, version, state, time and expiry. A disposable PostgreSQL 16 test consumes both through the pre-existing M2-B L2 NEX ledger with exact replay idempotence, immutable source mapping, tenant RLS, rejection of rollback, and persistence after reconnect.

The UUIDv5 namespace is ONLY for cross-language synthetic compatibility; actual NEX binding UUIDv4 remains independently owned by NEX. No protected data or private keys are transferred. No real CDS API, server, database, secret, user record or NEX order interface is contacted.

## Gates still open before real NDSP data
1. Authoritative durable CDS-issued monotonic version transaction, replay rollback policy and producer-side historical integrity; current in-memory version reset makes L4 issuer not production-ready.
2. Approved tenant membership derived from server auth and real issuer identity, not fixtures or caller parameters.
3. A dedicated private read-only Published/public exporter (not unrestricted existing by-ID CDS route), least privilege, authorization, bounded pagination and audit.
4. Source evidence provenance (currently synthetic metadata SHA256, NOT NDSP-certified evidence), real timeframe, validity and decision/flow semantic mapping; never treat Published as EXECUTABLE.
5. Ed25519 canonical signing profile, KMS/HSM key ownership, rotation and revocation semantics, independently approved production golden vectors.
6. M1 security/operations approval and M2-A genuine Redis/Keycloak acceptance; explicit change and deployment approval. Existing PRs remain Draft.

**NO-GO for real NDSP read-only integration or any trading activation.**
