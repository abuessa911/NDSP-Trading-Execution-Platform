# Threat Model

## Project Overview

NEX is an independent foundation for a future multi-tenant trading execution
platform. M1 provides an authenticated control API, tenant isolation, PostgreSQL
persistence, Redis coordination, audit evidence, health checks, and portable
Docker deployment. It does not yet integrate with NDSP, Binance, or any trading
engine. The Master Specification is authoritative; the NDSP report is product
vision only.

## Assets

- **OIDC access tokens and identity subjects** — token theft or weak validation
  could impersonate a tenant member.
- **Tenant, user, and membership records** — cross-tenant disclosure or role
  escalation would expose future financial data.
- **Audit events** — alteration or deletion would remove evidence of access and
  administrative actions.
- **Database and deployment secrets** — compromise could expose tenant data or
  later integrations.
- **Safety configuration** — changing the paper-only mode or global stop could
  violate the approved release gate. M1 must fail closed if these values are
  unsafe.

## Trust Boundaries

- **Client to API:** Client input and identity claims are untrusted until validated
  by OIDC signature, issuer, audience, expiry, and server-side membership checks.
- **API to PostgreSQL:** Queries must be parameterized and tenant-scoped. Audit
  writes are append-only.
- **API to Redis:** Redis is a coordination/cache boundary only in M1; its data is
  not an authorization source.
- **API to identity provider:** JWKS and issuer metadata come from configured
  OIDC endpoints and must be fetched over TLS with bounded timeouts.
- **NEX to NDSP:** No connection exists in M1. A future integration is read-only
  and accepts only the signed/versioned contract; it must not mutate NDSP or copy
  protected logic.
- **Development to deployment:** Local/test configuration is separate from
  deployment configuration. Unsafe trading flags prevent startup.

## Scan Anchors

- Production API entry point: `apps/api/` (FastAPI application and dependencies).
- Persistence and migrations: `apps/api` data models and Alembic migration package.
- Security-sensitive areas: OIDC validation, tenant resolution, secrets provider,
  and audit writer.
- Public surfaces: liveness/readiness health only. User and tenant endpoints
  require a validated OIDC identity and active membership.
- Dev/test fixtures are isolated from runtime modules and must never be enabled
  by production configuration.

## Threat Categories

### Spoofing

An attacker may forge a subject claim or replay an expired token. The API MUST
validate the token signature against the configured JWKS, issuer, audience,
expiry, and permitted algorithm. Unknown or unprovisioned subjects MUST be
rejected; development fixtures MUST NOT be accepted by production settings.

### Tampering

An attacker may supply a different tenant ID, role, or resource identifier.
Tenant identity and roles MUST be derived from active database membership, not
from caller-supplied authorization fields. All body, path, and query input MUST
be validated, and database queries MUST use parameterized values.

### Repudiation

A user or operator may deny a security- or tenant-management action. Such actions
MUST append an audit record containing actor, tenant, action, target, outcome, and
UTC timestamp. The application MUST NOT expose update/delete operations for audit
records.

### Information Disclosure

Cross-tenant queries, token logging, stack traces, or secret values in API
responses could expose protected data. Authenticated queries MUST be tenant
scoped. Tokens and secret values MUST be redacted from logs and responses. Health
responses MUST contain only operational status.

### Denial of Service

Unauthenticated traffic or expensive identity-provider calls could exhaust API,
database, or Redis capacity. Health and auth routes MUST use bounded request
sizes/timeouts; JWKS retrieval MUST be cached with bounded refresh behavior; the
service MUST fail closed when identity validation or required persistence is
unavailable.

### Elevation of Privilege

An ordinary member could attempt administrative actions or switch tenants.
Authorization MUST be enforced server-side on every protected operation, with
roles and tenant membership loaded from the database. Administrative identities
must be explicitly provisioned; there is no default or hardcoded administrator.