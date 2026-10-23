#!/usr/bin/env python3
"""Generate fail-closed public-hostname API settings for Hunter ONLY.

Does not provision an owner user or enable live trading.
"""
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
from cryptography.fernet import Fernet
import os
base=Path("/etc/hunter-ksa1-identity")
file=base/"public-api.env"
if file.exists():raise SystemExit("PUBLIC_M1_API_CONFIG_ALREADY_EXISTS")
entries={}
for src in (Path("/etc/hunter-ksa1-backend/db-connections.env"),
            base/"public-api-db.env",base/"public-mfa-client.env"):
    for row in src.read_text().splitlines():
        k,sep,v=row.partition("=")
        if sep:entries[k]=v
issuer="https://bot.ndsp.app/oidc/realms/hunter-m1"
for name in ("DATABASE_URL","MIGRATION_DATABASE_URL"):
    u=urlsplit(entries[name])
    if (u.hostname,u.port,u.path)!=("127.0.0.1",55433,"/nex"):
        raise SystemExit("PUBLIC_API_DB_MISMATCH")
r=urlsplit(entries["REDIS_URL"])
if (r.hostname,r.port)!=("127.0.0.1",16391):
    raise SystemExit("BOT_REDIS_ISOLATION_MISMATCH")
redis=urlunsplit((r.scheme,r.netloc,"/1",r.query,r.fragment))
values={
    "ENVIRONMENT":"production",
    "DATABASE_URL":entries["DATABASE_URL"],
    "REDIS_URL":redis,
    "TRADING_MODE":"paper",
    "LIVE_TRADING_ENABLED":"false",
    "GLOBAL_KILL_SWITCH":"true",
    "BINANCE_ALLOW_WITHDRAW":"false",
    "M2A_PUBLIC_MARKET_ENABLED":"false",
    "OIDC_ISSUER":issuer,
    "OIDC_AUDIENCE":"hunter-m1-browser",
    "OIDC_JWKS_URL":issuer+"/protocol/openid-connect/certs",
    "OIDC_BROWSER_LOGIN_ENABLED":"true",
    "OIDC_CLIENT_ID":"hunter-m1-browser",
    "OIDC_REDIRECT_URI":"https://bot.ndsp.app/api/v1/auth/callback",
    "OIDC_POST_LOGOUT_REDIRECT_URI":"https://bot.ndsp.app/",
    "OIDC_ADMIN_MFA_POLICY":"keycloak-password-totp-v1",
    "OIDC_ADMIN_MFA_CLIENT_ID":"hunter-m1-admin",
    "OIDC_ADMIN_MFA_CLIENT_SECRET":entries["OIDC_ADMIN_MFA_CLIENT_SECRET"],
    "OIDC_ADMIN_MFA_MAX_AGE":"600",
    "NEX_SESSION_ENCRYPTION_KEY":Fernet.generate_key().decode(),
    "NEX_SESSION_SECONDS":"1800",
    "NO_PROXY":"127.0.0.1,localhost",
}
fd=os.open(file,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,"w") as out:
    for k,v in values.items():
        if "\n" in v:raise SystemExit("UNSAFE_ENV_VALUE")
        out.write(f"{k}={v}\n")
print("M1_PUBLIC_HOSTNAME_API_CONFIG_PREPARED_NO_USERS_NO_TRADING")
