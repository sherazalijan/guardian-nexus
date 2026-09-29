"""Phase 8 — SQLAlchemy ORM models for Guardian Nexus persistence.

Design notes (read before modifying):

1. This module persists the OUTPUT of existing Pydantic models
   (app.models.*) — it does not replace or duplicate any business logic.
   Every table here mirrors an existing Pydantic model 1:1 as closely as
   practical. Where the existing model already exposes a UUID/str id
   (event_id, evidence_id, signal_id, etc.), that same id is reused as
   the primary key here instead of minting a new one, so a row can
   always be traced back to the exact object the service layer produced.

2. Category/severity/status/type fields are stored as plain `String`,
   not native Postgres ENUM types, and hold the `.value` of whatever
   StrEnum the domain model uses (e.g. SecurityCategory.value). This is
   a deliberate simplification: the app's enums (SecurityCategory,
   ThreatCategory, VoiceSignalType, ...) are still evolving across
   phases, and a native PG enum requires an ALTER TYPE migration every
   time a member is added/renamed. Plain strings + an index give 95% of
   the query benefit with none of the migration friction. Revisit if/
   when the enum sets stabilize.

3. `session_id` throughout is a `str` (matches `ProtectionService`,
   `SessionIntelligenceService`, etc., which all key sessions by the
   AssemblyAI-provided or generated `str` session id) — NOT a UUID
   foreign key to `sessions.id` typed as UUID. `sessions.id` is
   therefore also a `str` primary key, not a surrogate UUID, so joins
   stay simple and match what the in-memory services already use as
   their identity.

4. JSON is used for: nested/variable-shape data that has no query need
   of its own (risk_factors, evidence lists, metadata dicts,
   matched_patterns/matched_indicators). Everything that Threat Memory
   matching needs to filter/join on (category, signal_type, severity)
   is a real column, not buried in JSON. `JSONVariant` (app.db.base)
   compiles to native JSONB on Postgres and plain JSON elsewhere (e.g.
   sqlite in tests) — see that module's docstring.

5. `Uuid`/`_now_col()` use SQLAlchemy's generic `Uuid` type and
   `func.now()` (not the Postgres-only `postgresql.UUID` type or the raw
   SQL string `"now()"`) so this schema — and the Phase 8 test suite —
   runs unmodified against sqlite as well as Postgres.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONVariant


def _uuid_col():
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _now_col():
    return mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Clients / Sessions
# ---------------------------------------------------------------------------


class Client(Base):
    """Minimal identity record. Not an auth system — just enough of an
    anchor to group sessions by the same protected person/device, per the
    Phase 8 spec's "do not overbuild authentication" instruction."""

    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = _uuid_col()
    external_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = _now_col()

    sessions: Mapped[list["Session"]] = relationship(back_populates="client")


