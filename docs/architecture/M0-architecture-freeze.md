# M0 Architecture Freeze

**Status:** Frozen for M1  
**Authority:** `docs/reference/MASTER_SPECIFICATION_V1.docx`  
**Product reference:** `docs/reference/NDSP_PRODUCT_VISION.docx`

## Document precedence

The NEX Master Specification is the engineering source of truth. The NDSP Trading
Execution Platform report is product vision and requirements context only. If they
conflict, the Master Specification wins.

## System boundary

NEX is a new, independently operated project with its own repository, PostgreSQL
database, secrets, deployment, audit domain, and release cycle. It does not connect
to or modify the existing NDSP platform in M0 or M1.

NDSP remains an external decision-support system. A future NEX integration may
consume only the signed, versioned `NDSP-NEX-1.0` decision contract over a
read-only boundary. Protected NMP/TDL formulas, source code, thresholds, and
internal logic are out of scope and must not be copied or reimplemented.

## Frozen M1 architecture

- **Application:** FastAPI/Python control API, structured as a modular monolith.
  Future workers may be split out only at the documented module and contract
  boundaries.
- **Persistence:** NEX-owned PostgreSQL, with Alembic migrations. Use UUIDs,
  timezone-aware UTC timestamps, and `NUMERIC` for financially meaningful values.
- **Coordination:** NEX-owned Redis service in Docker Compose. M1 does not enqueue
  trading or exchange work.
- **Identity:** Provider-neutral OIDC JWT validation using configured issuer,
  audience, and JWKS URL. No Replit Auth or Replit-managed auth dependency is used.
  Unknown identities are denied until explicitly provisioned into a tenant.
- **Tenancy:** Every user-owned record is tenant-scoped. Tenant identity is
  resolved server-side from the authenticated subject's active membership; a
  client-supplied tenant identifier never grants access.
- **Secrets:** A `SecretProvider` boundary supports deployment-injected environment
  values and mounted Docker secret files. M1 has no exchange-credential fields or
  credential write API. Future stored exchange credentials require a KMS/Vault
  envelope-encryption adapter before that feature is introduced.
- **Audit:** Material security and administrative events are durable, tenant-scoped,
  append-only records. There is no application update/delete operation for audit
  evidence.
- **Packaging:** Standard Dockerfiles and Docker Compose for API, PostgreSQL, and
  Redis. Runtime configuration uses ordinary environment variables and mounted
  secrets; production code does not depend on Replit APIs, connectors, storage, or
  deployment services.

## Safety invariants

The initial runtime configuration is fixed to:

```dotenv
TRADING_MODE=paper
LIVE_TRADING_ENABLED=false
GLOBAL_KILL_SWITCH=true
BINANCE_ALLOW_WITHDRAW=false
```

M1 contains no Binance client, exchange credential model, order endpoint, paper
execution engine, or live-trading implementation. Startup rejects an unsafe mode
or a changed safety flag. Health endpoints do not expose credentials or user data.

## M1 scope

M1 implements repository and CI foundations, real OIDC token validation, tenant
and user membership, database migrations, a secrets-provider abstraction,
append-only audit, and liveness/readiness health checks.

M1 explicitly excludes Binance read-only integration (M2), paper execution (M3),
risk engine (M4), testnet order writes (M5), shadow mode (M6), and controlled live
trading (M8). No phase may be skipped.

## M0 exit decision

- Master Specification is retained as the authoritative project reference.
- The NDSP/NEX trust boundary and protected-algorithm boundary are frozen above.
- The architecture uses portable interfaces and a Docker deployment, not
  Replit-specific production services.
- No unresolved critical architecture choice blocks M1. The identity provider is
  intentionally an OIDC configuration, not a hard dependency on one vendor.