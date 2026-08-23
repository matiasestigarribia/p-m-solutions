"""Async database engine for Neon PostgreSQL.

Engine is created lazily on first call to get_engine() — importing this module
is safe even when PM_DATABASE_URL is unset (dev / testing without DB).
PgBouncer/Neon pooler safety: statement_cache_size=0, pool_pre_ping, pool_recycle.
"""
from __future__ import annotations

from typing import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.core.settings import settings

_engine: AsyncEngine | None = None


def normalize_database_url(url: str) -> str:
    """Use asyncpg for standard PostgreSQL/Neon URLs."""
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    parsed = urlsplit(url)
    if parsed.scheme != "postgresql+asyncpg":
        return url
    query = parse_qsl(parsed.query, keep_blank_values=True)
    query = [
        ("ssl" if key == "sslmode" else key, value)
        for key, value in query
        if key != "channel_binding"
    ]
    return urlunsplit(parsed._replace(query=urlencode(query, doseq=True)))


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        if not settings.database_url:
            raise RuntimeError(
                "PM_DATABASE_URL is not configured. "
                "Set PM_DATABASE_URL and PM_ENABLE_DATABASE=true."
            )
        _engine = create_async_engine(
            normalize_database_url(settings.database_url),
            echo=False,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={"statement_cache_size": 0},
        )
    return _engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        yield session
