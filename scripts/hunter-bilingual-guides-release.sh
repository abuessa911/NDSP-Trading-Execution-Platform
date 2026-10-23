#!/usr/bin/env bash
# Hunter-only source-based static UI release (including verified market outputs).
set -Eeuo pipefail
umask 077
ROOT=/opt/hunter_ksa1-bot
OUT="$ROOT/artifacts/ndsp-console/out"
PUBLIC=/srv/hunter-ksa1-preview
EVID="$ROOT/docs/hunter-live-outputs-20261017"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
STAGE="$PUBLIC/out-guide-stage-$STAMP"
BEFORE="$PUBLIC/out-before-bilingual-guides-$STAMP"
exec 9>/run/lock/hunter-bilingual-guide-release.lock
flock -n 9 || { echo "Another guide release is in progress"; exit 11; }
[ "$(id -u)" -eq 0 ] && [ "$(hostname -s)" = vmi2934783 ] || exit 12
grep -q 'pass 37' "$EVID/ui-tests.log"
grep -q '38/38' "$EVID/build.log"
test -f "$OUT/strategies/index.html"
test -f "$OUT/user-guide/index.html"
test -f "$OUT/admin/owner-guide/index.html"
systemctl is-active --quiet hunter-ksa1-preview
systemctl is-active --quiet hunter-ksa1-gateway
systemctl is-active --quiet hunter-ksa1-api-public-candidate
grep -qx 'LIVE_TRADING_ENABLED=false' /etc/hunter-ksa1-identity/public-api.env
grep -qx 'GLOBAL_KILL_SWITCH=true' /etc/hunter-ksa1-identity/public-api.env
grep -qx 'BINANCE_ALLOW_WITHDRAW=false' /etc/hunter-ksa1-identity/public-api.env
echo "SOURCE_38_PAGES_AND_37_UI_TESTS_PASS"
test ! -e "$STAGE" && test ! -e "$BEFORE"
cp -a "$PUBLIC/out" "$STAGE"
rsync -rlt --delete --no-perms --no-owner --no-group "$OUT/" "$STAGE/"
chmod -R u=rwX,go=rX "$STAGE"
for page in strategies user-guide admin/owner-guide trading account-access markets; do
  runuser -u www-data -- test -r "$STAGE/$page/index.html"
done
# Preserve rollback; swap only static bot UI, no services restarted.
mv "$PUBLIC/out" "$BEFORE"
if ! mv "$STAGE" "$PUBLIC/out"; then mv "$BEFORE" "$PUBLIC/out"; exit 20; fi
failed=0
for page in /strategies/ /user-guide/ /admin/owner-guide/ /trading/ /account-access/ /markets/; do
  if [ "$(curl -sS --max-time 7 -o /dev/null -w '%{http_code}' "http://127.0.0.1:19344$page")" != 200 ]; then failed=1; fi
done
for page in /strategies/ /user-guide/ /admin/owner-guide/ /trading/ /markets/; do
  cmp -s "$OUT/$page/index.html" "$PUBLIC/out/$page/index.html" || failed=1
  test "$(curl -skS --max-time 7 -o /dev/null -w '%{http_code}' "https://bot.ndsp.app$page")" = 401 || failed=1
done
test "$(curl -skS --max-time 7 -o /dev/null -w '%{http_code}' https://ndsp.app/)" = 200 || failed=1
curl -fsS --max-time 8 http://127.0.0.1:19486/api/health/ready |
  python3 -c 'import sys,json;d=json.load(sys.stdin);assert d["components"]=={"database":"ready","redis":"ready","oidc":"ready"}' || failed=1
if [ "$failed" -ne 0 ]; then
  mv "$PUBLIC/out" "$PUBLIC/out-failed-guides-$STAMP"
  mv "$BEFORE" "$PUBLIC/out"
  echo 'POST_DEPLOY_FAILURE_ROLLED_BACK'
  exit 30
fi
printf 'HUNTER_REAL_READ_ONLY_MARKET_UI_PUBLISHED\nPAGE_COUNT=38\nUI_TESTS_PASSED=37\nMARKETS_OUTPUT=/markets/\nTRADING_OUTPUT=/trading/\nREAL_MARKET_READ_ONLY=true\nORDERS_ENABLED=false\nROLLOUT_BACKUP=%s\nNDSP_UNCHANGED=true\n' "$BEFORE" | tee "$EVID/deployment.log"
