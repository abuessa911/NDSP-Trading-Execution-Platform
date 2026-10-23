#!/usr/bin/env bash
# Hunter KSA1 source/deployment verification. Read-only, with evidence.
# Does NOT publish, restart services, alter NDSP, grant roles or enable trading.
set -Eeuo pipefail
umask 077
ROOT=/opt/hunter_ksa1-bot
WEB=/srv/hunter-ksa1-preview/out
API=/srv/hunter-ksa1-api-public/nex_api
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EVID="$ROOT/docs/source-release-verification-$STAMP"
mkdir -p "$EVID"
cd "$ROOT"
export PATH="/root/.ndsp-remote-node/node_modules/node/bin:/root/.local/share/pnpm/bin:$PATH"
exec 9>/run/lock/hunter-source-release-verification.lock
flock -n 9 || { echo "ANOTHER_VERIFICATION_RUNNING"; exit 16; }
echo "UTC=$(date -u +%FT%TZ)" | tee "$EVID/results.txt"
fail() { printf 'FAIL %s\n' "$1" | tee -a "$EVID/results.txt"; exit 1; }
ok() { printf 'PASS %s\n' "$1" | tee -a "$EVID/results.txt"; }
[ "$(hostname -s)" = vmi2934783 ] || fail HOST
for unit in hunter-ksa1-preview hunter-ksa1-gateway hunter-ksa1-api-public-candidate hunter-ksa1-keycloak-public-staging hunter-ksa1-redis; do
  systemctl is-active --quiet "$unit" || fail "service:$unit"
done
ok HUNTER_SERVICES
for expected in 'TRADING_MODE=paper' 'LIVE_TRADING_ENABLED=false' 'GLOBAL_KILL_SWITCH=true' 'BINANCE_ALLOW_WITHDRAW=false'; do
  grep -qx "$expected" /etc/hunter-ksa1-identity/public-api.env || fail "TRADING_FAIL_CLOSED"
done
ok TRADING_FAIL_CLOSED
test -f artifacts/ndsp-console/out/admin/owner-guide/index.html || fail BUILD_MISSING
if find artifacts/ndsp-console/src -type f \( -name '*.tsx' -o -name '*.ts' -o -name '*.css' \) \
   -newer artifacts/ndsp-console/out/user-guide/index.html | grep -q .; then fail SOURCE_NEWER_THAN_BUILD; fi
ok SOURCE_BUILD_FRESH
rsync -rcni --delete artifacts/ndsp-console/out/ "$WEB/" > "$EVID/static-diff.txt"
[ ! -s "$EVID/static-diff.txt" ] || fail SOURCE_PUBLISHED_MISMATCH
ok BUILT_PUBLISHED_CHECKSUMS
for file in main.py routes/auth.py routes/trading_profile.py; do
  cmp -s "apps/api/nex_api/$file" "$API/$file" || fail "BACKEND_SOURCE_MISMATCH:$file"
done
ok BACKEND_SOURCE_PUBLISHED
PYTHONPATH=apps/api .venv-qa/bin/pytest -q apps/api/tests > "$EVID/backend-tests.log" 2>&1 || fail BACKEND_TESTS
ok BACKEND_TESTS
pnpm --filter @workspace/ndsp-console test > "$EVID/frontend-tests.log" 2>&1 || fail UI_TESTS
ok UI_TESTS
pnpm --filter @workspace/ndsp-console typecheck > "$EVID/types.log" 2>&1 || fail TYPECHECK
ok TYPECHECK
curl -fsS --max-time 9 http://127.0.0.1:19486/api/health/ready |
  python3 -c 'import sys,json; c=json.load(sys.stdin)["components"]; assert c=={"database":"ready","redis":"ready","oidc":"ready"}' || fail API_READINESS
ok API_READINESS
for path in /strategies/ /user-guide/ /admin/owner-guide/ /trading/; do
  [ "$(curl -sS --max-time 7 -o /dev/null -w '%{http_code}' "http://127.0.0.1:19344$path")" = 200 ] || fail "LOCAL:$path"
  [ "$(curl -skS --max-time 7 -o /dev/null -w '%{http_code}' "https://bot.ndsp.app$path")" = 401 ] || fail "PUBLIC_GATE:$path"
done
ok UI_ROUTES_AND_GATE
[ "$(curl -skS --max-time 7 -o /dev/null -w '%{http_code}' https://ndsp.app/)" = 200 ] || fail NDSP_BASELINE
ok NDSP_BASELINE
printf '\nTEST_SUMMARIES\n' >> "$EVID/results.txt"
tail -n 1 "$EVID/backend-tests.log" >> "$EVID/results.txt"
grep -E '^. (tests|pass|fail)' "$EVID/frontend-tests.log" | tail -n 3 >> "$EVID/results.txt" || :
echo 'OTHER_TOOLS_SCHEDULED_TASKS_ARE_NOT_CERTIFIED_BY_THIS_SCRIPT' >> "$EVID/results.txt"
printf "VERIFIED_SOURCE_DEPLOY_PASS\nEVIDENCE=%s\n" "$EVID"
