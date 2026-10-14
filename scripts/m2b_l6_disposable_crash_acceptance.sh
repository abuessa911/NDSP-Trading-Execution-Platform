#!/usr/bin/env bash
# NDSP/NEX L6: COMPLETE disposable PostgreSQL cryptographic crash test.
# Runs ONLY on GitHub Actions using a fixed synthetic database.
# NO production credentials, real CDS/API clients, PM2, migrations or orders.
set -Eeuo pipefail
trap 'echo "M2B_L6_FAIL_CLOSED at line $LINENO" >&2' ERR
[[ "$CI" == "true" && "$GITHUB_ACTIONS" == "true" ]] || {
  echo 'REFUSE_L6_OUTSIDE_CI'; exit 70;
}
expected='postgresql://m2b_fixture:synthetic-m2b-admin-only@127.0.0.1:5432/nex_m2b_preview'
[[ "$M2B_L6_ADMIN_DSN" == "$expected" ]] || {
  echo 'REFUSE_L6_UNSAFE_DATABASE'; exit 71;
}
cd "$(cd -- "$(dirname -- "$0")/.." && pwd)"
echo '=== Lock dependencies, static lint and typecheck ==='
uv sync --frozen
uv run --frozen ruff check \
 apps/api/nex_api/ndsp_source_issuer_l6_preview.py \
 apps/api/tests/test_ndsp_l6_crash_recovery_issuer_preview.py
uv run --frozen mypy apps/api/nex_api
echo '=== Publisher reserve/reconnect/seal and strict tenant RBAC ==='
uv run --frozen pytest -q apps/api/tests/test_ndsp_l6_crash_recovery_issuer_preview.py
echo '=== Historical M1 OpenAPI frozen ==='
uv run --frozen python scripts/export-m1-openapi.py --check
echo 'M2B_L6_ISOLATED_ISSUER_RECOVERY_ACCEPTANCE=PASS'