class Session(Base):
    """A monitored Guardian interaction. Keyed by the same `str` session_id
    every in-memory service (ProtectionService, SessionIntelligenceService,
    ...) already uses — see module docstring, point 3."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("clients.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    highest_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    highest_severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = _now_col()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=datetime.utcnow
    )

    client: Mapped[Client | None] = relationship(back_populates="sessions")


# ---------------------------------------------------------------------------
# Transcript
# ---------------------------------------------------------------------------


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    __table_args__ = (
        Index("ix_transcript_segments_session_seq", "session_id", "sequence"),
    )

    id: Mapped[uuid.UUID] = _uuid_col()
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    is_final: Mapped[bool] = mapped_column(Boolean)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now_col()


# ---------------------------------------------------------------------------
# Risk Engine output (RiskResult)
# ---------------------------------------------------------------------------


class RiskEvent(Base):
    __tablename__ = "risk_events"

    id: Mapped[uuid.UUID] = _uuid_col()
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id"), index=True
    )
    score: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    evidence_state: Mapped[str] = mapped_column(String(16))
    explanation: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(String(16))
    risk_factors: Mapped[list] = mapped_column(JSONVariant, default=list)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now_col()


# ---------------------------------------------------------------------------
# Evidence (EvidenceItem, session_intelligence)
# ---------------------------------------------------------------------------


class Evidence(Base):
    __tablename__ = "evidence_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(32), default="transcript")
    text: Mapped[str] = mapped_column(Text)
    signal: Mapped[str] = mapped_column(String(128), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16))
    risk_score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = _now_col()


# ---------------------------------------------------------------------------
# Protection events (ProtectionEvent) + Phase1 timeline (TimelineEvent)
# ---------------------------------------------------------------------------


class ProtectionEventRow(Base):
    __tablename__ = "protection_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event_type: Mapped[str] = mapped_column(String(48), index=True)
    severity: Mapped[str] = mapped_column(String(16))
    risk_score: Mapped[float] = mapped_column(Float)
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64), index=True)
    evidence: Mapped[list] = mapped_column(JSONVariant, default=list)
    recommended_action: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = _now_col()


class TimelineEventRow(Base):
    """Phase 1 `TimelineEvent` (label/category/severity/detail/metadata) —
    distinct from `IncidentTimelineEvent` (see `IncidentEventRow` below),
    which carries a richer, differently-shaped Phase 2 payload."""

    __tablename__ = "timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    label: Mapped[str] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict] = mapped_column(JSONVariant, default=dict)
    created_at: Mapped[datetime] = _now_col()


# ---------------------------------------------------------------------------
# Session Intelligence: risk history + incident timeline + summary
# ---------------------------------------------------------------------------


class RiskHistoryEntryRow(Base):
    __tablename__ = "risk_history_entries"

    id: Mapped[uuid.UUID] = _uuid_col()
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    previous_score: Mapped[float] = mapped_column(Float)
    new_score: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(16))
    state: Mapped[str] = mapped_column(String(16))
    trigger: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = _now_col()


class IncidentEventRow(Base):
    """Phase 2 `IncidentTimelineEvent`."""

    __tablename__ = "incident_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event_type: Mapped[str] = mapped_column(String(48), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_ids: Mapped[list] = mapped_column(JSONVariant, default=list)
    created_at: Mapped[datetime] = _now_col()


class SessionSummaryRow(Base):
    """One row per session, written once at session end (Phase 1 +
    Phase 2/3 additive keys flattened into columns/JSON)."""

    __tablename__ = "session_summaries"

    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id"), primary_key=True
    )
    session_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    session_ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    highest_risk_score: Mapped[float] = mapped_column(Float)
    final_risk_score: Mapped[float] = mapped_column(Float)
    highest_severity: Mapped[str] = mapped_column(String(16))
    detected_categories: Mapped[list] = mapped_column(JSONVariant, default=list)
    detected_signals: Mapped[list] = mapped_column(JSONVariant, default=list)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    critical_alert_count: Mapped[int] = mapped_column(Integer, default=0)
    recommended_final_action: Mapped[str] = mapped_column(Text)
    # Phase 2/3 additive fields (evidence_count, primary_category,
    # risk_escalation_count, final_state, intervention_count,
    # critical_intervention_occurred) — kept as JSON rather than columns
    # since they were bolted onto the WS payload additively too.
    extra: Mapped[dict] = mapped_column(JSONVariant, default=dict)
    created_at: Mapped[datetime] = _now_col()


# ---------------------------------------------------------------------------
# Voice Intelligence
# ---------------------------------------------------------------------------


class VoiceSignalRow(Base):
    __tablename__ = "voice_signals"
    __table_args__ = (
        Index("ix_voice_signals_session_type", "session_id", "signal_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id"), index=True
    )
    signal_type: Mapped[str] = mapped_column(String(64), index=True)
    category: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(16))
    evidence_text: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(64))
    signal_metadata: Mapped[dict] = mapped_column(JSONVariant, default=dict)
    created_at: Mapped[datetime] = _now_col()


class VoicePatternRow(Base):
    __tablename__ = "voice_patterns"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id"), index=True
    )
    pattern_type: Mapped[str] = mapped_column(String(64), index=True)
    signals: Mapped[list] = mapped_column(JSONVariant, default=list)
    confidence: Mapped[float] = mapped_column(Float)
    evidence: Mapped[list] = mapped_column(JSONVariant, default=list)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now_col()


# ---------------------------------------------------------------------------
# Interventions: Phase 3 policy-engine Intervention + Phase 5 InterventionEvent
# ---------------------------------------------------------------------------


class InterventionRow(Base):
    """Phase 3 `Intervention` (InterventionPolicyService) — the
    acknowledgeable, cooldown/escalation-managed lifecycle object."""

    __tablename__ = "interventions"

    intervention_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    priority: Mapped[str] = mapped_column(String(16), index=True)
    risk_score: Mapped[float] = mapped_column(Float)
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recommended_action: Mapped[str] = mapped_column(Text)
    requires_acknowledgement: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), index=True)
    source_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence: Mapped[list] = mapped_column(JSONVariant, default=list)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalated_from: Mapped[str | None] = mapped_column(String(64), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = _now_col()


class InterventionEventRow(Base):
    """Phase 5 `InterventionEvent` (real-time intervention engine /
    `intervention_alert` frame) — deliberately a separate table from
    `InterventionRow`: the two models are unrelated per Phase 5's own
    docstring (`app.models.intervention_engine`)."""

    __tablename__ = "intervention_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    level: Mapped[str] = mapped_column(String(16), index=True)
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(64))
    risk_score: Mapped[float] = mapped_column(Float)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = _now_col()


# ---------------------------------------------------------------------------
# Guardian Alerts (Phase 6)
# ---------------------------------------------------------------------------


class GuardianAlertRow(Base):
    __tablename__ = "guardian_alerts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sessions.id"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    risk_score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(64))
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = _now_col()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=datetime.utcnow
    )


class GuardianAlertEventRow(Base):
    __tablename__ = "guardian_alert_events"

    id: Mapped[uuid.UUID] = _uuid_col()
    alert_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("guardian_alerts.id"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(32))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    details: Mapped[dict] = mapped_column(JSONVariant, default=dict)
    created_at: Mapped[datetime] = _now_col()
