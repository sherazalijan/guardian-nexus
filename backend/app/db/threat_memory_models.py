"""Phase 8 — Persistent Threat Memory schema.

This is the core deliverable of Phase 8 (see the phase brief: "the most
important part"). Five tables:

    Threat            — a persistent, named known threat
    ThreatPattern     — a reusable structured pattern belonging to a threat
    ThreatIndicator   — normalized signals/keywords that recognize a threat
    ThreatOccurrence  — where/when a threat appeared (Threat <-> Session)
    ThreatMatch        — a new session matched against a known threat

Everything a `Threat` is recognized BY is structured (ThreatIndicator
rows), not a text blob — see `app.services.threat_memory.matcher` for how
these are compared against a live session's accumulated voice-intelligence
signals (VoiceSignalType values) and protection categories
(SecurityCategory values), deterministically, with no embeddings and no
external APIs, per the phase brief's explicit constraint.

`ThreatMatch.match_score` is never used to replace or override the Risk
Engine's own 0-100 score. It IS, however, converted into an additional,
real `ThreatSignal` (see `app.services.persistence.hooks.
PersistenceHooks.build_known_threat_signals`) that is handed to the
*existing* `run_risk_engine()` alongside the signals it already computes
— the Risk Engine remains the sole place a score is produced, it simply
gets to see one more, real, structured piece of evidence.

`Uuid`/`JSONVariant` (see `app.db.base`) keep this schema portable across
Postgres (production) and sqlite (the Phase 8 test suite).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONVariant


def _uuid_col():
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Threat(Base):
    __tablename__ = "threats"

    id: Mapped[uuid.UUID] = _uuid_col()
    category: Mapped[str] = mapped_column(String(64), index=True)
    type: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(16), default="active", index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    occurrence_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=datetime.utcnow
    )

    patterns: Mapped[list["ThreatPattern"]] = relationship(
        back_populates="threat", cascade="all, delete-orphan"
    )
    indicators: Mapped[list["ThreatIndicator"]] = relationship(
        back_populates="threat", cascade="all, delete-orphan"
    )
    occurrences: Mapped[list["ThreatOccurrence"]] = relationship(
        back_populates="threat", cascade="all, delete-orphan"
    )


class ThreatPattern(Base):
    """A reusable, named pattern belonging to a threat — e.g.
    "BANK_IMPERSONATION", "OTP_REQUEST". Deliberately mirrors the shape of
    `app.services.voice_intelligence.correlation.CorrelationRule`
    (required signal types + any_of groups) so the SAME structural
    vocabulary a live session's `VoicePattern.pattern_type` already uses
    can be looked up here directly — no separate pattern taxonomy to keep
    in sync."""

    __tablename__ = "threat_patterns"
    __table_args__ = (
        UniqueConstraint("threat_id", "pattern_type", name="uq_threat_pattern"),
    )

    id: Mapped[uuid.UUID] = _uuid_col()
    threat_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("threats.id"), index=True
    )
    pattern_type: Mapped[str] = mapped_column(String(64), index=True)
    # VoiceSignalType values required for this pattern to be considered
    # present (mirrors CorrelationRule.required).
    required_signal_types: Mapped[list] = mapped_column(JSONVariant, default=list)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    threat: Mapped[Threat] = relationship(back_populates="patterns")


class ThreatIndicator(Base):
    """A single normalized signal that helps recognize a threat.

    `signal_type` reuses `VoiceSignalType` values where the indicator
    came from voice-intelligence detection (the common case); `category`
    reuses `SecurityCategory`/`ThreatCategory` values as a coarser
    fallback. `normalized_value` is free text run through the existing
    `app.services.normalization.normalize_indicator` for consistent
    matching, exactly like `ThreatSignal` deduplication already does.
    """

    __tablename__ = "threat_indicators"
    __table_args__ = (
        Index("ix_threat_indicators_threat_signal", "threat_id", "signal_type"),
    )

    id: Mapped[uuid.UUID] = _uuid_col()
    threat_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("threats.id"), index=True
    )
    signal_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    normalized_value: Mapped[str] = mapped_column(String(255))
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String(64), default="voice-intelligence-agent")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    threat: Mapped[Threat] = relationship(back_populates="indicators")


class ThreatOccurrence(Base):
    """Records that `threat_id` appeared in `session_id`. Lets Threat
    Memory answer "how many times has this appeared" / "when was it last
    observed" without recomputing from ThreatMatch history each time —
    `Threat.occurrence_count` / `last_seen_at` are updated alongside this
    row (see `app.services.threat_memory.repository.record_occurrence`)."""

    __tablename__ = "threat_occurrences"
    __table_args__ = (
        UniqueConstraint("threat_id", "session_id", name="uq_threat_occurrence_session"),
    )

    id: Mapped[uuid.UUID] = _uuid_col()
    threat_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("threats.id"), index=True
    )
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id"), index=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    threat: Mapped[Threat] = relationship(back_populates="occurrences")


class ThreatMatch(Base):
    """A live session recognized as resembling a known threat.

    `match_score` is 0.0-1.0, deterministic, computed by
    `app.services.threat_memory.matcher.score_match` — a weighted overlap
    between the session's accumulated voice-signal types / categories and
    the threat's `ThreatIndicator`/`ThreatPattern` rows. It never replaces
    the Risk Engine's own 0-100 score; see
    `app.services.persistence.hooks.PersistenceHooks.build_known_threat_signals`
    for how a match becomes one additional, real `ThreatSignal` fed back
    into the existing `run_risk_engine()`.
    """

    __tablename__ = "threat_matches"
    __table_args__ = (
        Index("ix_threat_matches_session", "session_id"),
        Index("ix_threat_matches_threat", "threat_id"),
    )

    id: Mapped[uuid.UUID] = _uuid_col()
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id"), index=True
    )
    threat_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("threats.id"), index=True
    )
    match_score: Mapped[float] = mapped_column(Float)
    matched_patterns: Mapped[list] = mapped_column(JSONVariant, default=list)
    matched_indicators: Mapped[list] = mapped_column(JSONVariant, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
