#!/usr/bin/env bash
# Hunter bot: single secure Gmail SMTP + Keycloak owner onboarding script.
# sudo bash /opt/hunter_ksa1-bot/scripts/hunter-gmail-keycloak-owner.sh --check|--setup|--finalize
set -Eeuo pipefail
umask 077
set +x
ROOT=/opt/hunter_ksa1-bot
PYTHON=/srv/hunter-ksa1-api-public/.venv/bin/python
MODE="${1:---check}"
case "$MODE" in --check|--setup|--finalize) ;; *) echo 'Use --check, --setup or --finalize'; exit 2;; esac
[ "$(id -u)" -eq 0 ] && [ "$(hostname -s)" = vmi2934783 ] || { echo 'Requires root on authorized Contabo vmi2934783'; exit 3; }
[ -x "$PYTHON" ] || exit 4
exec 9>/run/lock/hunter-gmail-keycloak-owner.lock
flock -n 9 || { echo 'Script already running'; exit 5; }
"$PYTHON" - "$MODE" <<'PY'
import getpass, json, os, re, smtplib, ssl, subprocess, sys, time
from email.message import EmailMessage
from pathlib import Path
import httpx

MODE=sys.argv[1]
OWNER="ndsp.app@gmail.com"
ISSUER="https://bot.ndsp.app/oidc/realms/hunter-m1"
KC="http://127.0.0.1:19485/oidc"
REALM=KC+"/admin/realms/hunter-m1"
ROOT=Path("/opt/hunter_ksa1-bot")
STAMP=time.strftime("%Y%m%dT%H%M%SZ",time.gmtime())
HEADERS={"Host":"bot.ndsp.app","X-Forwarded-Proto":"https",
         "X-Forwarded-Host":"bot.ndsp.app","X-Forwarded-Port":"443"}

def env_map(path):
    result={}
    for line in Path(path).read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            name,value=line.split("=",1)
            result[name]=value.strip().strip('"').strip("'")
    return result

kcenv=env_map("/etc/hunter-ksa1-identity/public-keycloak.env")
apienv=env_map("/etc/hunter-ksa1-identity/public-api.env")
for key,expected in {
    "GLOBAL_KILL_SWITCH":"true","LIVE_TRADING_ENABLED":"false",
    "BINANCE_ALLOW_WITHDRAW":"false","TRADING_MODE":"paper",
    "OIDC_ISSUER":ISSUER,"OIDC_BROWSER_LOGIN_ENABLED":"true",
}.items():
    if apienv.get(key)!=expected:
        raise SystemExit("UNSAFE_HUNTER_CONFIGURATION_"+key)

