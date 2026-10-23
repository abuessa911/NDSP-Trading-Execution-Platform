#!/usr/bin/env python3
"""Provision bot-only public-hostname Keycloak (inactive until gates pass).

Creates a separate Keycloak database and root-only runtime credentials.
Does not touch NDSP clusters or the existing synthetic test realm.
"""
from pathlib import Path
import os, secrets, subprocess
base=Path("/etc/hunter-ksa1-identity")
env=base/"public-keycloak.env"
if env.exists() or Path("/opt/hunter-keycloak-public").exists():
    raise SystemExit("REFUSED_EXISTING_PUBLIC_IDENTITY")
cluster=subprocess.run(["pg_lsclusters","-h"],capture_output=True,text=True,check=True).stdout
if not any(row.split()[:3]==["16","hunter","55432"] and "online" in row.split() for row in cluster.splitlines()):
    raise SystemExit("REFUSED_NO_ISOLATED_HUNTER_CLUSTER")
pw=secrets.token_urlsafe(48)
bootstrap=secrets.token_urlsafe(48)
statements=(f"CREATE ROLE hunter_identity LOGIN PASSWORD '{pw}' NOSUPERUSER NOCREATEROLE NOCREATEDB NOINHERIT NOBYPASSRLS;\n"
            "CREATE DATABASE hunter_identity OWNER hunter_identity TEMPLATE template0 ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C';\n")
p=subprocess.run(["runuser","-u","postgres","--","psql","-X","-q","-v","ON_ERROR_STOP=1","-p","55432","-d","postgres"],input=statements,text=True,capture_output=True)
if p.returncode:
    raise SystemExit("PUBLIC_IDENTITY_DB_PROVISION_FAILED")
base.mkdir(mode=0o700,parents=True,exist_ok=True)
os.chmod(base,0o700)
settings={
"KC_DB":"postgres",
"KC_DB_URL":"jdbc:postgresql://127.0.0.1:55432/hunter_identity",
"KC_DB_USERNAME":"hunter_identity",
"KC_DB_PASSWORD":pw,
"KC_BOOTSTRAP_ADMIN_USERNAME":"hunter-identity-bootstrap",
"KC_BOOTSTRAP_ADMIN_PASSWORD":bootstrap,
"KC_HOSTNAME":"https://bot.ndsp.app/oidc",
"KC_HTTP_RELATIVE_PATH":"/oidc",
"KC_HTTP_HOST":"127.0.0.1",
"KC_HTTP_PORT":"19485",
"KC_HTTP_ENABLED":"true",
"KC_PROXY_HEADERS":"xforwarded",
"KC_HEALTH_ENABLED":"true",
"KC_METRICS_ENABLED":"false",
"KC_CACHE":"local",
}
fd=os.open(env,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,"w") as f:
    for k,v in settings.items():
        f.write(f"{k}={v}\n")
print("BOT_ONLY_IDENTITY_DB_PREPARED; OUTSIDE_NDSP; NOT_PUBLICLY_ROUTED")
