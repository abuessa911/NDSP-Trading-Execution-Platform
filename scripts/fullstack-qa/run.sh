#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
QA="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$QA/../.." && pwd)"
cd "$QA"
mkdir -p results
npm ci --ignore-scripts --no-audit --no-fund
npx playwright install chromium
status=0
npm test || status=1
npm run test:api || status=1
if [[ -n "${QA_PYTHON:-}" && -x "$QA_PYTHON" ]]; then
 cd "$ROOT"
 "$QA_PYTHON" -m pytest -q apps/api/tests/test_contract.py apps/api/tests/test_hunter_usdm_current_contract.py apps/api/tests/test_ndsp_contract_preview.py apps/api/tests/test_health.py apps/api/tests/test_browser_auth.py apps/api/tests/test_hunter_execution_safety_v1.py apps/api/tests/test_hunter_transport_guard_v1.py apps/api/tests/test_hunter_emergency_stop_v1.py apps/api/tests/test_tenant_isolation.py --junitxml="$QA/results/backend.xml" || status=1
else
 echo 'BACKEND=BLOCKED: set QA_PYTHON to the existing test interpreter.'
 status=1
fi
printf 'Read-only public smoke scope; authenticated journeys, production persistence and telemetry delivery require separate evidence.\n'
exit "$status"
