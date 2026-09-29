"""Phase 8 — async SQLAlchemy engine/session setup.

Additive: nothing in the existing codebase imports this yet. Wiring it
into `app.api.routes` is done via `app.services.persistence.PersistenceHooks`
(see that module) so the WebSocket gateway's existing control flow is
untouched.

Uses PostgreSQL via asyncpg. Reads DATABASE_URL from Settings (added to
`app.core.config.Settings` — see INTEGRATION.md) rather than hardcoding
a connection string.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        return create_async_engine(settings.database_url, echo=False)
    return create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(), expire_on_commit=False, class_=AsyncSession
    )


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-style dependency / async-with helper.

    Guardian Nexus's persistence is invoked from a long-lived WebSocket
    handler, not per-HTTP-request, so most callers will do:

        async with get_sessionmaker()() as session:
            ...

    rather than depending on this generator. It's provided for symmetry
    and for any future HTTP routes that read persisted data.
    """
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session
