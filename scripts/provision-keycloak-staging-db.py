#!/usr/bin/env python3
"""Provision dedicated Keycloak staging database in Hunter-only PG cluster.

Intentionally NOT a production provider or a public authentication service.
Passwords never appear in stdout or process arguments.
"""
from pathlib import Path
from urllib.parse import quote
import os
import secrets
import subprocess

config_dir = Path("/etc/hunter-ksa1-keycloak")
env_file = config_dir / "staging.env"
if env_file.exists():
    raise SystemExit("REFUSED_EXISTING_KEYCLOAK_CREDENTIALS")
rows = subprocess.run(["pg_lsclusters","-h"],capture_output=True,text=True,check=True).stdout
if not any(r.split()[:3] == ["16","hunter","55432"] and "online" in r.split() for r in rows.splitlines()):
    raise SystemExit("REFUSED_NO_ISOLATED_POSTGRES")
password = secrets.token_urlsafe(40)
bootstrap = secrets.token_urlsafe(40)
sql = (
    f"CREATE ROLE hunter_keycloak LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;\n"
    "CREATE DATABASE hunter_keycloak OWNER hunter_keycloak TEMPLATE template0 ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C';\n"
)
result = subprocess.run(
    ["runuser","-u","postgres","--","psql","-X","-q","-v","ON_ERROR_STOP=1","-p","55432","-d","postgres"],
    input=sql, capture_output=True, text=True
)
if result.returncode:
    raise SystemExit("ISOLATED_KEYCLOAK_DATABASE_PROVISION_FAILED")
config_dir.mkdir(parents=True,mode=0o700,exist_ok=True)
os.chmod(config_dir,0o700)
settings = {
    "KC_DB":"postgres",
    "KC_DB_URL":"jdbc:postgresql://127.0.0.1:55432/hunter_keycloak",
    "KC_DB_USERNAME":"hunter_keycloak",
    "KC_DB_PASSWORD":password,
    "KC_BOOTSTRAP_ADMIN_USERNAME":"hunter-staging-admin",
    "KC_BOOTSTRAP_ADMIN_PASSWORD":bootstrap,
    "KC_HOSTNAME":"https://localhost:18443/oidc",
    "KC_HTTP_RELATIVE_PATH":"/oidc",
    "KC_HTTP_HOST":"127.0.0.1",
    "KC_HTTP_PORT":"19482",
    "KC_HTTP_ENABLED":"true",
    "KC_PROXY_HEADERS":"xforwarded",
    "KC_HEALTH_ENABLED":"true",
    "KC_METRICS_ENABLED":"false",
    "KC_CACHE":"local",
}
fd=os.open(env_file,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,"w") as stream:
    for name,value in settings.items():
        stream.write(f"{name}={value}\n")
print("HUNTER_KEYCLOAK_STAGING_POSTGRES_PROVISIONED_ON_55432")
