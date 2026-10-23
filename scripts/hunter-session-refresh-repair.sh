#!/usr/bin/env bash
# Hunter bot-only session refresh repair. Never modify NDSP or Keycloak settings.
set -Eeuo pipefail
umask 077
ROOT=/opt/hunter_ksa1-bot
API=/srv/hunter-ksa1-api-public/nex_api/routes/auth.py
UI=/srv/hunter-ksa1-preview
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
EVID="$ROOT/docs/session-refresh-20261017"
BAK="$EVID/backup-$STAMP"
mkdir -p "$BAK"
chmod 700 "$BAK"
exec 9>/run/lock/hunter-session-refresh-release.lock
flock -n 9 || { echo ACTIVE_RELEASE_LOCK; exit 9; }
[ "$(hostname -s)" = vmi2934783 ] && [ "$(id -u)" = 0 ] || exit 10
test -f "$ROOT/artifacts/ndsp-console/out/account-access/index.html"
test -f "$ROOT/artifacts/ndsp-console/out/subscription/index.html"
test -s "$EVID/backend-tests.log"
test -s "$EVID/frontend-build.log"
grep -Eq '28[0-9] passed, 15 skipped' "$EVID/backend-tests.log"
grep -q '36/36' "$EVID/frontend-build.log"
python3 -m py_compile "$ROOT/apps/api/nex_api/routes/auth.py"
systemctl is-active --quiet hunter-ksa1-api-public-candidate
systemctl is-active --quiet hunter-ksa1-preview
systemctl is-active --quiet hunter-ksa1-gateway
# Verify published release cannot inadvertently enable exchange execution.
grep -q '^LIVE_TRADING_ENABLED=false' /etc/hunter-ksa1-identity/public-api.env
grep -q '^GLOBAL_KILL_SWITCH=true' /etc/hunter-ksa1-identity/public-api.env
grep -q '^BINANCE_ALLOW_WITHDRAW=false' /etc/hunter-ksa1-identity/public-api.env
cp -p "$API" "$BAK/auth.py"
cp -a "$UI/out" "$BAK/out"
APPLIED=0
SWAPPED=0
STAGE="$UI/out-stage-session-$STAMP"
BEFORE="$UI/out-before-session-$STAMP"
failback() {
  rc=$?
  trap - EXIT
  if [ "$rc" -ne 0 ]; then
    echo "SESSION_REFRESH_RELEASE_FAILED__ROLLBACK" >&2
    if [ "$SWAPPED" = 1 ]; then
      mv "$UI/out" "$UI/out-failed-session-$STAMP" || true
      mv "$BEFORE" "$UI/out" || cp -a "$BAK/out" "$UI/out"
    fi
    if [ "$APPLIED" = 1 ]; then
      cp -p "$BAK/auth.py" "$API" || true
      systemctl restart hunter-ksa1-api-public-candidate || true
    fi
  fi
  echo "ROLLBACK_BACKUP=$BAK"
  exit "$rc"
}
trap failback EXIT
# Build a new static preview without touching its currently running files.
cp -a "$UI/out" "$STAGE"
rsync -rlt --no-owner --no-group --no-perms "$ROOT/artifacts/ndsp-console/out/" "$STAGE/"
chmod -R u=rwX,go=rX "$STAGE"
runuser -u www-data -- test -r "$STAGE/account-access/index.html"
# Only update the isolated Hunter candidate service; do not touch NDSP.
cp -p "$ROOT/apps/api/nex_api/routes/auth.py" "$API"
# The source tree is root-only (0600); the systemd service is DynamicUser.
# Restore read permissions on this deployed non-secret Python module only.
chmod 644 "$API"
APPLIED=1
systemctl restart hunter-ksa1-api-public-candidate
OK=0
for attempt in $(seq 1 20); do
  if curl -fsS --max-time 4 http://127.0.0.1:19486/api/health/ready | python3 -c 'import json,sys; x=json.load(sys.stdin); assert x["components"]=={"database":"ready","redis":"ready","oidc":"ready"}' >/dev/null 2>&1; then
    OK=1
    break
  fi
  sleep 1
done
[ "$OK" = 1 ] || exit 22
mv "$UI/out" "$BEFORE"
mv "$STAGE" "$UI/out"
SWAPPED=1
[ "$(curl -s --max-time 7 -o /dev/null -w '%{http_code}' http://127.0.0.1:19344/account-access/)" = 200 ]
[ "$(curl -sk --max-time 7 -o /dev/null -w '%{http_code}' https://bot.ndsp.app/account-access/)" = 401 ]
[ "$(curl -sk --max-time 7 -o /dev/null -w '%{http_code}' https://bot.ndsp.app/api/v1/auth/session)" = 401 ]
[ "$(curl -sk --max-time 7 -o /dev/null -w '%{http_code}' https://ndsp.app/)" = 200 ]
cmp "$ROOT/artifacts/ndsp-console/out/account-access/index.html" "$UI/out/account-access/index.html"
sha256sum "$API" "$ROOT/apps/api/nex_api/routes/auth.py" > "$BAK/source-sha256.txt"
trap - EXIT
echo "HUNTER_SESSION_REFRESH_REPAIR_PUBLISHED"
echo "RELEASE_BACKUP=$BAK"
echo "ADMIN_MFA_REAL_BROWSER_REFRESH_VALIDATION_PENDING"
