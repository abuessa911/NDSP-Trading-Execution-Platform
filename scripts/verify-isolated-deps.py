#!/usr/bin/env python3
"""Safe local readiness check. Reads only Hunter's private credentials."""
from pathlib import Path
import asyncio
import os
import sys
from urllib.parse import urlsplit

base = Path("/opt/hunter_ksa1-bot")
sys.path.insert(0, str(base / "apps/api"))
for line in Path("/etc/hunter-ksa1-backend/db-connections.env").read_text().splitlines():
    key, eq, value = line.partition("=")
    if eq and key in {"DATABASE_URL","REDIS_URL","MIGRATION_DATABASE_URL"}:
        os.environ[key] = value
dbu, ru = urlsplit(os.environ["DATABASE_URL"]), urlsplit(os.environ["REDIS_URL"])
if (dbu.hostname, dbu.port, dbu.path) != ("127.0.0.1",55432,"/nex"):
    raise SystemExit("WRONG_DATABASE_ISOLATION")
if (ru.hostname, ru.port) != ("127.0.0.1",16391):
    raise SystemExit("WRONG_REDIS_ISOLATION")
from nex_api.config import Settings
from nex_api.database import create_session_factory, database_is_available
from redis.asyncio import Redis

async def main():
    s = Settings(environment="test", oidc_browser_login_enabled=False)
    factory = create_session_factory(s)
    db_ok = await database_is_available(factory)
    if factory:
        await factory.kw["bind"].dispose()
    redis = Redis.from_url(s.redis_url, socket_connect_timeout=2, socket_timeout=2)
    try:
        redis_ok = bool(await redis.ping())
    except Exception:
        redis_ok = False
    finally:
        await redis.aclose()
    print(f"HUNTER_DB_READY={str(db_ok).lower()} HUNTER_REDIS_READY={str(redis_ok).lower()}")
    if not db_ok or not redis_ok:
        raise SystemExit(1)

if __name__ == "__main__":
    asyncio.run(main())
