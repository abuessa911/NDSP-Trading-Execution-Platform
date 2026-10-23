#!/usr/bin/env bash
# Hunter KSA1 personal-use finalization, isolated and idempotent.
set -Eeuo pipefail
umask 077
set +x
ROOT=/opt/hunter_ksa1-bot
PY=/srv/hunter-ksa1-api-public/.venv/bin/python
[ "$(id -u)" = 0 ] && [ "$(hostname -s)" = vmi2934783 ] || exit 12
exec 9>/run/lock/hunter-personal-final.lock
flock -n 9 || exit 13
cd "$ROOT"
REPORT="$ROOT/docs/HUNTER_PERSONAL_FINAL_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 "$REPORT"
systemctl is-active --quiet hunter-ksa1-api-public-candidate
systemctl is-active --quiet hunter-ksa1-keycloak-public-staging
systemctl is-active --quiet hunter-ksa1-gateway
systemctl is-active --quiet postgresql@16-hunterprod
nginx -t > "$REPORT/nginx.log" 2>&1
nginx -p /etc/hunter-ksa1-gateway/ -c nginx.conf -t >> "$REPORT/nginx.log" 2>&1
runuser -u postgres -- pg_dump -p 55433 -d nex -Fc > "$REPORT/nex-before.dump"
test -s "$REPORT/nex-before.dump"
echo "ISOLATED_BACKUP_AND_GATEWAY_PASS"
PYTHONPATH="$ROOT/apps/api" "$PY" - <<'PY'
import asyncio,os
from pathlib import Path
from urllib.parse import urlsplit
import httpx
from sqlalchemy import select,text
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
def read_env(name):
    result={}
    for line in Path(name).read_text().splitlines():
        if '=' in line and not line.startswith('#'):
            a,b=line.split('=',1)
            result[a]=b.strip().strip('"').strip("'")
    return result
owner='ndsp.app@gmail.com'
issuer='https://bot.ndsp.app/oidc/realms/hunter-m1'
public=read_env('/etc/hunter-ksa1-identity/public-api.env')
db=read_env('/etc/hunter-ksa1-identity/public-api-db.env')
kc=read_env('/etc/hunter-ksa1-identity/public-keycloak.env')
for key,value in dict(GLOBAL_KILL_SWITCH='true',LIVE_TRADING_ENABLED='false',
  BINANCE_ALLOW_WITHDRAW='false',M2A_PUBLIC_MARKET_ENABLED='false',
  TRADING_MODE='paper',OIDC_BROWSER_LOGIN_ENABLED='true',
  OIDC_ISSUER=issuer).items():
    if public.get(key)!=value: raise SystemExit('UNSAFE_CONFIG_'+key)
for key,role in [('DATABASE_URL','nex_app'),('MIGRATION_DATABASE_URL','nex_migrator')]:
    url=urlsplit(db.get(key,''))
    if (url.scheme!='postgresql+asyncpg' or url.hostname!='127.0.0.1'
      or url.port!=55433 or url.path!='/nex' or url.username!=role or not url.password):
        raise SystemExit('UNSAFE_DB_'+key)
with httpx.Client(timeout=12,trust_env=False,headers=dict(Host='bot.ndsp.app',
     **{'X-Forwarded-Proto':'https','X-Forwarded-Host':'bot.ndsp.app',
       'X-Forwarded-Port':'443'})) as client:
    response=client.post('http://127.0.0.1:19485/oidc/realms/master/protocol/openid-connect/token',
        data={'client_id':'admin-cli','grant_type':'password',
              'username':kc['KC_BOOTSTRAP_ADMIN_USERNAME'],
              'password':kc['KC_BOOTSTRAP_ADMIN_PASSWORD']})
    if response.status_code!=200: raise SystemExit('KEYCLOAK_ADMIN_READ_UNAVAILABLE')
    auth={'Authorization':'Bearer '+response.json()['access_token']}
    base='http://127.0.0.1:19485/oidc/admin/realms/hunter-m1'
    def get(p,params=None):
        r=client.get(base+p,params=params,headers=auth)
        if r.status_code!=200: raise SystemExit('KEYCLOAK_READ_UNAVAILABLE')
        return r.json()
    realm=get('')
    if (realm.get('verifyEmail') is not True or realm.get('registrationAllowed') is not False
        or realm.get('bruteForceProtected') is not True): raise SystemExit('UNSAFE_REALM')
    users=[u for u in get('/users',{'email':owner,'exact':'true'})
           if (u.get('email') or '').lower()==owner]
    if len(users)!=1: raise SystemExit('OWNER_NOT_UNIQUE')
    user=get('/users/'+users[0]['id'])
    types={v.get('type') for v in get('/users/'+users[0]['id']+'/credentials')}
    if not (user.get('emailVerified') is True and user.get('enabled') is True
       and not user.get('requiredActions') and {'password','otp'}<=types):
        raise SystemExit('EMAIL_PASSWORD_TOTP_INCOMPLETE')
    subject=user['id']
    clients=get('/clients',{'clientId':'hunter-m1-admin'})
    if (len(clients)!=1 or clients[0].get('publicClient') is not False
        or not clients[0].get('authenticationFlowBindingOverrides',{}).get('browser')):
        raise SystemExit('ADMIN_MFA_CLIENT_UNSAFE')
