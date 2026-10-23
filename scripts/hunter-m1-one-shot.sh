#!/usr/bin/env bash
# Hunter KSA1 M1 governed one-shot completion and acceptance.
# Owner-triggered, bot-scoped; never grants roles, creates real credentials, or enables trading.
set -Eeuo pipefail
umask 077
ROOT=/opt/hunter_ksa1-bot
PUBLIC=/srv/hunter-ksa1-preview
DATE="$(date -u +%Y%m%dT%H%M%SZ)"
WORK="$ROOT/docs/M1_ONESHOT_$DATE"
REPORT="$ROOT/docs/HUNTER_M1_ONESHOT_LATEST.md"
mkdir -p "$WORK"
chmod 700 "$WORK"
exec 9>/run/lock/hunter-ksa1-m1-one-shot.lock
flock -n 9 || { echo "Another Hunter M1 run is active"; exit 11; }
RESULTS="$WORK/results.tsv"
touch "$RESULTS"
PHASE="PRECHECK"
PATCHED=0
DEPLOYED=0
OLD_OUT=""
SRC_FILES=(
  artifacts/ndsp-console/src/components/AccountEnrollmentPanel.tsx
  artifacts/ndsp-console/src/ndsp/i18n.tsx
  artifacts/ndsp-console/tests/account-onboarding.test.mjs
)
record() { printf '%s\t%s\n' "$1" "$2" >> "$RESULTS"; printf '[%s] %s\n' "$2" "$1"; }
restore_sources() {
  for f in "${SRC_FILES[@]}"; do
    if [ -f "$WORK/source-before/$f" ]; then cp -p "$WORK/source-before/$f" "$ROOT/$f"; fi
  done
}
finish() {
  local rc=$?
  trap - EXIT
  if [ "$rc" -ne 0 ]; then
    if [ "$PATCHED" = 1 ] && [ "$DEPLOYED" = 0 ]; then restore_sources; fi
    record "$PHASE" "FAILED"
  fi
  {
    echo '# Hunter KSA1 M1 — One-shot governed acceptance'
    echo
    echo "- UTC: $DATE"
    echo "- Server: vmi2934783"
    echo "- Runner: $ROOT/scripts/hunter-m1-one-shot.sh"
    echo "- Execution result: $([ "$rc" -eq 0 ] && echo AUTOMATED_GATES_PASSED || echo AUTOMATED_GATES_FAILED)"
    echo "- M1 approval: **NOT ACCEPTED — OWNER VERIFICATION REQUIRED**"
    echo "- Trading: **PAPER ONLY, GLOBAL KILL SWITCH ON**"
    echo "- Production NDSP services: not reconfigured or restarted by this script"
    echo "- Private evidence directory: $WORK"
    echo
    echo '## Completed gates'
    while IFS="$(printf '\t')" read -r name status; do printf -- '- %s: %s\n' "$name" "$status"; done < "$RESULTS"
    echo
    echo '## Unautomatable acceptance requirements'
    echo '1. The owner must verify control of their real email through Keycloak using a secure delivery channel.'
    echo '2. The owner must personally establish a strong password and TOTP; never generate/share secrets via logs or chat.'
    echo '3. A genuinely authenticated public-browser ADMIN + MFA acceptance must prove session, CSRF, audit, RLS and logout.'
    echo '4. Provisioning and SMTP delivery must be approved before real account invitations can complete.'
    echo '5. Do not enable private exchange orders, live trading, or close NAW-65 until all remaining gates pass.'
    echo
    echo '## Rollback'
    if [ -n "$OLD_OUT" ]; then
      echo "- Previous public static UI snapshot: $OLD_OUT"
    else
      echo '- No static deployment swap occurred.'
    fi
    echo "- Source edits backed up at: $WORK/source-before"
  } > "$REPORT"
  chmod 600 "$REPORT"
  printf 'REPORT=%s\nEVIDENCE=%s\n' "$REPORT" "$WORK"
  exit "$rc"
}
trap finish EXIT
run_step() {
  local label="$1" slug="$2"
  shift 2
  PHASE="$label"
  if "$@" > "$WORK/$slug.log" 2>&1; then record "$label" "PASS"
  else
    echo "FAILED: $label (private log: $WORK/$slug.log)" >&2
    tail -n 10 "$WORK/$slug.log" | sed -E 's/(password|secret|token|cookie|authorization)([=: ]+)[^ ]+/\1 [REDACTED]/Ig' >&2
    return 1
  fi
}
cd "$ROOT"
[ "$(hostname -s)" = vmi2934783 ] || { echo "Unexpected host"; exit 12; }
[ "$(id -u)" = 0 ] || { echo "Root privileges required for protected bot-only gates"; exit 13; }
[ -x .venv-qa/bin/pytest ] || { echo "QA venv missing"; exit 14; }
[ -f "$PUBLIC/out/subscription/index.html" ] || { echo "Public bot UI missing"; exit 15; }
[ -f /etc/hunter-ksa1-gateway/nginx.conf ] || exit 16
[ -f /etc/hunter-ksa1-identity/public-api.env ] || exit 17
mkdir -p "$WORK/source-before"
for f in "${SRC_FILES[@]}"; do
  mkdir -p "$WORK/source-before/$(dirname "$f")"
  cp -p "$f" "$WORK/source-before/$f"
