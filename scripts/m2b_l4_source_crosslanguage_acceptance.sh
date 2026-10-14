#!/usr/bin/env bash
# M2-B L4 NDSP-issued test vectors -> NEX disposable PostgreSQL acceptance.
# Runs only in GitHub Actions. No NDSP production requests, writes or orders.
set -Eeuo pipefail
trap 'echo "M2B_L4_ACCEPTANCE_ERROR: line $LINENO" >&2' ERR
[[ "$CI" == "true" && "$GITHUB_ACTIONS" == "true" ]] || {
  echo 'REFUSE_NON_CI_L4_RUN'; exit 70;
}
[[ "$M2B_L4_ADMIN_DSN" == \
"postgresql://m2b_fixture:synthetic-m2b-admin-only@127.0.0.1:5432/nex_m2b_preview" ]] || {
  echo 'REFUSE_NON_DISPOSABLE_POSTGRES'; exit 71;
}
root="$(cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$root"
uv sync --frozen
uv run --frozen ruff check \
  apps/api/tests/test_ndsp_l4_source_issuer_crosslanguage.py
uv run --frozen mypy apps/api/nex_api
uv run --frozen pytest -q \
  apps/api/tests/test_ndsp_l4_source_issuer_crosslanguage.py
uv run --frozen python scripts/export-m1-openapi.py --check
echo 'M2B_L4_CROSS_LANGUAGE_AND_DISPOSABLE_DB=PASS'
