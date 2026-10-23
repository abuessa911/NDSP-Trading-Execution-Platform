#!/usr/bin/env python3
"""Short-lived Basic Auth smoke account; strict cleanup even on failed test.

Tests real public HTTPS, API forwarding, Set-Cookie, CSRF origin, and Keycloak
authorization page. Never logs password/hash/cookie/token.
"""
from pathlib import Path
import os,secrets,subprocess,tempfile
from urllib.parse import urlsplit
import httpx

htpasswd=Path("/etc/hunter-ksa1-gateway/htpasswd")
initial=htpasswd.read_bytes()
if not initial or not initial.endswith(b"\n"):
    raise SystemExit("UNEXPECTED_GATEWAY_CREDENTIAL_FILE")
username="hunter-smoke-"+secrets.token_hex(6)
password=secrets.token_urlsafe(40)
result=subprocess.run(["/usr/bin/htpasswd","-n","-i","-B",username],
                      input=password+"\n",capture_output=True,text=True)
if result.returncode or not result.stdout.startswith(username+":"):
    raise SystemExit("COULD_NOT_CREATE_EPHEMERAL_BASIC_ACCOUNT")
added=result.stdout.encode()
expected=initial+added
def replace(data):
    fd,p=tempfile.mkstemp(dir=htpasswd.parent,prefix=".hunter-basic-qa-")
    try:
        os.fchmod(fd,0o640)
        os.fchown(fd,0,33)
        with os.fdopen(fd,"wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(p,htpasswd)
    finally:
        if os.path.exists(p):os.unlink(p)

replace(expected)
try:
    origin="https://bot.ndsp.app"
    with httpx.Client(auth=(username,password),timeout=8,trust_env=False,
                      follow_redirects=False) as client:
        response=client.get(origin+"/api/health/auth")
        if response.status_code!=200:
            raise RuntimeError("PUBLIC_AUTH_CONFIG_NOT_REACHABLE")
        data=response.json()
        if not (data.get("browser_login_enabled") and data.get("administrator_mfa_configured")):
            raise RuntimeError("AUTH_BUTTONS_NOT_CONFIGURED")
        print("PUBLIC_M1_AUTH_CONFIG_PASS")

        for admin in (False,True):
            result=client.post(origin+"/api/v1/auth/login",
                               params={"admin_mfa":str(admin).lower()},
                               headers={"Origin":origin})
            if result.status_code!=200:
                raise RuntimeError("OIDC_START_NOT_READY:"+("ADMIN" if admin else "USER"))
            cookie=result.headers.get("set-cookie","")
            if not ("__Secure-nex_oidc=" in cookie and "Secure" in cookie
                    and "HttpOnly" in cookie and "Path=/api" in cookie):
                raise RuntimeError("OIDC_FLOW_COOKIE_NOT_SECURE")
            url=result.json().get("authorization_url","")
            uri=urlsplit(url)
            if uri.scheme!="https" or uri.netloc!="bot.ndsp.app" or not uri.path.startswith("/oidc/realms/hunter-m1/"):
                raise RuntimeError("OIDC_AUTHORIZATION_REDIRECT_NOT_PINNED")
            landing=client.get(url)
            if landing.status_code!=200:
                raise RuntimeError("OIDC_PROVIDER_LOGIN_FORM_NOT_READY")
            print("PUBLIC_M1_"+("ADMIN_TOTP" if admin else "USER")+"_LOGIN_INITIATION_PASS")
        unauthenticated=client.get(origin+"/api/v1/auth/session")
        if unauthenticated.status_code!=401:
            raise RuntimeError("UNVERIFIED_IDENTITY_GAINED_ACCESS")
        print("M1_NO_AUTH_SESSION_FAIL_CLOSED_PASS")
finally:
    current=htpasswd.read_bytes()
    if current==expected:
        replace(initial)
    elif added in current:
        replace(current.replace(added,b"",1))
    else:
        raise RuntimeError("SMOKE_ACCOUNT_REVIEW_REQUIRED: credentials changed concurrently")
print("EPHEMERAL_TEST_GATE_CREDENTIAL_REMOVED")
