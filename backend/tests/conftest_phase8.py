"""Shared fixtures for the Phase 8 persistence / Threat Memory tests.

Runs against an in-memory sqlite database via aiosqlite rather than a
real Postgres instance — see `app.db.base.JSONVariant` and the `Uuid`
column type used throughout `app.db.models` / `app.db.threat_memory_models`
for why this schema is portable across both. Production still talks to
Postgres via `DATABASE_URL` / `app.core.database`; this fixture never
touches that.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
# Import every model module so their tables register on Base.metadata
# before create_all runs — mirrors what alembic/env.py already does for
# real migrations.
from app.db import models as _db_models  # noqa: F401
from app.db import threat_memory_models as _threat_models  # noqa: F401


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sessionmaker = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    session = sessionmaker()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()
