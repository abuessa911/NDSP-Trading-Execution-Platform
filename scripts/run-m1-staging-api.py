#!/usr/bin/env python3
"""Start a private M1 API staging listener; fail closed on unsafe config."""
from pathlib import Path
import os,sys
from urllib.parse import urlsplit
path=Path("/etc/hunter-ksa1-backend/m1-staging.env")
if not path.is_file():raise SystemExit("M1_STAGING_NOT_PROVISIONED")
for row in path.read_text().splitlines():
    key,sep,value=row.partition("=")
    if sep:os.environ[key]=value
d=urlsplit(os.environ.get("DATABASE_URL",""))
r=urlsplit(os.environ.get("REDIS_URL",""))
if (d.hostname,d.port,d.path)!=("127.0.0.1",55432,"/nex"):
    raise SystemExit("REFUSED_DATABASE_TARGET")
if (r.hostname,r.port)!=("127.0.0.1",16391):
    raise SystemExit("REFUSED_REDIS_TARGET")
if (os.environ.get("ENVIRONMENT"),os.environ.get("LIVE_TRADING_ENABLED"),os.environ.get("GLOBAL_KILL_SWITCH"))!=("test","false","true"):
    raise SystemExit("REFUSED_UNSAFE_TRADING_MODE")
sys.path.insert(0,"/opt/hunter_ksa1-bot/apps/api")
import uvicorn
uvicorn.run("nex_api.main:app",host="127.0.0.1",port=19481,access_log=False,log_level="warning")
