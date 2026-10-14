# NDSP → NEX M2-B L6 — Source authority reservation/recovery prototype

Classification: DEVELOPMENT TEST ONLY / NOT REAL NDSP DECISIONS / NO TRADING.
Stacked upon Draft #8 (and earlier Draft PRs). No production merge, source or runtime change.

## Implemented isolated behavior
- A disposable PostgreSQL 16 schema with two immutable append-only tables: source-owned reservation of monotonically increasing versions; subsequently sealed Ed25519-signed artifacts. Reservations get unique, tenant-scoped operation UUIDs.
- A transactional PostgreSQL advisory lock plus uniqueness gives atomic first allocation, concurrent exact retry idempotence, prevents reassigning an operation UUID to different content, and refuses allocation of the next version while a previous reservation has no signed artifact.
- Fail-closed recovery test simulates a process crash between source reservation and signing by closing/reopening the pool; the unsigned revision is durable but remains unavailable to read. The same operation ID reuses its reservation; a strictly verified signed test fixture can then be sealed without creating a second version. A new source revision is allocated only after a seal.
- Explicit read returns NOTHING if the newest reservation is unsigned. Signing is verified independently from the preexisting isolated NDSP L4 Node-issued public Ed25519 fixtures, and output is non-executable BLOCKED/FLAT.
- Signed synthetic IdP token checks scopes reserve/seal/read, tenant context and independently provided test source-ownership mapping; RLS separates tenants. Direct UPDATE/DELETE/TRUNCATE denied. No HTTP handlers.
- Test-only issuer reserve allocator does not sign or produce a new signed envelope and cannot reuse real NDSP version authority. Node CDS L4 isolated signer issued the pre-provided version-1/version-2 test fixtures.

## Mandatory missing production design approval
- Real CDS journal must share a governed production transaction with completion/publication source mutations and guarantee durable source ownership/immutability; THIS test DB is not connected to real CDS, and using the test schema in production is forbidden.
- Signed JWT belongs to a disposable test IdP and synthetic owner mapping; not Supabase, Keycloak, or a verified live membership/tenant database. Do not trust caller-provided ownership maps in production.
- Ed25519/test contract profile has no approved real NDSP publisher keys, independent KMS/HSM trust lifecycle, revocation, production cross-language signed vectors or authorized read-only gateway.
- Source evidence is a synthetic allowlisted digest. Raw CDS payload/PII/TDL/NMP never enter this contract. Published state is not trading authorization.
- PostgreSQL advisory/unique rules are unit/prototype concurrency controls and require transactional CDS integration/recovery review before production.
- M1/M2-A/M2-B L1-L6 Draft PRs must not be merged or deployed by automated inference from CI green.

Release decision: real read-only NEX binding = NO-GO; NEX live execution = NO-GO.
