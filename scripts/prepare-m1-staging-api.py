#!/usr/bin/env python3
"""Provision a private, test-only FastAPI configuration for the Hunter bot."""
import base64,os,secrets
from pathlib import Path
from urllib.parse import urlsplit
from cryptography.fernet import Fernet
private=Path("/etc/hunter-ksa1-backend")
target=private/"m1-staging.env"
if target.exists():raise SystemExit("REFUSED_EXISTING_M1_STAGE")
values={}
for f in (private/"db-connections.env",Path("/etc/hunter-ksa1-keycloak/admin-client.env")):
    for row in f.read_text().splitlines():
        name,sep,value=row.partition("=")
        if sep:values[name]=value
for name,port in (("DATABASE_URL",55432),("REDIS_URL",16391)):
    uri=urlsplit(values[name])
    if uri.hostname!="127.0.0.1" or uri.port!=port:raise SystemExit("STAGING_ISOLATION_REQUIRED")
issuer="https://localhost:18443/oidc/realms/nex-m1-test"
values.update({
 "ENVIRONMENT":"test","TRADING_MODE":"paper",
 "LIVE_TRADING_ENABLED":"false","GLOBAL_KILL_SWITCH":"true",
 "BINANCE_ALLOW_WITHDRAW":"false","M2A_PUBLIC_MARKET_ENABLED":"false",
 "OIDC_ISSUER":issuer,"OIDC_AUDIENCE":"nex-m1-browser",
 "OIDC_JWKS_URL":issuer+"/protocol/openid-connect/certs",
 "OIDC_BROWSER_LOGIN_ENABLED":"true",
 "OIDC_CLIENT_ID":"nex-m1-browser",
 "OIDC_REDIRECT_URI":"https://localhost:18443/api/v1/auth/callback",
 "OIDC_POST_LOGOUT_REDIRECT_URI":"https://localhost:18443/",
 "OIDC_ADMIN_MFA_POLICY":"keycloak-password-totp-v1",
 "OIDC_ADMIN_MFA_MAX_AGE":"600",
 "NEX_SESSION_ENCRYPTION_KEY":Fernet.generate_key().decode(),
 "SSL_CERT_FILE":"/etc/hunter-ksa1-keycloak/tls/cert.pem",
 "NO_PROXY":"127.0.0.1,localhost",
})
assert "OIDC_ADMIN_MFA_CLIENT_SECRET" in values
fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,"w") as out:
    for key,value in values.items():
        if "\n" in value:raise SystemExit("INVALID_ENV_LINE")
        out.write(key+"="+value+"\n")
print("ISOLATED_M1_STAGING_CONFIG_PREPARED")