os.environ.update(public)
os.environ.update(db)
from nex_api.bootstrap import provision_owner
from nex_api.models import User
from nex_api.database import normalize_database_url
async def finish():
    engine=create_async_engine(normalize_database_url(db['MIGRATION_DATABASE_URL']),
       hide_parameters=True,pool_pre_ping=True)
    try:
        async with async_sessionmaker(engine)() as session:
            ok=(await session.execute(text(
              "SELECT NOT rolsuper AND NOT rolbypassrls FROM pg_roles "
              "WHERE rolname=current_user AND current_user='nex_migrator'"
            ))).scalar_one_or_none()
            if ok is not True: raise RuntimeError('WRONG_MIGRATION_ROLE')
            existing=(await session.execute(select(User).where(
                (User.email==owner)|((User.issuer==issuer)&(User.subject==subject))
            ))).scalars().all()
            if existing:
                if (len(existing)!=1 or existing[0].subject!=subject
                    or existing[0].issuer!=issuer or existing[0].email!=owner
                    or existing[0].role!='ADMIN' or existing[0].status!='active'):
                    raise RuntimeError('OWNER_DATABASE_CONFLICT')
                print('OWNER_ADMIN_ALREADY_BOUND')
                return
        await provision_owner(issuer=issuer,subject=subject,
            tenant_name='Hunter KSA1 personal owner',email=owner,role='ADMIN')
        async with async_sessionmaker(engine)() as session:
            verified=(await session.execute(select(User).where(User.issuer==issuer,
               User.subject==subject,User.email==owner,User.role=='ADMIN',
               User.status=='active'))).scalars().all()
            if len(verified)!=1: raise RuntimeError('OWNER_BOOTSTRAP_NOT_VERIFIED')
        print('VERIFIED_OWNER_BOUND_TO_ADMIN')
    finally:
        await engine.dispose()
asyncio.run(finish())
PY
echo 'OWNER_DATABASE_GATE_PASS'
curl -fsS --max-time 8 http://127.0.0.1:19486/api/health/ready |
  "$PY" -c 'import json,sys; x=json.load(sys.stdin);assert x["components"]=={"database":"ready","redis":"ready","oidc":"ready"}'
for p in /api/v1/me /api/v1/auth/session /api/v1/admin/registrations; do
  [ "$(curl -sS --max-time 8 -o /dev/null -w '%{http_code}' "http://127.0.0.1:19486$p")" = 401 ] || exit 40
done
[ "$(curl -sk --max-time 8 -o /dev/null -w '%{http_code}' https://bot.ndsp.app/subscription/)" = 401 ] || exit 41
PYTHONPATH=apps/api "$ROOT/.venv-qa/bin/pytest" -q apps/api/tests > "$REPORT/backend-tests.log" 2>&1
pnpm --filter @workspace/ndsp-console test > "$REPORT/ui-tests.log" 2>&1
tail -n 1 "$REPORT/backend-tests.log"
grep -E 'pass [0-9]+' "$REPORT/ui-tests.log" | tail -n 1
echo 'PERSONAL_SERVER_GATES_PASS'
echo 'MANUAL_BROWSER_MFA_LOGIN_STILL_REQUIRED'
echo 'OPEN=https://bot.ndsp.app/account-access/'
echo "EVIDENCE=$REPORT"
