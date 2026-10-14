#!/usr/bin/env bash
# M2-B L8: synthetic-only signed subject+entitlement binding acceptance.
# Refuses to run outside GitHub Actions. NO real NDSP/IdP/CDS, orders or keys.
set -Eeuo pipefail
trap 'echo "M2B_L8_ACCEPTANCE_FAIL line $LINENO" >&2' ERR
if [[ "$CI" != "true" || "$GITHUB_ACTIONS" != "true" ]]; then
  echo 'REFUSE_L8_OUTSIDE_GITHUB_CI' >&2
  exit 70
fi
cd "$(cd -- "$(dirname -- "$0")/.." && pwd)"
uv sync --frozen
uv run --frozen ruff check \
 apps/api/nex_api/ndsp_subject_bound_read_l8_preview.py \
 apps/api/tests/test_ndsp_l8_subject_bound_read_preview.py \
 apps/api/nex_api/ndsp_canonical_read_gate_l7_preview.py
uv run --frozen mypy apps/api/nex_api
uv run --frozen pytest -q \
 apps/api/tests/test_ndsp_l8_subject_bound_read_preview.py \
 apps/api/tests/test_ndsp_l7_canonical_read_gate_preview.py
uv run --frozen python scripts/export-m1-openapi.py --check
echo 'M2B_L8_SUBJECT_BINDING_SYNTHETIC_GATE=PASS'
