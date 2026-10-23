#!/usr/bin/env python3
"""Idempotent isolated M1 synthetic ADMIN provisioning, no user production data."""
from pathlib import Path
import os,subprocess
root=Path("/opt/hunter_ksa1-bot")
env=os.environ.copy()
for row in Path("/etc/hunter-ksa1-backend/m1-staging.env").read_text().splitlines():
    key,sep,value=row.partition("=")
    if sep:env[key]=value
env["PYTHONPATH"]=str(root/"apps/api")
if env.get("ENVIRONMENT")!="test" or env.get("OIDC_ISSUER")!="https://localhost:18443/oidc/realms/nex-m1-test":
    raise SystemExit("REFUSED_NON_TEST_IDENTITY")
argv=[str(root/".venv-qa/bin/python"),"-m","nex_api.bootstrap",
      "--issuer",env["OIDC_ISSUER"],
      "--subject","22222222-2222-4222-8222-222222222202",
      "--tenant-name","Hunter isolated M1 admin test",
      "--email","nex-test-admin@nex.example.test",
      "--role","ADMIN"]
result=subprocess.run(argv,cwd=root,env=env,capture_output=True,text=True)
if result.returncode:
    print("STAGING_ADMIN_BOOTSTRAP_NOT_COMPLETED")
else:
    print("STAGING_ADMIN_TENANT_PROVISIONED")