with httpx.Client(timeout=15,trust_env=False,headers=HEADERS,follow_redirects=False) as client:
    response=client.post(KC+"/realms/master/protocol/openid-connect/token",data={
        "client_id":"admin-cli","grant_type":"password",
        "username":kcenv["KC_BOOTSTRAP_ADMIN_USERNAME"],
        "password":kcenv["KC_BOOTSTRAP_ADMIN_PASSWORD"],
    })
    if response.status_code!=200:
        raise SystemExit("KEYCLOAK_ADMIN_UNAVAILABLE")
    bearer={"Authorization":"Bearer "+response.json()["access_token"]}

    def api(method,path,**kwargs):
        return client.request(method,REALM+path,headers=bearer,**kwargs)

    rr=api("GET","")
    if rr.status_code!=200:
        raise SystemExit("REALM_NOT_AVAILABLE")
    realm=rr.json()
    if (realm.get("realm")!="hunter-m1" or realm.get("verifyEmail") is not True
        or realm.get("registrationAllowed") is not False
        or realm.get("bruteForceProtected") is not True):
        raise SystemExit("REALM_POLICY_INCOMPLETE")

    def find_owner():
        answer=api("GET","/users",params={"email":OWNER,"exact":"true","max":10})
        if answer.status_code!=200:
            raise SystemExit("USER_QUERY_FAILED")
        found=[x for x in answer.json() if (x.get("email") or "").lower()==OWNER]
        if len(found)>1:
            raise SystemExit("MULTIPLE_OWNER_IDENTITIES")
        return found[0] if found else None

    def inspect(user):
        if user is None: return dict(present=False,verified=False,password=False,otp=False,actions=[])
        full=api("GET","/users/"+user["id"])
        creds=api("GET","/users/"+user["id"]+"/credentials")
        if full.status_code!=200 or creds.status_code!=200:
            raise SystemExit("USER_STATE_READ_FAILED")
        x=full.json()
        types={c.get("type") for c in creds.json()}
        return dict(present=True,verified=x.get("emailVerified") is True,
                    enabled=x.get("enabled") is True,password="password" in types,
                    otp="otp" in types,actions=x.get("requiredActions",[]),subject=x["id"])

    found=find_owner()
    state=inspect(found)
    smtp=realm.get("smtpServer") or {}
    print("GMAIL_SENDER="+OWNER)
    print("REALM=hunter-m1")
    print("GMAIL_SMTP_CONFIGURED="+str(smtp.get("host")=="smtp.gmail.com").lower())
    print("OWNER_ACCOUNT_EXISTS="+str(state["present"]).lower())
    print("OWNER_EMAIL_VERIFIED="+str(state["verified"]).lower())
    print("OWNER_PASSWORD_SET="+str(state["password"]).lower())
    print("OWNER_TOTP_SET="+str(state["otp"]).lower())
    if MODE=="--check":
        print("READ_ONLY_CHECK_SUCCESS")
        sys.exit(0)

    if MODE=="--setup":
        if smtp.get("host") and smtp.get("host")!="smtp.gmail.com":
            raise SystemExit("REFUSED_REPLACE_EXISTING_MAIL_PROVIDER")
        print("Generate Google App Password: https://myaccount.google.com/apppasswords")
        print("Enter the value privately into the server terminal, never in chat.")
        password="".join(getpass.getpass("Gmail app password (16 characters): ").split())
        if not re.fullmatch(r"[A-Za-z0-9]{16}",password):
            raise SystemExit("INVALID_APP_PASSWORD_FORMAT")
        message=EmailMessage()
        message["From"]=OWNER
        message["To"]=OWNER
        message["Subject"]="Hunter KSA1 SMTP connectivity test"
        message.set_content("Hunter KSA1 authenticated SMTP was tested. No administrator account privileges were assigned.")
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com",465,timeout=18,context=ssl.create_default_context()) as smtp_conn:
                smtp_conn.login(OWNER,password)
                smtp_conn.send_message(message)
        except (smtplib.SMTPException,OSError,TimeoutError):
            raise SystemExit("GMAIL_SMTP_AUTH_OR_TLS_FAILED__NO_CHANGE")
        print("GMAIL_AUTHENTICATED_SMTP_TEST_MESSAGE_SENT")
        new_smtp={
            "host":"smtp.gmail.com","port":"465","from":OWNER,
            "fromDisplayName":"Hunter KSA1","replyTo":OWNER,
            "ssl":"true","starttls":"false","auth":"true",
            "user":OWNER,"password":password,
        }
        backup=Path("/etc/hunter-ksa1-identity")/("smtp-before-"+STAMP+".json")
        fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"w") as stream:
            json.dump({"smtpServer":smtp},stream)
        update=api("PUT","",json={"smtpServer":new_smtp})
        password=""
        new_smtp.clear()
        if update.status_code not in (200,204):
            raise SystemExit("KEYCLOAK_SMTP_UPDATE_FAILED")
        reread=api("GET","")
        if reread.status_code!=200:
            raise SystemExit("KEYCLOAK_SMTP_VERIFICATION_UNAVAILABLE")
        actual=reread.json().get("smtpServer") or {}
        if (actual.get("host")!="smtp.gmail.com" or actual.get("from")!=OWNER
            or str(actual.get("ssl")).lower()!="true"):
            raise SystemExit("KEYCLOAK_SMTP_VERIFICATION_FAILED")
        print("KEYCLOAK_GMAIL_SMTP_SAVED")
        if not found:
            created=api("POST","/users",json={
                "username":OWNER,"email":OWNER,"emailVerified":False,"enabled":True,
                "requiredActions":["VERIFY_EMAIL","UPDATE_PASSWORD","CONFIGURE_TOTP"],
            })
            if created.status_code!=201:
                raise SystemExit("PENDING_OWNER_ACCOUNT_CREATE_FAILED")
            found=find_owner()
            if not found:
                raise SystemExit("NEW_ACCOUNT_NOT_FOUND")
            print("OWNER_PENDING_IDENTITY_CREATED__NO_ADMIN_ROLE")
        elif state["verified"] and state["password"] and state["otp"]:
            print("OWNER_ALREADY_VERIFIED__RUN_FINALIZE")
            sys.exit(0)
        else:
            print("OWNER_PENDING_IDENTITY_REUSED")
        sent=api("PUT","/users/"+found["id"]+"/execute-actions-email",
                 params={"lifespan":3600},
                 json=["VERIFY_EMAIL","UPDATE_PASSWORD","CONFIGURE_TOTP"])
        if sent.status_code not in (200,204):
            raise SystemExit("KEYCLOAK_EMAIL_ACTION_DISPATCH_FAILED")
        print("SECURE_OWNER_SETUP_EMAIL_SENT__EXPIRES_1_HOUR")
        print("COMPLETE_EMAIL_PASSWORD_TOTP_PERSONALLY__THEN_RUN_--finalize")
        sys.exit(0)

    # --finalize: only a verified owner with password AND OTP credentials qualifies.
    if not found:
        raise SystemExit("OWNER_NOT_PRESENT__RUN_SETUP")
    state=inspect(found)
    if (not state["verified"] or not state["enabled"]
        or not state["password"] or not state["otp"] or state["actions"]):
        raise SystemExit("OWNER_IDENTITY_PROOFS_INCOMPLETE__NO_ROLE_GRANTED")
    if not apienv.get("MIGRATION_DATABASE_URL"):
        raise SystemExit("MIGRATION_ROLE_NOT_CONFIGURED")
    invocation=os.environ.copy()
    invocation.update(apienv)
    invocation["PYTHONPATH"]=str(ROOT/"apps/api")
    args=[
        "/srv/hunter-ksa1-api-public/.venv/bin/python",
        "-m","nex_api.bootstrap",
        "--issuer",ISSUER,"--subject",state["subject"],
        "--tenant-name","Hunter KSA1 owner",
        "--email",OWNER,"--role","ADMIN",
    ]
    finish=subprocess.run(args,env=invocation,cwd=ROOT,capture_output=True,text=True,timeout=45)
    if finish.returncode:
        raise SystemExit("BOOTSTRAP_NOT_COMPLETED__PRIVATE_AUDIT_REVIEW")
    print("VERIFIED_OWNER_SUBJECT_BOUND_TO_ADMIN")
    print("ACTUAL_BROWSER_PASSWORD_TOTP_LOGIN_STILL_REQUIRED")
    print("SIGNIN=https://bot.ndsp.app/account-access/")
PY
