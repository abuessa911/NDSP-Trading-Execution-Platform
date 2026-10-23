#!/usr/bin/env bash
# hunter_ksa1 — final M1 acceptance orchestration
# Executes all available automated proof gates; never fakes the owner's email/MFA evidence.
set -Eeuo pipefail
umask 077
ROOT=/opt/hunter_ksa1-bot
APP="$ROOT/artifacts/ndsp-console"
BASE=/etc/hunter-ksa1-identity
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
EVIDENCE="$ROOT/docs/HUNTER_M1_FINAL_$STAMP"
REPORT="$ROOT/docs/HUNTER_M1_FINAL_LATEST.md"
mkdir -p "$EVIDENCE"
chmod 700 "$EVIDENCE"
exec 9>/run/lock/hunter-ksa1-m1-final.lock
flock -n 9 || { echo 'M1 FINAL ALREADY RUNNING'; exit 8; }
RESULTS="$EVIDENCE/results.tsv"
touch "$RESULTS"
STATUS=AUTOMATED_CHECKS_FAILED
step=START
log_result() { printf '%s\t%s\n' "$1" "$2" >> "$RESULTS"; printf '[%s] %s\n' "$2" "$1"; }
finish() {
  rc=$?
  trap - EXIT
  if [ "$rc" -eq 0 ]; then STATUS=READY_FOR_OWNER_VERIFICATION; fi
  {
    printf '# hunter_ksa1 M1 Final Acceptance — %s\n\n' "$STAMP"
    printf -- '- Automated result: **%s**\n' "$STATUS"
    printf -- '- M1 overall acceptance: **NOT ACCEPTED**\n'
    printf -- '- Account: ndsp.app@gmail.com — PENDING, not an authenticated ADMIN\n'
    printf -- '- Live trading: disabled, global kill switch on\n'
    printf -- '- Scope: read-only acceptance, no NDSP service changes, no real account promotion\n'
    printf -- '- Evidence directory: %s\n\n' "$EVIDENCE"
    echo '## Gate results'
    while IFS="$(printf '\t')" read -r n s; do printf -- '- %s: %s\n' "$n" "$s"; done < "$RESULTS"
    echo
    echo '## Required manual / external proofs'
    echo '1. Configure a trusted Keycloak SMTP sender and test delivery; no SMTP secret may be logged.'
    echo '2. Establish owner identity through a verified email action link; owner personally sets the password and TOTP.'
    echo '3. Verify Keycloak emailVerified=true and OTP enrollment, then bind the verified OIDC subject to the ADMIN record using an approved operator bootstrap.'
    echo '4. Prove a real public-browser password+TOTP sign-in, CSRF, admin API, tenant isolation, audit, refresh and logout; preserve negative tests.'
    echo '5. Independently approve M1 and close NAW-65 only after those proofs. Paper/live execution remains disabled.'
    echo
    echo '## Official references'
    echo '- https://www.keycloak.org/server/reverseproxy'
    echo '- https://www.keycloak.org/docs-api/latest/rest-api/index.html'
  } > "$REPORT"
  chmod 600 "$REPORT"
  printf 'FINAL_REPORT=%s\n' "$REPORT"
  exit "$rc"
}
trap finish EXIT
check() {
  name="$1"; slug="$2"; shift 2
  step="$name"
  if "$@" > "$EVIDENCE/$slug.log" 2>&1; then log_result "$name" PASS
  else
    log_result "$name" FAIL
    printf 'FAILED %s; evidence in %s\n' "$name" "$EVIDENCE/$slug.log" >&2
    return 1
  fi
}
[ "$(id -u)" -eq 0 ] || { echo 'ROOT REQUIRED'; exit 9; }
[ "$(hostname -s)" = vmi2934783 ] || { echo 'WRONG HOST'; exit 10; }
cd "$ROOT"
check 'Hard fail-closed trading and browser login config' safety python3 - <<'PY'
from pathlib import Path
p=Path('/etc/hunter-ksa1-identity/public-api.env')
kv=dict(line.split('=',1) for line in p.read_text().splitlines() if '=' in line and not line.startswith('#'))
expected=dict(GLOBAL_KILL_SWITCH='true',LIVE_TRADING_ENABLED='false',TRADING_MODE='paper',BINANCE_ALLOW_WITHDRAW='false',M2A_PUBLIC_MARKET_ENABLED='false',OIDC_BROWSER_LOGIN_ENABLED='true',OIDC_ISSUER='https://bot.ndsp.app/oidc/realms/hunter-m1')
for k,v in expected.items():
  if kv.get(k,'').strip(" '\"") != v: raise SystemExit('INVALID_'+k)