done
cp -p /etc/hunter-ksa1-gateway/nginx.conf "$WORK/gateway.before"
cp -p /etc/nginx/sites-enabled/ndsp-contabo-recovery.conf "$WORK/main-nginx.before"
sha256sum "$WORK/gateway.before" "$WORK/main-nginx.before" > "$WORK/config-backup-checksums.txt"
record "Scoped backup and exclusive lock" "PASS"

PHASE="Fail-closed configuration"
python3 - <<'PY'
from pathlib import Path
p=Path('/etc/hunter-ksa1-identity/public-api.env')
settings=dict(line.split('=',1) for line in p.read_text().splitlines() if '=' in line and not line.lstrip().startswith('#'))
for k,expected in {'LIVE_TRADING_ENABLED':'false','GLOBAL_KILL_SWITCH':'true','BINANCE_ALLOW_WITHDRAW':'false','M2A_PUBLIC_MARKET_ENABLED':'false','TRADING_MODE':'paper','OIDC_BROWSER_LOGIN_ENABLED':'true','OIDC_ISSUER':'https://bot.ndsp.app/oidc/realms/hunter-m1'}.items():
    if settings.get(k,'').strip(" '\"").lower()!=expected.lower(): raise SystemExit('UNSAFE_M1_CONFIG_'+k)
print('FAIL_CLOSED_POLICY_PASS')
PY
record "Trading disabled and OIDC issuer pinned" "PASS"
for svc in hunter-ksa1-api-public-candidate hunter-ksa1-keycloak-public-staging hunter-ksa1-gateway hunter-ksa1-preview hunter-ksa1-redis postgresql@16-hunter; do
  systemctl is-active --quiet "$svc" || { echo "Missing isolated service: $svc"; exit 18; }
done
record "Isolated public M1 services running" "PASS"
run_step "System Nginx syntax" nginx-system nginx -t
run_step "Private gateway syntax" nginx-bot nginx -p /etc/hunter-ksa1-gateway/ -c nginx.conf -t
run_step "API readiness + HTTP authorization negative tests" api-smoke python3 - <<'PY'
import json,urllib.request,urllib.error
def status(url,method='GET',headers=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,method=method,headers=headers or {}),timeout=8) as r:
            return r.status,r.read()
    except urllib.error.HTTPError as e:
        return e.code,e.read()
for port in (19481,19486):
    root=f'http://127.0.0.1:{port}'
    code,body=status(root+'/api/health/ready')
    if code!=200 or json.loads(body).get('components')!={'database':'ready','redis':'ready','oidc':'ready'}:
        raise RuntimeError('DEPENDENCY_UNREADY')
    for url in ('/api/v1/me','/api/v1/auth/session','/api/v1/admin/registrations'):
        code,_=status(root+url)
        if code!=401: raise RuntimeError('ANONYMOUS_ACCESS_NOT_DENIED')
    code,_=status(root+'/api/v1/auth/login',method='POST')
    if code!=403: raise RuntimeError('MISSING_ORIGIN_NOT_DENIED')
for url,expected in (
 ('https://bot.ndsp.app/api/v1/auth/session',401),
 ('https://bot.ndsp.app/subscription/',401),
 ('https://bot.ndsp.app/oidc/admin/',403),
 ('https://bot.ndsp.app/oidc/realms/master/',403)):
    code,_=status(url)
    if code!=expected: raise RuntimeError('PUBLIC_SECURITY_GATE_MISMATCH')
code,body=status('https://bot.ndsp.app/oidc/realms/hunter-m1/.well-known/openid-configuration')
if code!=200 or json.loads(body).get('issuer')!='https://bot.ndsp.app/oidc/realms/hunter-m1':
    raise RuntimeError('PUBLIC_OIDC_DISCOVERY_MISMATCH')
