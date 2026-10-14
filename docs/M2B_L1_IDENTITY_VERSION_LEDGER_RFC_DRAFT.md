# RFC M2-B-L1 — Decision identity, version ledger and signing trust (DRAFT)

Status: REVIEW ONLY — not an approved production policy, migration, API change, merge or deployment. This branch is stacked on draft PR #3 (which is stacked on #2 and #1). No real NDSP data, paper orders or live trading.

## 1. Boundary and invariant
NDSP Completed Decision Service (CDS) is sole issuer of the original textual `CD-...` identifier; it is never rewritten, normalized into an irreversible synthetic identity or modified in historical records. NEX stores an independently generated random UUID (UUIDv4, server-side) per binding. Mapping is created only after trusted, scoped issuer/tenant validation, then immutable. Do not derive UUIDv5 from unapproved namespaces or accept caller-supplied NEX UUID as a binding authority. Every source identity is scoped by immutable verified issuer ID + trusted tenant binding + source environment + original decision ID. No source ID across tenants can be conflated. No NEX writes to NDSP.

## 2. Proposed records (NOT migrations)
`decision_bindings`: `binding_id UUID PK`; `issuer_id TEXT NOT NULL`; `source_environment TEXT NOT NULL`; `tenant_id UUID NOT NULL`; `source_decision_id TEXT NOT NULL`; `created_at TIMESTAMPTZ NOT NULL`; unique(`issuer_id, source_environment, tenant_id, source_decision_id`). The NEX UUID used by signed `decision_id` is bound to this `binding_id`; this relationship requires review against frozen NDSP-NEX-1.0 contract.

`decision_versions`: `binding_id UUID FK`; `version BIGINT CHECK(version>0)`; `source_revision_token TEXT NOT NULL` (only if issued by authoritative CDS); `evidence_hash TEXT NOT NULL`; `canonical_payload_hash TEXT NOT NULL`; `key_id TEXT NOT NULL`; `issuer_signature TEXT NOT NULL`; `received_at TIMESTAMPTZ NOT NULL`; `published_at TIMESTAMPTZ`; `status TEXT NOT NULL`; PK(`binding_id,version`). Insert-only (no UPDATE/DELETE even for corrections). Version numbers are issuer-assigned, monotonically increasing **per source decision and tenant scope**. Supersession is appended with explicit provenance; no wall-clock-derived version, no import-order-driven version, no renumbering after retry. Gaps require documented policy; never assume a missing predecessor implies safety.

`receipt_rejections` and `key_registry` are separate audited security records, not license to edit decision history. RLS, role grants, audit controls and concurrent insertion must undergo security review before production schema exists.

## 3. Atomic acceptance policy
1. Independently verify trusted issuer key and Ed25519 signature over the exact **approved** canonical bytes, key_id and signed contract version. A signature proves origin/integrity only; never authorizes orders.
2. Verify trusted tenant-to-issuer authorization and source-environment separation; deny unsigned/unpublished/private or expired source, mismatched evidence and wrong market/timeframe.
3. Transactionally bind original `CD-...` to a single NEX UUID on first authorized acceptance; replayed identity must resolve to the existing binding, never a new UUID.
4. For each binding, allow exact replay of the same version only when canonical payload hash, evidence hash, issuer, signer policy and source lineage match; record idempotent receipt. Reject same-version changed bytes, unsigned drift, older versions and untrusted future versions. Serialize competing arrivals per binding with an advisory/row lock.
5. Retain complete history and revocation events, and fail closed on unavailable trust registry, database, tenant mapping, missing provenance or ambiguous evidence.
6. Do not expose a read/write production endpoint from this proposal. NDSP-NEX-1.0 public M1 shape stays frozen. M1/M2-A/M2-B remain drafts.

## 4. Trust registry proposal
Use Ed25519 **only after dedicated approval**, stored signing keys in an issuer-owned KMS/HSM (never in NEX or git); verifier key records pinned by issuer, environment, key_id, public key fingerprint, not_before, not_after, revoked_at, and approval provenance. Support overlapping verification windows and auditable rotation; a revoked key must fail according to a preapproved historical-signature policy and a trusted issuance-time proof, not merely a client-controlled `issued_at`. Canonicalization, test vectors and key distribution MUST be mutually approved by NDSP and NEX. Prevent key substitution, cross-tenant replay, downgrade and algorithm confusion.

## 5. Test matrix for isolated implementation
- Stable `CD-...` roundtrip with independent NEX UUID, same original ID under different tenants/issuers, malformed IDs, collision tests.
- First version, unchanged replay, newer immutable version, same-version conflict, rollback, missing version, skipped version under chosen gap policy, concurrent writers and crash/retry.
- Signature tampering, unauthorized signer, unknown/revoked/expired key, rotation overlap, canonicalization differences, UTC/expiry and evidence hash mismatch.
- Cross-tenant read/insert, no-tenant context, direct UPDATE/DELETE denial, backup/restart continuity and no access to protected TDL/NMP fields.
- Run only against disposable isolated PostgreSQL using synthetic records. Keep public contract snapshot byte-identical; no real NDSP calls, no orders or production changes.

## 6. Acceptance blockers / signoffs
CDS team must implement and document an authoritative immutable version source and read-only Published/public export with tenant provenance, timeframe/expiry definitions and source evidence lineage. Security owners must approve canonicalization, Ed25519 trust distribution, key rotation/revocation and independent cross-language golden vectors. NEX owners must approve persistent migration, RLS audit, replay behavior, hosted Keycloak/Redis and M1 operational security. No merge/deployment/real data/trading until explicit independent authorization.

**Outcome of this RFC:** a reviewable decision and test specification only. No runtime behavior changes.
