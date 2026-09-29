from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Cross-dialect JSON column type: compiles to real JSONB on Postgres
# (keeping its indexing/containment-query benefits in production) and to
# plain JSON everywhere else — in particular sqlite, which is what the
# Phase 8 test suite runs against (see backend/tests/persistence/conftest.py)
# rather than requiring a live Postgres instance for tests to run at all.
JSONVariant = JSON().with_variant(JSONB(), "postgresql")
