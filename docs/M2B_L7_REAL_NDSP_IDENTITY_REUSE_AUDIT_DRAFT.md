# NDSP → NEX M2-B L7 — Real identity reuse audit and test-only read boundary

Classification: SOURCE INSPECTION + SYNTHETIC CI. NOT an approved connection.
Status: M2-B L7 Draft. Keep PR #1 through this PR Draft and unmerged.

## Canonical Contabo source review (read-only)
Server: vmi2934783; canonical source root: /home/ndsp/empire-core-v5-1-1-clean.
Verified by read-only source inspection, not requests against live user sessions:
- backend/auth_api/ndsp_entitlement_authority_9091.cjs: GET /api/entitlements/me, whose upstreamSession() calls GET http://127.0.0.1:9020/api/auth/session using incoming cookie/authorization. It checks a canonical UUID user.id, then fetches user account status and plan; its public JSON includes authority NDSP_CANONICAL_ENTITLEMENT_9091_V1 and entitlement object.
- The 9091 entitlement JSON inspected does NOT include a proof binding the response to subject user.id; it relies on the upstream caller session. A separate authenticated subject check and source ownership record are mandatory before exposing decisions.
- backend/auth_api/ndsp_quality_live_entitlement_gateway_9192.cjs uses GET http://127.0.0.1:9001/api/auth/session and 9091 entitlement endpoint for another gate. The 9001 vs 9020 session routing must be independently certified as equivalent before any true identity adapter is chosen.
- backend/auth_api/ndsp_quality_live_authenticated_boundary_candidate_v1.cjs is an isolated candidate that orders session -> entitlement -> assignment -> quality evidence; it must NOT be assumed to be production-active.
- backend/services/completed_decision/main.cjs: CD-... text source decision IDs, no tenant_id or owner_user_id column in the inspected bootstrap schema, nullable expiry, by-ID read SELECT * WHERE decision_id=$1 without Published/public SQL condition. It is NOT an acceptable public exporter. No actual DB schema or user records were inspected, so independently stored decision ownership is UNVERIFIED, not disproved.

## Implemented L7 isolated prototype in NEX
- Dependency-injected pure async Python gate (NO HTTP listener or real NDSP calls).
- Test mock for session resembles {ok:true,user:{id:<canonical UUID>}}; entitlement mock contains exact 9091 authority name; ownership mock is a separate trusted server-side authority with source_decision_id, canonical owner_user_id, tenant_id, Published/public and source context.
- Reuses pinned *synthetic* Ed25519 source signer public key from L4; rejects any signed envelope with wrong key/signature, expired or mismatched context and any state other than BLOCKED/FLAT/test.
- Fail closed on missing/unknown session, **inactive or missing account status** (canonical session itself does not guarantee account activation), email-only identity, wrong owner, missing publication, mismatched symbol/timeframe, unentitled asset/timeframe, unknown selected-asset assignment, authority timeout, tampered signature, malformed credentials or explicit production context.
- Source metadata/owner binding is trusted ONLY because fixtures are injected server-side; there is currently no real CDS ownership authority. No tenant or role is derived from client headers or signature alone.
- Returns only previously signed synthetic envelope bytes; execution_authorized=False. Does not grant order permission or install a protected gateway.

## Mandatory production gates
1. Certify authoritative production authentication path (9001 vs 9020) and origin/subject guarantees. Do not accept client headers or independently forged JWTs.
2. Certify 9091 entitlement response is bound to the SAME session subject; either use a verified internal adapter or add a versioned, authenticated subject-binding claim/contract, with governance and compatibility review.
3. Source CDS must supply authoritative immutable decision owner and tenant linkage. Current inspected CDS table does not prove one. If a source decision is globally public by policy, explicitly define the authorized access policy instead of inventing tenant ownership.
4. Add publication/visibility/expiry policy, asset and timeframe entitlement and verified assignments; ensure no internal PII or protected TDL/NMP calculations are exposed.
5. Approve private authenticated read-only exporter and audit/rate-limit policy, CDS transactional issuer-version/migration, real KMS signing and public key rotation/revocation. Prove with independently issued staging decisions only after explicit authorization.
6. No live production NDSP or NEX integration, KMS changes, merging, deployment, or trading until separately authorized.

Production real-data gate: NO-GO. Test-only authorization proof is not real identity certification.
