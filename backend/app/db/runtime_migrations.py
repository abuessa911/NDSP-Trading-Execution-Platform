from sqlalchemy import inspect, text

from app.db.session import engine


def ensure_runtime_columns() -> None:
    inspector = inspect(engine)

    if not inspector.has_table("bot_settings"):
        return

    columns = {column["name"] for column in inspector.get_columns("bot_settings")}

    if "market_type" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE bot_settings ADD COLUMN market_type VARCHAR(20) DEFAULT 'spot'")
            )
