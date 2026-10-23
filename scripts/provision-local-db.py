#!/usr/bin/env python3
"""One-time standalone PostgreSQL provisioning for hunter_ksa1 bot.
Works ONLY with the distinct PostgreSQL 16/hunter cluster on port 55432.
Never connects to the shared/main 5432 cluster.
"""
from pathlib import Path
import os
import secrets
import subprocess
from urllib.parse import quote

base = Path("/etc/hunter-ksa1-backend")
secrets_path = base / "db-connections.env"
if secrets_path.exists():
    raise SystemExit("REFUSED: existing credentials detected; no changes made")
clusters = subprocess.run(["pg_lsclusters", "-h"], capture_output=True, text=True, check=True).stdout
if not any(line.split()[:3] == ["16", "hunter", "55432"] and "online" in line.split() for line in clusters.splitlines()):
    raise SystemExit("REFUSED: isolated 16/hunter cluster not online on port 55432")
pw_app = secrets.token_urlsafe(32)
pw_migrate = secrets.token_urlsafe(32)
# Passwords are generated on the server and sent to psql by stdin; never printed or used in argv.
create = (
    f"CREATE ROLE nex_app LOGIN PASSWORD '{pw_app}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;\n"
    f"CREATE ROLE nex_migrator LOGIN PASSWORD '{pw_migrate}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;\n"
    "CREATE DATABASE nex OWNER nex_migrator TEMPLATE template0 ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C';\n"
)
cmd = ["runuser", "-u", "postgres", "--", "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-p", "55432", "-d", "postgres"]
result = subprocess.run(cmd, input=create, text=True, capture_output=True)
if result.returncode:
    raise SystemExit("FAILED: database provisioning returned an error; inspect isolated cluster manually")
grant = """GRANT CONNECT ON DATABASE nex TO nex_app, nex_migrator;
GRANT USAGE ON SCHEMA public TO nex_app;
GRANT USAGE, CREATE ON SCHEMA public TO nex_migrator;
ALTER DEFAULT PRIVILEGES FOR ROLE nex_migrator IN SCHEMA public GRANT SELECT ON TABLES TO nex_app;
"""
cmd[-1] = "nex"
result = subprocess.run(cmd, input=grant, text=True, capture_output=True)
if result.returncode:
    raise SystemExit("FAILED: isolated role grants; do not proceed to migrations")
base.mkdir(mode=0o700, parents=True, exist_ok=True)
os.chmod(base, 0o700)
urls = {
    "DATABASE_URL": f"postgresql+asyncpg://nex_app:{quote(pw_app)}@127.0.0.1:55432/nex",
    "MIGRATION_DATABASE_URL": f"postgresql+asyncpg://nex_migrator:{quote(pw_migrate)}@127.0.0.1:55432/nex",
}
fd = os.open(secrets_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
with os.fdopen(fd, "w") as file:
    for name, url in urls.items():
        file.write(f"{name}={url}\n")
print("ISOLATED_DATABASE_PROVISIONED: postgres 16/hunter port 55432, nex UTF8, restricted roles and root-only secret file")
