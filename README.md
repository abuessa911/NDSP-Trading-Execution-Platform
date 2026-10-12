# NEX Trading Execution Platform

NEX is a new, standalone foundation for a future decision-driven trading
execution platform. It is independent of NDSP. The NEX Master Specification is
the engineering source of truth; the NDSP platform report is product vision only.

M0 Architecture Freeze and M1 Foundation are the only in-scope milestones for
this build. No Binance integration, paper execution engine, or real-money
trading is included.

## Safety configuration

The application is restricted to:

```dotenv
TRADING_MODE=paper
LIVE_TRADING_ENABLED=false
GLOBAL_KILL_SWITCH=true
BINANCE_ALLOW_WITHDRAW=false
```

The API must refuse to start if any value is unsafe. No exchange order endpoint
or Binance credentials are part of M1.

## Architecture and references

- `docs/architecture/M0-architecture-freeze.md` — frozen M0 decisions and phase
  boundaries.
- `docs/reference/MASTER_SPECIFICATION_V1.docx` — authoritative engineering
  specification.
- `docs/reference/NDSP_PRODUCT_VISION.docx` — product vision and requirements
  reference only.
- `threat_model.md` — M0 threat model and M1 security guarantees.

## M1 repository

```text
apps/api/nex_api/            FastAPI control API
apps/api/migrations/         versioned Alembic migrations
apps/api/tests/              auth, safety, secrets, health, tenancy tests
infra/postgres/init/         least-privilege runtime/migration roles
infra/nginx/                 portable API gateway
docs/architecture/           M0 decisions
docs/reference/              original source documents
```

## Local development

Python 3.12 is required. Install the locked dependencies with `uv sync`, then:

```bash
PYTHONPATH=apps/api uv run uvicorn nex_api.main:app --reload
PYTHONPATH=apps/api uv run pytest
PYTHONPATH=apps/api uv run ruff check apps/api
PYTHONPATH=apps/api uv run mypy apps/api/nex_api
```

The liveness endpoint works without external services. Readiness and protected
routes remain unavailable until PostgreSQL, Redis, and a real OIDC issuer are
configured. M1 does not include a development-auth bypass.

## Docker deployment

The approved Next.js console migration is documented in
[`docs/M1_CONSOLE.md`](docs/M1_CONSOLE.md). It uses static export and the existing
FastAPI authentication/session endpoints, not a second authentication server.
The original API-only Compose deployment remains unchanged. The optional
`infra/console/compose.console.yml` overlay packages the console into the gateway.
No production deployment or M1 acceptance is implied.

Copy `.env.example` to `.env` and supply unique values through a secret manager.
The database URLs must use `nex_app` for the API and `nex_migrator` for Alembic.
Set `REDIS_URL` to the authenticated Redis instance and provide the exact
OIDC issuer, audience, and JWKS URL for the trusted identity provider.

```bash
docker compose build
docker compose --profile tools run --rm migrate
docker compose up -d
```

The gateway exposes `/api/*` and authenticated `/admin/*` on `NEX_HTTP_PORT` (default 8080). TLS
termination belongs in the deployment ingress. The initial `nex_bootstrap`
PostgreSQL role is used only to initialize the database; the API uses the
non-owner `nex_app` role and migrations use `nex_migrator`.

Provision the first tenant owner only after the OIDC provider and migrations are
ready:

```bash
set -a
. ./.env
set +a
docker compose --profile tools run --rm bootstrap \
  --issuer "$OIDC_ISSUER" \
  --subject "<verified OIDC subject>" \
  --tenant-name "<tenant name>" \
  --email "<verified email>" \
  --role USER
```

The bootstrap service uses the migration/operator database role only for this
one-off operation. It creates one tenant and directly tenant-owned user with an
explicit email/role and records an audit event. Administrative roles are denied
until provider MFA assurance is genuinely established; an `amr` claim alone is
not accepted as that assurance.
There is no hardcoded administrator, seeded user, or password login.

See `docs/architecture/M0-architecture-freeze.md` for the frozen M1 design and
phase exclusions. Never place real credentials in the repository.

## M1 remediation acceptance

**M1 NOT ACCEPTED.** See `M1_REMEDIATION_REPORT.md` and
`M1_FINAL_EVIDENCE_REPORT.md`. Login/logout return explicit HTTP 501 requirements:
bearer validation does not implement provider login or revoke tokens. No M2
work is authorized.

Alembic is the sole migration authority. `MIGRATION_DATABASE_URL` is required
explicitly and must use `nex_migrator`; runtime fallback and Drizzle pushes are
disabled. The upgrade refuses populated legacy identities until approved
tenant/email/role mappings exist, and preserves historical audit separately.
Never use autogeneration to drop the retained `audit_events_legacy` table.

For mounted-file delivery, select `SECRET_PROVIDER=file` and explicitly mount
`DATABASE_URL`, `MIGRATION_DATABASE_URL` (operator tools only), and `REDIS_URL`
files beneath `/run/secrets` using a deployment-specific Compose override or
secret manager. Missing files do not fall back to ambient environment URLs.
Do not mount migration credentials in the runtime API.

The runtime role may only read its validated identity projection and tenant,
and may insert but not mutate audit. Operator audit reads remain tenant-scoped;
unknown-identity security events use a reserved disabled security tenant that
the runtime cannot read. RLS assumes a trusted API role: a compromised runtime
connection can set its own context variables; it is not a DBA-proof boundary.

Explicit isolated verification (synthetic credentials and local test JWKS only):

```bash
uv run python scripts/verify-m1-compose.py
NEX_M1_POSTGRES_TEST=isolated uv run pytest apps/api/tests
uv run python scripts/export-m1-openapi.py --check
pnpm --filter @workspace/api-spec run codegen
pnpm run typecheck
```

The verifier refuses existing test containers rather than erasing evidence.
`--down` deletes only its explicitly named isolated test volumes; preserve
evidence before using it. An unsuccessful Compose startup is not acceptance,
even if native PostgreSQL checks pass.