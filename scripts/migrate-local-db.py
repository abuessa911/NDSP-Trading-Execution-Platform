#!/usr/bin/env python3
"""Apply M1 migrations ONLY to the isolated hunter PostgreSQL cluster."""
from pathlib import Path
import os
import subprocess
import sys
from urllib.parse import urlsplit

root = Path("/opt/hunter_ksa1-bot")
cfg = Path("/etc/hunter-ksa1-backend/db-connections.env")
if not cfg.is_file():
    raise SystemExit("ISOLATED_DB_CONFIG_MISSING")
env = os.environ.copy()
for line in cfg.read_text().splitlines():
    name, sep, value = line.partition("=")
    if sep and name in ("DATABASE_URL", "MIGRATION_DATABASE_URL"):
        env[name] = value
for key in ("DATABASE_URL", "MIGRATION_DATABASE_URL"):
    u = urlsplit(env.get(key,""))
    if u.hostname != "127.0.0.1" or u.port != 55432 or u.path != "/nex":
        raise SystemExit("REFUSED: not the isolated hunter database")
env["PYTHONPATH"] = str(root / "apps/api")
env["ENVIRONMENT"] = "test"
result = subprocess.run(
    [str(root / ".venv-qa/bin/python"), "-m", "alembic", "-c", "apps/api/alembic.ini", "upgrade", "head"],
    env=env, cwd=root, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
)
# Alembic normally emits only revision IDs; never print exception tracebacks that might contain URLs.
if result.returncode:
    raise SystemExit("ISOLATED_MIGRATION_FAILED; inspect Alembic securely without exposing connection URLs")
print("ISOLATED_MIGRATIONS_PASS")
