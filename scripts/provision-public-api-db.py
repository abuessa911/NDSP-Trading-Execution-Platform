#!/usr/bin/env python3
"""Create a separate Hunter production-candidate API database on 16/hunterprod.

Does NOT create a user/admin account, nor grant trading permissions.
"""
from pathlib import Path
import os, secrets, subprocess
from urllib.parse import quote

config=Path("/etc/hunter-ksa1-identity/public-api-db.env")
if config.exists():
    raise SystemExit("EXISTING_PUBLIC_API_DB_CONFIG; ABORT")
ls=subprocess.run(["pg_lsclusters","-h"],check=True,capture_output=True,text=True).stdout
if not any(x.split()[:3]==["16","hunterprod","55433"] and "online" in x.split() for x in ls.splitlines()):
    raise SystemExit("PUBLIC_API_DB_CLUSTER_NOT_ISOLATED")
pa,pm=secrets.token_urlsafe(40),secrets.token_urlsafe(40)
sql=(f"CREATE ROLE nex_app LOGIN PASSWORD '{pa}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;\n"
    f"CREATE ROLE nex_migrator LOGIN PASSWORD '{pm}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;\n"
    "CREATE DATABASE nex OWNER nex_migrator TEMPLATE template0 ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C';\n")
cmd=["runuser","-u","postgres","--","psql","-X","-q","-v","ON_ERROR_STOP=1","-p","55433","-d","postgres"]
a=subprocess.run(cmd,input=sql,capture_output=True,text=True)
if a.returncode:
    raise SystemExit("PUBLIC_API_PROVISION_FAILED")
cmd[-1]="nex"
permissions="""GRANT CONNECT ON DATABASE nex TO nex_app, nex_migrator;
GRANT USAGE ON SCHEMA public TO nex_app;
GRANT USAGE, CREATE ON SCHEMA public TO nex_migrator;
ALTER DEFAULT PRIVILEGES FOR ROLE nex_migrator IN SCHEMA public GRANT SELECT ON TABLES TO nex_app;
"""
b=subprocess.run(cmd,input=permissions,capture_output=True,text=True)
if b.returncode:raise SystemExit("PUBLIC_API_ROLE_GRANTS_FAILED")
fd=os.open(config,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,"w") as file:
    file.write("DATABASE_URL=postgresql+asyncpg://nex_app:"+quote(pa)+"@127.0.0.1:55433/nex\n")
    file.write("MIGRATION_DATABASE_URL=postgresql+asyncpg://nex_migrator:"+quote(pm)+"@127.0.0.1:55433/nex\n")
print("SEPARATE_M1_CANDIDATE_DATABASE_READY_PORT_55433_NO_USER_ACCOUNTS")
