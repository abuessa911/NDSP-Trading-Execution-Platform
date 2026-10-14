#!/usr/bin/env bash
# M2-B L7: synthetic canonical-session/entitlement/owner/read acceptance.
# No real auth tokens, production NDSP HTTP, API routes, DBs or trading.
set -Eeuo pipefail
trap 'echo "M2B_L7_READ_GATE_FAILED at line $LINENO" >&2' ERR
if [[ "$CI" != "true" || "$GITHUB_ACTIONS" != "true" ]]; then
  echo "REFUSE_L7_OUTSIDE_GITHUB_CI" >&2; exit 70
fi
cd "$(cd -- "$(dirname -- "$0")/.." && pwd)"
uv sync --frozen
uv run --frozen ruff check \
  apps/api/nex_api/ndsp_canonical_read_gate_l7_preview.py \
  apps/api/tests/test_ndsp_l7_canonical_read_gate_preview.py
uv run --frozen mypy apps/api/nex_api
uv run --frozen pytest -q \
  apps/api/tests/test_ndsp_l7_canonical_read_gate_preview.py \
  apps/api/tests/test_ndsp_l3_readonly_authorization_gate.py
uv run --frozen python scripts/export-m1-openapi.py --check
echo 'M2B_L7_CANONICAL_IDENTITY_SOURCE_OWNER_GATE=PASS'
