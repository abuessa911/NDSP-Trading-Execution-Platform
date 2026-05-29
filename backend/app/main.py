import time
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db.session import Base, engine
from app.api.routes import router
from app.api.advanced_routes import router as advanced_router
from app.core.config import settings


def wait_for_database(max_attempts: int = 30, delay_seconds: int = 2):
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            print("✅ Database is ready")
            return
        except OperationalError as exc:
            print(f"⏳ Waiting for database... attempt {attempt}/{max_attempts}")
            time.sleep(delay_seconds)

    raise RuntimeError("Database is not available after waiting")


wait_for_database()
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="MVP for NDSP Binance trading bot with dryrun-first safety.",
)

app.include_router(router)
app.include_router(advanced_router)


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "mode": settings.BINANCE_MODE,
        "docs": "/docs",
        "safety": "dryrun mode is recommended before testnet/live",
    }
