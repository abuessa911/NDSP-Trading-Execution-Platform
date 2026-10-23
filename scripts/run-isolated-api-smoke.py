#!/usr/bin/env python3
"""Isolated FastAPI smoke listener; no public proxy, no OIDC and no trading."""
from pathlib import Path
import os
import sys
from urllib.parse import urlsplit

root = Path("/opt/hunter_ksa1-bot")
sys.path.insert(0, str(root / "apps/api"))
for name in tuple(os.environ):
    if name.startswith(("OIDC_", "NEX_")) or name in {"DATABASE_URL", "MIGRATION_DATABASE_URL", "REDIS_URL"}:
        del os.environ[name]
for line in Path("/etc/hunter-ksa1-backend/db-connections.env").read_text().splitlines():
    name, eq, value = line.partition("=")
    if eq and name in ("DATABASE_URL", "REDIS_URL"):
        os.environ[name] = value
for name, port in [("DATABASE_URL", 55432), ("REDIS_URL", 16391)]:
    parsed = urlsplit(os.environ.get(name, ""))
    if parsed.hostname != "127.0.0.1" or parsed.port != port:
        raise SystemExit("REFUSED: backend dependency outside isolated localhost instance")
os.environ["ENVIRONMENT"] = "test"
os.environ["OIDC_BROWSER_LOGIN_ENABLED"] = "false"
os.environ["LIVE_TRADING_ENABLED"] = "false"
os.environ["GLOBAL_KILL_SWITCH"] = "true"
os.environ["TRADING_MODE"] = "paper"
os.environ["BINANCE_ALLOW_WITHDRAW"] = "false"
os.chdir(root)
import uvicorn
uvicorn.run("nex_api.main:app", host="127.0.0.1", port=19481, access_log=False, log_level="warning")
