# M2-B L8 — Proposed subject-bound authority proof (TEST ONLY)

This is a development-only, synthetic CI proof stacked on Draft PR #10. NO production NDSP source, HTTP adapter, real session, live 9091 entitlement, customer decision, operational API route, trading or deployment is used or authorized.

## Reviewed canonical NDSP source facts

- Canonical auth service 9020 exposes /api/auth/session and validates session/JWT; it returns a user record. The inspected session route is NOT a sufficient active-account authorization guarantee, so L7 explicitly checks user.status against active/approved/verified.
- Entitlement authority 9091 fetches that 9020 session internally and checks the account before generating its plan/feature response; its public response declares NDSP_CANONICAL_ENTITLEMENT_9091_V1 but does NOT cryptographically expose a binding to the canonical user.id or request. Its public entitlement is NOT a source of ownership.
- Separate staging gateway 9192 uses auth/session on 9001 rather than 9020. No verified equivalence has been established between the routes.
- CDS source bootstrap lacks owner_user_id / tenant_id in the inspected decision table; the presence of an independent operational ownership ledger remains unverified. Existing by-ID GET lacks publication/visibility filtering. Do not connect it directly to NEX.

## L8 test-only proposal

A NEW separately trusted, ephemeral **test attester** signs a request-bound, nonce-bound EdDSA JWT containing:
- exact source SYSTEM and test-only environment
- canonical 9020 session and 9091 entitlement authority identity
- canonical user subject UUID
- original CD decision ID and read-only scope
- SHA-256 hashes of verified session and entitlement snapshots (NO raw token)
- a server-generated 24-byte random nonce and restricted 30-second validity
- strict issuer, audience, schema, type and field allowlists

Independent NEX Python code validates this pinned test signature and subject, claimed route, exact session/entitlement snapshots, nonce, read-only scope and expiry BEFORE calling the existing L7 owner+sealed-source verification gate. It supplies the SAME cached trusted session/entitlement snapshots to L7 to prevent read-after-recheck inconsistency. Rejects active-user status failures, forged or unrelated subjects, 9001 substitution, wrong tenant owner, expired/stale/replayed nonce, no rights and tampered signed decisions. The output remains original synthetic signed NDSP-NEX-1.0, BLOCKED/FLAT and execution_authorized=False.

## Explicit limitations / release blockers

1. There is **no actual bound 9091 claim or production attester**. This RFC prototype cannot demonstrate live subject binding or replace NDSP's existing authentication authority. Production would need independently designed and certified server-side signed assertion or transactional authenticated internal adapter; never accept a client-signed entitlement proof.
2. No live user/tenant/CDS ownership binding exists here. Synthetic ownership fixture is separately supplied from test code only.
3. No assurance for 9001-versus-9020 route equivalence, session consistency, prevention of privilege changes after attestation, genuine entitlement version, or production issuer trust, rotation and revocation.
4. No live CDS source or approved production signing evidence is tested or retrieved. Source versioning and KMS/IdP need independent security governance.
5. Do not merge Draft PRs #1–#11 (this PR), deploy source changes, enable any NEX trade/paper/live order, or expose existing CDS routes.

**Gate: test-only proof may PASS; REAL NDSP-NEX READ-ONLY BINDING and all trading remain NO-GO.**
