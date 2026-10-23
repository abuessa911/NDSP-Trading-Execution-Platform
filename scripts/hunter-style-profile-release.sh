#!/usr/bin/env bash
# Bot-only M1 user preference + UI release. No NDSP or exchange changes.
set -Eeuo pipefail
umask 077
ROOT=/opt/hunter_ksa1-bot
DEPLOY=/srv/hunter-ksa1-api-public/nex_api
STATIC=/srv/hunter-ksa1-preview
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
EVID="$ROOT/docs/ui-contract-audit-20261017"
BAK="$EVID/release-backup-$STAMP"
mkdir -p "$BAK"
exec 9>/run/lock/hunter-style-mode-release.lock
flock -n 9 || exit 17
[ "$(id -u)" -eq 0 ] && [ "$(hostname -s)" = vmi2934783 ] || exit 18
grep -q "286 passed, 15 skipped" "$EVID/backend-tests-v2.log"
grep -q 'pass 34' "$EVID/frontend-tests.log"
grep -q "36/36" "$EVID/build.log"
grep -q 'LIVE_TRADING_ENABLED=false' /etc/hunter-ksa1-identity/public-api.env
grep -q 'GLOBAL_KILL_SWITCH=true' /etc/hunter-ksa1-identity/public-api.env
grep -q 'BINANCE_ALLOW_WITHDRAW=false' /etc/hunter-ksa1-identity/public-api.env
systemctl is-active --quiet hunter-ksa1-api-public-candidate
systemctl is-active --quiet hunter-ksa1-gateway
systemctl is-active --quiet hunter-ksa1-keycloak-public-staging
cmp "$ROOT/apps/api/nex_api/routes/auth.py" "$DEPLOY/routes/auth.py"
python3 -m py_compile "$ROOT/apps/api/nex_api/main.py" "$ROOT/apps/api/nex_api/routes/trading_profile.py"
cp -p "$DEPLOY/main.py" "$BAK/main.py"
if [ -f "$DEPLOY/routes/trading_profile.py" ]; then cp -p "$DEPLOY/routes/trading_profile.py" "$BAK/trading_profile.py"; fi
cp -a "$STATIC/out" "$BAK/out"
TEMP="$STATIC/out-stage-style-$STAMP"
PREV="$STATIC/out-before-style-$STAMP"
cp -a "$STATIC/out" "$TEMP"
rsync -rlt --no-owner --no-group --no-perms "$ROOT/artifacts/ndsp-console/out/" "$TEMP/"
chmod -R u=rwX,go=rX "$TEMP"
runuser -u www-data -- test -r "$TEMP/trading/index.html"
API_CHANGED=0
UI_CHANGED=0
rollback() {
  code=$?
  trap - EXIT
  if [ "$code" -ne 0 ]; then
    echo "HUNTER_STYLE_RELEASE_FAILED_REVERTING"
    if [ "$UI_CHANGED" = 1 ]; then
      mv "$STATIC/out" "$STATIC/out-failed-style-$STAMP" || true
      mv "$PREV" "$STATIC/out" || cp -a "$BAK/out" "$STATIC/out"
    fi
    if [ "$API_CHANGED" = 1 ]; then
      cp -p "$BAK/main.py" "$DEPLOY/main.py"
      chmod 644 "$DEPLOY/main.py"
      if [ -f "$BAK/trading_profile.py" ]; then
        cp -p "$BAK/trading_profile.py" "$DEPLOY/routes/trading_profile.py"
      else
        rm -f "$DEPLOY/routes/trading_profile.py"
      fi
      systemctl restart hunter-ksa1-api-public-candidate || true
    fi
  fi
  echo "ROLLBACK_BACKUP=$BAK"
  exit "$code"
}
trap rollback EXIT
cp -p "$ROOT/apps/api/nex_api/main.py" "$DEPLOY/main.py"
cp -p "$ROOT/apps/api/nex_api/routes/trading_profile.py" "$DEPLOY/routes/trading_profile.py"
chmod 644 "$DEPLOY/main.py" "$DEPLOY/routes/trading_profile.py"
API_CHANGED=1
systemctl restart hunter-ksa1-api-public-candidate
OK=0
for i in $(seq 1 20); do
  if curl -fsS --max-time 5 http://127.0.0.1:19486/api/health/ready 2>/dev/null |
     python3 -c 'import json,sys;d=json.load(sys.stdin);assert d["components"]=={"database":"ready","redis":"ready","oidc":"ready"}' 2>/dev/null; then
    OK=1; break
  fi
  sleep 1
done
[ "$OK" = 1 ] || exit 31
[ "$(curl -sS --max-time 7 -o /dev/null -w '%{http_code}' http://127.0.0.1:19486/api/v1/trading/profile)" = 401 ] || exit 32
curl -fsS --max-time 6 http://127.0.0.1:19486/api/openapi.json |
  python3 -c 'import json,sys; x=json.load(sys.stdin); assert "/api/v1/trading/profile" not in x["paths"]' || exit 33
mv "$STATIC/out" "$PREV"
mv "$TEMP" "$STATIC/out"
UI_CHANGED=1
[ "$(curl -sS --max-time 8 -o /dev/null -w '%{http_code}' http://127.0.0.1:19344/trading/)" = 200 ] || exit 34
cmp "$ROOT/artifacts/ndsp-console/out/trading/index.html" "$STATIC/out/trading/index.html"
[ "$(curl -sk --max-time 8 -o /dev/null -w '%{http_code}' https://bot.ndsp.app/trading/)" = 401 ] || exit 35
[ "$(curl -sk --max-time 8 -o /dev/null -w '%{http_code}' https://bot.ndsp.app/api/v1/trading/profile)" = 401 ] || exit 36
[ "$(curl -sk --max-time 8 -o /dev/null -w '%{http_code}' https://ndsp.app/)" = 200 ] || exit 37
trap - EXIT
echo "HUNTER_TRADING_STYLE_UI_BACKEND_RELEASE_PASS"
echo "STYLE_OPTIONS=INVESTMENT,SPECULATIVE"
echo "ALL_ORDER_EXECUTION_STILL_DISABLED"
echo "NDSP_PUBLIC_CONTRACT_UNCHANGED"
echo "ROLLBACK_BACKUP=$BAK"
