import asyncio
from pathlib import Path
import asyncpg
row=next(v.partition("=")[2] for v in Path("/etc/hunter-ksa1-backend/db-connections.env").read_text().splitlines() if v.startswith("DATABASE_URL="))
url=row.replace("postgresql+asyncpg://","postgresql://")
async def main():
    try:
        connection=await asyncpg.connect(dsn=url,timeout=3)
        print("ISOLATED_DB_SELECT",await connection.fetchval("SELECT 1"))
        await connection.close()
    except Exception as e:
        print("ISOLATED_DB_ERROR_CLASS",type(e).__name__,"SQLSTATE",getattr(e,"sqlstate",None))
asyncio.run(main())