print('PUBLIC_AND_PRIVATE_HTTP_SECURITY_PASS')
PY
run_step "Keycloak MFA policy and empty real-user baseline" keycloak-policy /srv/hunter-ksa1-api-public/.venv/bin/python scripts/verify-public-keycloak-policy.py
run_step "Real HTTPS OIDC login initiation + ephemeral gate cleanup" public-login /srv/hunter-ksa1-api-public/.venv/bin/python scripts/smoke-public-m1-login.py
PHASE="Outdated registration description"
python3 - <<'PY'
from pathlib import Path
base=Path('artifacts/ndsp-console')
old='The current M1 API does not provide administrator-approved account creation. Registration is not available until its protected server workflow and tests are completed.'
new='Account invitations require an authenticated administrator with verified MFA. Public sign-up remains disabled, and invited identities must verify their email.'
old_ar='واجهة M1 الحالية لا توفر وظيفة معتمدة لإنشاء الحسابات بواسطة المدير. التسجيل غير متاح حتى اكتمال وظيفته المحمية واختباراتها على الخادم.'
new_ar='دعوات الحسابات تتطلب مديراً مصادقاً عليه مع تحقق متعدد العوامل. التسجيل العام معطّل، ويجب على المدعوين تأكيد بريدهم الإلكتروني.'
files=[
 ('src/components/AccountEnrollmentPanel.tsx',old,new),
 ('src/ndsp/i18n.tsx',old,new),
 ('src/ndsp/i18n.tsx',old_ar,new_ar),
 ('tests/account-onboarding.test.mjs','account creation remains explicitly disabled until an authorized backend exists','public account creation remains blocked while MFA-protected invitations exist'),
 ('tests/account-onboarding.test.mjs','current M1 API does not provide administrator-approved account creation','Account invitations require an authenticated administrator with verified MFA'),
]
for filename,source,dest in files:
    path=base/filename
    value=path.read_text()
    if value.count(source)!=1: raise RuntimeError('SOURCE_VERSION_UNEXPECTED_'+filename)
    path.write_text(value.replace(source,dest,1))
PY
PATCHED=1
record "Registration copy corrected without exposing public enrollment" "PASS"
run_step "Python API automated suite" python-tests bash -lc "cd '$ROOT' && PYTHONPATH=apps/api .venv-qa/bin/pytest -q apps/api/tests"
run_step "Frontend UI/contract automated suite" ui-tests pnpm --filter @workspace/ndsp-console run test
run_step "Frontend TypeScript checks" ui-ts pnpm --filter @workspace/ndsp-console run typecheck
run_step "Static Next.js build" ui-build pnpm --filter @workspace/ndsp-console run build
PHASE="Static export scope validation"
for page in index.html subscription/index.html settings/index.html account-access/index.html registration/index.html; do
  [ -f "artifacts/ndsp-console/out/$page" ] || { echo "Missing generated bot page: $page"; exit 21; }
done
record "Generated public bot pages present" "PASS"
PHASE="Bot-only static UI deployment"
NEXT_OUT="$PUBLIC/out-stage-$DATE"
OLD_OUT="$PUBLIC/out-before-m1-one-shot-$DATE"
[ ! -e "$NEXT_OUT" ] && [ ! -e "$OLD_OUT" ] || { echo "Previous deployment naming collision"; exit 22; }
cp -a "$PUBLIC/out" "$NEXT_OUT"
rsync -rlt --no-perms --no-owner --no-group "artifacts/ndsp-console/out/" "$NEXT_OUT/"
# The runner has umask 077. Explicitly restore public-read permissions ONLY
# for generated static pages/assets; keep all secrets/configuration private.
chmod -R u=rwX,go=rX "$NEXT_OUT"
runuser -u www-data -- test -r "$NEXT_OUT/subscription/index.html" || { echo "Static export not readable by www-data"; exit 30; }
mv "$PUBLIC/out" "$OLD_OUT"
if ! mv "$NEXT_OUT" "$PUBLIC/out"; then
  mv "$OLD_OUT" "$PUBLIC/out"
  exit 23
fi
DEPLOYED=1
if ! cmp -s artifacts/ndsp-console/out/subscription/index.html "$PUBLIC/out/subscription/index.html"; then
  mv "$PUBLIC/out" "$PUBLIC/out-failed-$DATE"
  mv "$OLD_OUT" "$PUBLIC/out"
  DEPLOYED=0
  echo "M1 deployment mismatch, reverted"
  exit 24
fi
for page in / /subscription/ /settings/ /account-access/ /registration/; do
  code=$(curl -sS --max-time 6 -o /dev/null -w '%{http_code}' "http://127.0.0.1:19344$page")
  [ "$code" = 200 ] || { mv "$PUBLIC/out" "$PUBLIC/out-failed-$DATE"; mv "$OLD_OUT" "$PUBLIC/out"; DEPLOYED=0; echo "Rolled back preview failure"; exit 25; }
done
record "Bot-only static interface deployed and HTTP-smoked" "PASS"
PHASE="Final safety and unchanged routes"
cmp -s "$WORK/gateway.before" /etc/hunter-ksa1-gateway/nginx.conf || { echo "Bot gateway changed unexpectedly"; exit 26; }
cmp -s "$WORK/main-nginx.before" /etc/nginx/sites-enabled/ndsp-contabo-recovery.conf || { echo "Main Nginx config changed unexpectedly"; exit 27; }
for svc in hunter-ksa1-api-public-candidate hunter-ksa1-keycloak-public-staging hunter-ksa1-gateway hunter-ksa1-preview; do systemctl is-active --quiet "$svc" || exit 28; done
[ "$(curl -ksS -o /dev/null -w '%{http_code}' --max-time 8 https://bot.ndsp.app/subscription/)" = 401 ] || exit 29
record "Final services, gateway protection, and unchanged Nginx configuration" "PASS"
echo "AUTOMATED_M1_GATES_PASSED__OWNER_EMAIL_MFA_STILL_PENDING"
