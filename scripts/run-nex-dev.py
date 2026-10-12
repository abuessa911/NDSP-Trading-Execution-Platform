"""NEX preview starts without ambient managed/NDSP database or production secrets.

For development, connection URLs must be explicitly supplied as NEX_DEV_*.
The hosted isolated Compose tests do not use this launcher.
"""
import os
import subprocess

environment = {name: os.environ[name] for name in ("PATH", "HOME", "PORT") if name in os.environ}
environment["ENVIRONMENT"] = "development"
for name in ("DATABASE_URL", "MIGRATION_DATABASE_URL", "REDIS_URL"):
    environment[name] = os.environ.get("NEX_DEV_" + name, "")
for name in ("OIDC_ISSUER", "OIDC_AUDIENCE", "OIDC_JWKS_URL", "OIDC_CLIENT_ID",
             "OIDC_BROWSER_LOGIN_ENABLED", "OIDC_REDIRECT_URI", "OIDC_POST_LOGOUT_REDIRECT_URI",
             "NEX_SESSION_ENCRYPTION_KEY", "OIDC_CLIENT_SECRET", "SSL_CERT_FILE"):
    if name in os.environ:
        environment[name] = os.environ[name]
raise SystemExit(subprocess.call([
    "uv", "run", "--frozen", "--directory", "apps/api", "uvicorn", "nex_api.main:app",
    "--host", "0.0.0.0", "--port", environment.get("PORT", "8080"), "--reload", "--no-access-log",
], env=environment))