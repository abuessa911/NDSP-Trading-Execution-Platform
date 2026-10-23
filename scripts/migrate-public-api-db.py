#!/usr/bin/env python3
"""Run migrations ONLY against isolated Hunter candidate PostgreSQL 55433."""
import os,subprocess
from pathlib import Path
from urllib.parse import urlsplit
root=Path("/opt/hunter_ksa1-bot")
settings={}
for row in Path("/etc/hunter-ksa1-identity/public-api-db.env").read_text().splitlines():
    name,_,value=row.partition("=")
    if name in {"DATABASE_URL","MIGRATION_DATABASE_URL"}:settings[name]=value
for name in ("DATABASE_URL","MIGRATION_DATABASE_URL"):
    u=urlsplit(settings.get(name,""))
    if (u.hostname,u.port,u.path)!=("127.0.0.1",55433,"/nex"):
        raise SystemExit("REFUSED_WRONG_API_DATABASE")
env=os.environ.copy()
env.update(settings)
env["PYTHONPATH"]=str(root/"apps/api")
env["ENVIRONMENT"]="production"
run=subprocess.run([str(root/".venv-qa/bin/python"),"-m","alembic","-c","apps/api/alembic.ini","upgrade","head"],env=env,cwd=root,text=True,capture_output=True)
if run.returncode:raise SystemExit("PUBLIC_API_MIGRATIONS_FAILED; inspect restricted database privately")
print("ISOLATED_M1_CANDIDATE_MIGRATIONS_PASS")
