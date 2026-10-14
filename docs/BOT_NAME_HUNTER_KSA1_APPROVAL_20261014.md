# Official bot name — hunter_ksa1 bot

**Decision:** user-approved name of the trading/execution bot is exactly
**hunter_ksa1 bot** (lowercase, underscore, digit 1, space, lowercase bot).

**Distinct system:** NDSP remains **NDSP**, the separate decision-support
platform. The bot is independent and still has no approved live integration.

## Historical context

- NEX was an internal provisional name for the standalone execution codebase.
- The original UI also used the working labels Hunter_KSA1 and NAWAF.
- Those are no longer the display brand. The console presents hunter_ksa1 bot.
- Do not confuse an engineering identifier with an approved public-facing name.

## Compatibility scope

Only the human-visible product identity is updated in this review:
console sidebar, top label, screen heading, browser metadata, preview copy,
basic descriptions, and repository README title.

The following remain unchanged, intentionally, until a separate reviewed
migration is authorized: repository name/URL, app workspace package names,
Python nex_api import paths, existing environment variable names, API route
paths, OIDC audiences, database roles and schemas, database migrations,
historical decision/source IDs (CD-...), NDSP-NEX-1.0 frozen contract and
signature canonicalization, existing Master Specification references, CI
trigger names, and audit histories.

Avoid global search-and-replace of NEX/NDSP in code: it can invalidate
signatures, persisted settings, URLs, tests and authentication assumptions.

## Acceptance and risk

- Official display name remains exactly hunter_ksa1 bot everywhere that
  user-facing console identity is assembled.
- No exposure of private developer names in the main console brand.
- No changed source files in canonical NDSP production on Contabo.
- No database, trade, live market or provider connectivity is added.
- Stacked Draft PR only; no merge or deployment authorization.
- Acceptance: node --test artifacts/ndsp-console/tests/branding.test.mjs.

**Separate future change:** a repository rename or migration of internal NEX
symbols requires its own dependency inventory, compatibility aliases,
migration/rollback and formal user approval.
