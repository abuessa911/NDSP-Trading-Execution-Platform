#!/usr/bin/env bash
# M2-B L3: synthetic-only source authorization readiness gate.
# Run in isolated GitHub Actions ONLY. No real NDSP data or trading.
set -Eeuo pipefail
trap 'echo "M2B_L3_GATE_FAIL: line $LINENO" >&2' ERR
if [[ "$CI" != "true" || "$GITHUB_ACTIONS" != "true" ]]; then
  echo 'REFUSE_L3_OUTSIDE_GITHUB_CI' >&2
  exit 70
fi
root="$(cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$root"
uv sync --frozen
uv run --frozen ruff check \
  apps/api/tests/test_ndsp_l3_readonly_authorization_gate.py \
  apps/api/nex_api/ndsp_contract_preview.py \
  apps/api/nex_api/ndsp_source_binding_preview.py \
  apps/api/nex_api/ndsp_identity_ledger_l2_preview.py
uv run --frozen mypy apps/api/nex_api
uv run --frozen pytest -q \
  apps/api/tests/test_ndsp_l3_readonly_authorization_gate.py \
  apps/api/tests/test_ndsp_source_binding_preview.py \
  apps/api/tests/test_ndsp_identity_ledger_l2_preview.py
uv run --frozen python scripts/export-m1-openapi.py --check
echo 'M2B_L3_SYNTHETIC_PRODUCTION_DENIAL_GATE=PASS'
