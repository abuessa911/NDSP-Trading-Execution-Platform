# M2-B: Signed NDSP-NEX-1.0 contract — isolated test preview

**STATUS: synthetic signature-verification prototype ONLY; not an accepted NDSP
production connector, trusted signature profile or trade authority.**

## Source of truth and version

Authority: `docs/reference/MASTER_SPECIFICATION_V1.docx`, §3.2,
and `docs/architecture/M0-architecture-freeze.md`.
The fixed V1 contract is `NDSP-NEX-1.0`, containing exactly:

- `contract_version`, `decision_id`, `decision_version`;
- `asset`, `market`, `timeframe`, `direction`;
- `decision_state`, `scenario_state`, `risk_class`;
- `valid_from`, `valid_until`, `issued_at`;
- `source_system`, `source_environment`;
- `evidence_hash`, `key_id`, `signature`.

No NDSP NMP/TDL formulas, protected indicators, thresholds, layer internals or
source code enter NEX. No execution intent, order, position or simulation is
authorized by a cryptographically valid decision alone.

## Implemented as an OFFLINE synthetic-test-only prototype

`apps/api/nex_api/ndsp_contract_preview.py` provides an isolated pure
verification function. It **does not** register any FastAPI route, open an
HTTP connection, read a real NDSP key or private credential, persist a
decision, manipulate an NEX state machine, or alter NDSP.

- Enforces exact field set to reject extra protected inputs and missing fields.
- Rejects duplicate JSON keys, UTF-8/schema errors, oversized payloads,
  invalid UUID/version/asset/market/enumerations, and non-UTC timestamps.
- Checks trusted `key_id` against an *explicitly supplied* 32-byte public key.
  Payload-specified keys are not trusted.
- Tests a **PROPOSED** Ed25519 signature over UTF-8 JSON serialized with
  sorted keys, compact separators and `ensure_ascii=False`, excluding
  `signature`. This serialization is **not** a claimed NDSP issuer standard.
  NEX must not assume that NDSP currently signs in this format.
- Rejects signatures altered after signing, unknown signing keys, source
  system other than NDSP and unapproved contract versions.
- Limits this prototype to `source_environment=test`: a real production NDSP
  decision is **deliberately blocked** even if it has a valid test signature.
- Rejects values outside `valid_from <= now < valid_until` and future issue
  time. Returns immutable metadata with `execution_authorized=False`.
- Signing keys in unit tests are generated ephemerally for synthetic
  test vectors; **no private signing keys are included in code or CI.**

## Independent NDSP-side synthetic publisher cross-compatibility

The authorized publisher prototype is in an **entirely separate local Git
sandbox on Kali**, not part of the NEX repository or NDSP production source.
The NDSP deployment folder is not itself a Git checkout and an NDSP source
repository is not available to this environment, so this is **not a branch
of the canonical production project**.

The issuer-side preview signs a fixed `source_environment=test`,
`decision_state=BLOCKED` decision with a throwaway private key generated
in memory. **Only** the signed synthetic JSON document and a separately
pinned test public-key record are copied into
`apps/api/tests/fixtures/ndsp_publisher_preview/`. The fixture's
`signed_bytes_sha256` is independently recomputed in NEX and the pinned
test public key is supplied to the verifier from the separate fixture, not
from the untrusted signed payload.

The independent conformance test
`test_ndsp_publisher_golden_preview.py` checks acceptance plus signature
tampering, unknown key, expiry and inability to claim production trading.
It neither fetches production NDSP data nor contains any issuer signing
private key. This is proof that two independent **test implementations**
agree on the proposed signature bytes; it is **not** proof that the
current NDSP production platform issues or approves these signatures.

## Additional disposable PostgreSQL replay/tenant proof (not a NEX migration)

The separate `ndsp_replay_preview.py` proof has no FastAPI route and accepts
only `VerifiedSyntheticDecision` metadata whose environment remains `test`.
It explicitly requires a trusted tenant ID supplied by the test fixture,
never a client-owned tenant identifier. The SQL definition lives **only** in
`infra/testing/m2b_receipt_preview.sql`: it is **not** in Alembic migrations,
NEX's runtime Base metadata, deployment manifests or NDSP.

- Disposable GitHub PostgreSQL 16 service uses the literal database name
  `nex_m2b_preview`, localhost only and **synthetic test passwords**.
  The test refuses any alternate DB, hostname, username or password.
- The test administrator creates a dedicated no-superuser/no-BYPASSRLS
  `nex_m2b_preview_app` role and a freshly created schema, and drops both at
  the end; an existing test role/schema causes refusal, not reuse.
- A primary key on `tenant_id,decision_id,decision_version`, FORCE ROW LEVEL
  SECURITY, scoped `current_setting('m2b.tenant_id')`, SELECT/INSERT-only
  grants and UPDATE/DELETE triggers protect immutable receipts.
- Transaction advisory locking and latest-version checks make concurrent
  identical deliveries idempotent, reject older versions and same-version
  conflicting evidence, and append newer versions without erasing history.
- Tests confirm tenant isolation, zero visibility with no tenant context,
  rejection of UPDATE/DELETE, concurrency behavior and persistence after a
  database-connection-pool restart.
- This is only a **proof** of the persistence and tenant RLS design with
  synthetic metadata. It does **not** make real signed NDSP decisions admissible,
  bind an actual verified signer to tenant ownership or authorize trading.

**Read-only NDSP evidence audit (14 Oct 2026):** the existing NDSP source tree
contains `backend/architecture/contracts/COMPLETED_DECISION_CONTRACT.md`,
which defines a read-only published/completed-decision consumer boundary, but
the inspected backend contract and architecture sources did **not** yield
an issuer-published signed `NDSP-NEX-1.0` contract, golden vector or approved
canonical signing profile. This scoped inspection is not a claim that
no additional private integration material exists. Do not derive a fake
signature from an unsigned completed decision.

## Mandatory blockers before actual M2-B acceptance

1. **NDSP publisher contract:** an approved immutable `NDSP-NEX-1.0` JSON
   schema, exact canonicalization/signature algorithm, encoding, key
   distribution, rotation/revocation and independently produced golden vectors.
   The proposed Ed25519 profile in this PR is not binding on NDSP.
2. **Trust origin:** actual NDSP read-only URL or approved read-only export,
   mTLS or scoped authentication, allowlisted origin and tenant binding;
   NEX must have **zero** NDSP write permission.
3. **Persistence/idempotency:** durable NEX-owned `decision_id`/
   `decision_version` uniqueness and monotonic supersession with append-only
   audit, per-tenant ownership, rollback/replay rejection and failure recovery.
   This preview **has no durable replay protection** and must not consume
   production decisions.
4. **Semantic policy:** asset symbol and market mapping, supported timeframes,
   clock-skew allowance, execution eligibility for `BLOCKED`/
   `UNDER_MONITORING`/`FLAT`, expiry and concurrency rules; never interpret a
   signed payload as a direct order instruction.
5. **Operational gates:** M1 real production administrator MFA security sign-off,
   M2-A hosted Keycloak/Redis acceptance, monitoring/backpressure and failure
   observability, safety review and explicit separate rollout approval.

## Offline checks

```sh
uv run --frozen ruff check apps/api/nex_api/ndsp_contract_preview.py \
  apps/api/tests/test_ndsp_contract_preview.py
uv run --frozen mypy apps/api/nex_api
uv run --frozen pytest -q apps/api/tests/test_ndsp_contract_preview.py
uv run --frozen python scripts/export-m1-openapi.py --check
```

There are no live NDSP requests in CI and **no** deployment or merge workflow.
