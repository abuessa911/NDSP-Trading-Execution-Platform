#!/usr/bin/env bash
# NDSP-NEX M2-B L5: complete synthetic-only disposable acceptance.
# NO real NDSP connections, production credentials, deployments or trading.
set -Eeuo pipefail
trap 'echo "M2B_L5_ACCEPTANCE_FAILURE at line $LINENO" >&2' ERR
if [[ "$CI" != "true" || "$GITHUB_ACTIONS" != "true" ]]; then
  echo 'REFUSE_L5_OUTSIDE_GITHUB_ACTIONS' >&2
  exit 70
fi
expected='postgresql://m2b_fixture:synthetic-m2b-admin-only@127.0.0.1:5432/nex_m2b_preview'
if [[ "$M2B_L5_ADMIN_DSN" != "$expected" ]]; then
  echo 'REFUSE_L5_UNSAFE_POSTGRES_DSN' >&2
  exit 71
fi
root="$(cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$root"
uv sync --frozen
uv run --frozen ruff check \
 apps/api/nex_api/ndsp_source_export_l5_preview.py \
 apps/api/tests/test_ndsp_l5_source_export_preview.py
uv run --frozen mypy apps/api/nex_api
uv run --frozen pytest -q \
 apps/api/tests/test_ndsp_l5_source_export_preview.py \
 apps/api/tests/test_ndsp_l4_source_issuer_crosslanguage.py
uv run --frozen python scripts/export-m1-openapi.py --check
echo 'M2B_L5_DISPOSABLE_AUTH_SOURCE_LEDGER=PASS'
