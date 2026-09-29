"""Phase 8 — Threat Memory persistence operations.

Plain async functions over an `AsyncSession`, not a class — mirrors the
existing codebase's preference for stateless service functions
(`app.services.risk_engine.run_risk_engine`, `app.services.actions.
determine_action`, etc.) rather than introducing a new repository-object
convention.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.threat_memory_models import (
    Threat,
    ThreatIndicator,
    ThreatMatch,
    ThreatOccurrence,
    ThreatPattern,
)
from app.services.threat_memory.matcher import MatchResult, SessionSignature


async def get_active_threats(db: AsyncSession) -> list[Threat]:
    """Every threat eligible for matching, with indicators/patterns
    eager-loaded (matching is pure in-memory scoring — see
    `app.services.threat_memory.matcher` — so this is the only query per
    analysis pass, not one query per threat)."""
    stmt = (
        select(Threat)
        .where(Threat.status == "active")
        .options(selectinload(Threat.indicators), selectinload(Threat.patterns))
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _signature_of(threat: Threat) -> tuple[frozenset[str], frozenset[str]]:
    """The normalized (signal_type set, category set) a threat is
    recognized by — used both for live matching (indirectly, via
    `app.services.threat_memory.matcher`) and for exact-equivalence
    dedup checks (`find_equivalent_active_threat`)."""
    signal_types = frozenset(i.signal_type for i in threat.indicators if i.signal_type)
    categories = frozenset(i.category for i in threat.indicators if i.category)
    return signal_types, categories


async def find_equivalent_active_threat(
    db: AsyncSession, signature: SessionSignature
) -> Threat | None:
    """Deterministic dedup check for Phase 8 gap #7: "two identical
    CRITICAL sessions could create two separate Threat rows."

    An existing active threat is "equivalent" to `signature` when its
    normalized indicator signal_type set AND category set are each
    exactly equal to the candidate's (no embeddings, no fuzzy
    similarity — the phase brief is explicit about structured matching
    only). The caller (`app.services.persistence.hooks.PersistenceHooks.
    maybe_promote_threat`) uses this before calling
    `create_threat_from_session`; when a match is found here it should
    record an occurrence against the existing threat instead of creating
    a duplicate.
    """
    threats = await get_active_threats(db)
    for threat in threats:
        signal_types, categories = _signature_of(threat)
        if signal_types == signature.signal_types and categories == signature.categories:
            return threat
    return None


async def record_match(db: AsyncSession, session_id: str, match: MatchResult) -> ThreatMatch:
    row = ThreatMatch(
        id=uuid.uuid4(),
        session_id=session_id,
        threat_id=match.threat.id,
        match_score=match.score,
        matched_patterns=match.matched_pattern_types,
        matched_indicators=match.matched_indicator_ids,
    )
    db.add(row)
    await record_occurrence(db, threat_id=match.threat.id, session_id=session_id)
    return row


async def record_occurrence(
    db: AsyncSession, *, threat_id: uuid.UUID, session_id: str, now: datetime | None = None
) -> None:
    """Idempotent per (threat, session): a session that re-matches the
    same threat on a later transcript fragment does not inflate
    `occurrence_count` a second time — the unique constraint on
    `threat_occurrences` is the source of truth for that, so this checks
    existence first rather than relying on catching an IntegrityError."""
    now = now or datetime.now(timezone.utc)

    existing = await db.execute(
        select(ThreatOccurrence).where(
            ThreatOccurrence.threat_id == threat_id,
            ThreatOccurrence.session_id == session_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return

    db.add(
        ThreatOccurrence(
            id=uuid.uuid4(), threat_id=threat_id, session_id=session_id, occurred_at=now
        )
    )

    threat = await db.get(Threat, threat_id)
    if threat is not None:
        threat.occurrence_count += 1
        threat.last_seen_at = now


async def create_threat_from_session(
    db: AsyncSession,
    *,
    signature: SessionSignature,
    category: str,
    severity: str,
    confidence: float,
    title: str,
    description: str,
    pattern_type: str | None = None,
    source: str = "session-promotion",
    now: datetime | None = None,
) -> Threat:
    """Promote a session's detected signals into persistent Threat
    Memory. Called by `app.services.persistence.hooks.PersistenceHooks.
    maybe_promote_threat`, only for sessions that crossed a severity
    threshold with sufficient evidence, and only after that caller has
    already checked `find_equivalent_active_threat` — this function
    itself performs no dedup and will always insert a new `Threat` row
    when called, by design (see that method for the "when"/dedup policy;
    this stays purely "how").
    """
    now = now or datetime.now(timezone.utc)

    threat = Threat(
        id=uuid.uuid4(),
        category=category,
        type=pattern_type or category,
        title=title,
        description=description,
        severity=severity,
        confidence=confidence,
        status="active",
        first_seen_at=now,
        last_seen_at=now,
        occurrence_count=0,
    )
    db.add(threat)
    await db.flush()  # assign threat.id before children reference it

    for signal_type in sorted(signature.signal_types):
        db.add(
            ThreatIndicator(
                id=uuid.uuid4(),
                threat_id=threat.id,
                signal_type=signal_type,
                category=None,
                normalized_value=signal_type,
                weight=1.0,
                source=source,
            )
        )

    for category_value in sorted(signature.categories):
        db.add(
            ThreatIndicator(
                id=uuid.uuid4(),
                threat_id=threat.id,
                signal_type=None,
                category=category_value,
                normalized_value=category_value,
                weight=0.5,  # category indicators are coarser than a specific signal_type
                source=source,
            )
        )

    if pattern_type is not None:
        db.add(
            ThreatPattern(
                id=uuid.uuid4(),
                threat_id=threat.id,
                pattern_type=pattern_type,
                required_signal_types=sorted(signature.signal_types),
                weight=1.0,
            )
        )

    return threat
