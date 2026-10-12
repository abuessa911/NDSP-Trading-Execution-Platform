from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import async_engine_from_config

PROJECT_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from nex_api.config import Settings  # noqa: E402
from nex_api.database import normalize_database_url  # noqa: E402
from nex_api.models import Base  # noqa: E402
from nex_api.secrets import build_secret_provider, resolve_configuration  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url() -> str:
    settings = Settings()
    settings = resolve_configuration(settings, build_secret_provider(settings))
    url = settings.migration_database_url
    if not url:
        raise RuntimeError("Explicit MIGRATION_DATABASE_URL is required; no runtime fallback.")
    return normalize_database_url(url)


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        transaction_per_migration=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = database_url()
    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        safe_role = (await connection.execute(text(
            "SELECT current_user='nex_migrator' AND NOT rolsuper AND NOT rolbypassrls "
            "FROM pg_roles WHERE rolname=current_user"
        ))).scalar()
        if not safe_role:
            raise RuntimeError("Migrations require the non-superuser nex_migrator role.")
        await connection.rollback()
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())