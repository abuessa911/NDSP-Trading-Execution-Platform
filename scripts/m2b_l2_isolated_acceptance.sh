#!/usr/bin/env bash
# M2-B L2 acceptance: GitHub CI + disposable localhost postgres ONLY.
# Does not mutate production, merge PRs, access NDSP or enable trading.
set -Eeuo pipefail
IFS=$'\n\t'
trap 'echo "M2B_L2_ACCEPTANCE_FAILED at line $LINENO" >&2' ERR

[[ "$CI" == "true" && "$GITHUB_ACTIONS" == "true" ]] || {
  echo "REFUSE_L2_TEST_OUTSIDE_GITHUB_ACTIONS"; exit 70;
}
[[ "$M2B_L2_ADMIN_DSN" == \
'postgresql://m2b_fixture:synthetic-m2b-admin-only@127.0.0.1:5432/nex_m2b_preview' ]] || {
  echo "REFUSE_L2_UNAPPROVED_DATABASE"; exit 71;
}

repo_root="$(cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$repo_root"
echo "=== L2 static lint and type checks ==="
uv sync --frozen
uv run --frozen ruff check \
  apps/api/nex_api/ndsp_identity_ledger_l2_preview.py \
  apps/api/tests/test_ndsp_identity_ledger_l2_preview.py
uv run --frozen mypy apps/api/nex_api
echo "=== L2 issuer signature and isolated PostgreSQL checks ==="
uv run --frozen pytest -q \
  apps/api/tests/test_ndsp_identity_ledger_l2_preview.py
echo "=== M1 contract freeze ==="
uv run --frozen python scripts/export-m1-openapi.py --check
echo "M2B_L2_SYNTHETIC_ONLY_ACCEPTANCE=PASS"
