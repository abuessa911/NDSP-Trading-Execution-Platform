# NDSP + HUNTER verification — 2026-10-29

Scope: new tests and CI only. Existing source changes and production services are preserved.
Rollback: remove only the new scripts/fullstack-qa directory and .github/workflows/fullstack-qa.yml; no runtime rollback required.
No production database writes or exchange order calls were made.

## Executed evidence
- Browser: 8 passed, desktop/mobile, real public navigation and UI controls.
- Newman: 5 assertions passed across 3 public requests.
- Bot API selected health/authentication/execution safety tests: 69 passed.
- Existing backend contract gate: 55 passed; overall gate FAIL.
- Source/deployed routes: 65/67; missing response models: 29/31.
- Deployed-only routes: GET /api/v1/market-source/quote and GET /api/v1/market-source/sources.
- These are partial smoke tests, not complete button or application coverage.
- Authenticated journeys and real application persistence are NOT VERIFIED.

## Reproduce
Run:
QA_PYTHON=/srv/hunter-ksa1-api-public/.venv/bin/python bash scripts/fullstack-qa/run.sh

When using an already installed Chromium:
export QA_CHROMIUM=/root/.cache/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell
The public browser tests forbid all HTTP writes and external hosts.
Public credentials in the UI test are synthetic form inputs; no account is submitted or created.
HTML and JUnit reports are in results/ and must not be committed.
Screenshots use test-results/ and must not contain authenticated sessions.

## Existing database acceptance
The new workflow reuses scripts/ci-m1-compose.py with a uniquely named disposable project.
It verifies actual PostgreSQL/Redis/API behavior and performs scoped cleanup.
Docker is absent on the production server, so this job has NOT been executed there.
It is intended for a GitHub-hosted runner with Docker, never for the production database.

## Observability blockers
Sentry and OpenTelemetry SDKs were not installed in the inspected bot API interpreter.
No SENTRY/OTEL setting names were present in the inspected bot root environment file.
This does not prove absence from every service environment.
NDSP's canonical telemetry.py defines attributes only; this is not proof of SDK instrumentation/export.
No real Sentry event delivery, trace export or frontend-to-database trace correlation is certified.
Required: correct Sentry project configuration, OTLP collector destination, governed source instrumentation,
an isolated authenticated test account and a test-data cleanup policy.
Do not insert DSNs, auth tokens, cookies or private keys into this report or Git.

## Source control
The server NDSP root is not a Git checkout.
The bot server branch has uncommitted changes and was not found as an identically named remote branch.
The tested working tree differs from committed source; a hosted run cannot certify those uncommitted changes.
GitHub workflow presence on disk alone does not mean GitHub Actions is enabled or has run.