print('FAIL_CLOSED_POLICY_PASS')
PY
check 'Isolated Hunter service health' services bash -c '
  set -e
  for n in hunter-ksa1-gateway hunter-ksa1-preview hunter-ksa1-api-public-candidate hunter-ksa1-keycloak-public-staging hunter-ksa1-redis postgresql@16-hunter; do
    systemctl is-active --quiet "$n"
  done
  echo ISOLATED_SERVICES_PASS
'
check 'Nginx main and Hunter gateway configuration' nginx bash -c '
  set -e
  nginx -t
  nginx -p /etc/hunter-ksa1-gateway/ -c nginx.conf -t
'
check 'Keycloak public realm mandatory MFA policy' policy /srv/hunter-ksa1-api-public/.venv/bin/python scripts/verify-public-keycloak-policy.py
check 'Production candidate API and public HTTPS negative probes' http python3 - <<'PY'
import json,urllib.request,urllib.error
def fetch(url,method='GET',headers=None):
  try:
    with urllib.request.urlopen(urllib.request.Request(url,method=method,headers=headers or {}),timeout=12) as r: return r.status,r.read(131073)
  except urllib.error.HTTPError as e: return e.code,e.read(131073)
host='http://127.0.0.1:19486'
code,body=fetch(host+'/api/health/ready')
if code!=200 or json.loads(body).get('components')!={'database':'ready','redis':'ready','oidc':'ready'}: raise SystemExit('NOT_READY')
for path in ('/api/v1/me','/api/v1/auth/session','/api/v1/admin/registrations'):
  if fetch(host+path)[0]!=401: raise SystemExit('AUTH_BYPASS_'+path)
if fetch(host+'/api/v1/auth/login','POST')[0]!=403: raise SystemExit('ORIGIN_POLICY_FAIL')
for path,expected in (('/subscription/',401),('/registration/',401),('/api/v1/auth/session',401),('/oidc/admin/',403),('/oidc/realms/master/',403)):
  if fetch('https://bot.ndsp.app'+path)[0]!=expected: raise SystemExit('BAD_PUBLIC_GATE_'+path)
code,data=fetch('https://bot.ndsp.app/oidc/realms/hunter-m1/.well-known/openid-configuration')
if code!=200 or json.loads(data).get('issuer')!='https://bot.ndsp.app/oidc/realms/hunter-m1': raise SystemExit('OIDC_DISCOVERY_FAIL')
print('PUBLIC_IDENTITY_BOUNDARY_PASS')
PY
check 'Real HTTPS login initiation and temporary gate cleanup' login /srv/hunter-ksa1-api-public/.venv/bin/python scripts/smoke-public-m1-login.py
check 'Real backend auth, registration and RLS regression tests' python-regression bash -c '
  cd /opt/hunter_ksa1-bot
  PYTHONPATH=apps/api .venv-qa/bin/pytest -q apps/api/tests
'
check 'Frontend authenticated-session contract and UI tests' ui-tests bash -c '
  cd /opt/hunter_ksa1-bot
  pnpm --filter @workspace/ndsp-console test
'
check 'Existing published protected pages' frontend bash -c '
  set -e
  for path in / /subscription/ /account-access/ /registration/ /settings/; do
    status=$(curl --max-time 6 -sS -o /dev/null -w "%{http_code}" "http://127.0.0.1:19344$path")
    test "$status" = 200
  done
'
# SMTP readiness is not inferred from nonexistent env files or mail-provider guesses.
# No Keycloak user is created and no ADMIN privileges are assigned without owner proof.
printf 'smtp_credentials_or_provider_proof\tUNVERIFIED\n' >> "$RESULTS"
printf 'owner_verified_email_and_totp\tPENDING_OWNER\n' >> "$RESULTS"
printf 'real_authenticated_browser_admin_E2E\tPENDING_OWNER\n' >> "$RESULTS"
log_result 'No real Keycloak user created or elevated by this script' PASS
echo AUTOMATED_M1_FINAL_PROOFS_PASS__HUMAN_OWNER_PROOFS_PENDING
