"""Alembic async migration environment for Neon PostgreSQL.

Reads PM_DATABASE_URL from settings (env var or .env). Requires asyncpg.
"""
from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import all models so Alembic can discover metadata
from app.models import Base  # noqa: F401 — ensures all models are registered
from app.models.company import Company  # noqa: F401
from app.models.contact_messages import ContactMessage  # noqa: F401
from app.models.mission import Mission  # noqa: F401
from app.models.products import Product  # noqa: F401
from app.models.purpose import Purpose  # noqa: F401
from app.models.users import User  # noqa: F401
from app.models.vision import Vision  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Resolve DB URL from settings; fall back to env var for direct CLI use.
try:
    from app.core.settings import settings as _settings

    _db_url = _settings.database_url
except Exception:
    _db_url = None

_db_url = _db_url or os.environ.get("PM_DATABASE_URL")
if not _db_url:
    raise RuntimeError(
        "PM_DATABASE_URL is required to run migrations. "
        "Set it via environment variable or .env file."
    )

if _db_url.startswith("postgres://"):
    _db_url = "postgresql+asyncpg://" + _db_url[len("postgres://"):]
elif _db_url.startswith("postgresql://"):
    _db_url = "postgresql+asyncpg://" + _db_url[len("postgresql://"):]
_parsed_url = urlsplit(_db_url)
if _parsed_url.scheme == "postgresql+asyncpg":
    _query = parse_qsl(_parsed_url.query, keep_blank_values=True)
    _query = [
        ("ssl" if key == "sslmode" else key, value)
        for key, value in _query
        if key != "channel_binding"
    ]
    _db_url = urlunsplit(_parsed_url._replace(query=urlencode(_query, doseq=True)))

config.set_main_option("sqlalchemy.url", _db_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
