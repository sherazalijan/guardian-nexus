"""Models for Guardian Nexus Session Intelligence (Phase 2).

These models sit one layer above `app.models.protection`: they turn the
existing Protection Service / Risk Engine output, accumulated over a
whole session, into the evidence + risk-history + incident-timeline +
session-summary contract the frontend will eventually render. Nothing
here recalculates risk or re-detects threats -- see
`app.services.session_intelligence` for how these are populated.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.models.enums import ThreatSeverity
from app.models.protection import ProtectionState, SecurityCategory


class EvidenceSource(StrEnum):
    """Where a piece of evidence came from.

    Currently always the live transcript; kept as an enum so a future
    source doesn't require a breaking model change.
    """

    TRANSCRIPT = "transcript"


class EvidenceItem(BaseModel):
    """One piece of actual evidence from the session.

    Always traceable to a real `ThreatSignal` produced by the existing
    scam detector -- never fabricated. See
    `app.services.session_intelligence.evidence.extract_evidence`.
    """

    evidence_id: UUID = Field(default_factory=uuid4)
    session_id: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: EvidenceSource = EvidenceSource.TRANSCRIPT
    text: str = Field(min_length=1)
    signal: str = Field(min_length=1)
    category: SecurityCategory
    severity: ThreatSeverity
    risk_score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)


class RiskHistoryTrigger(StrEnum):
    """Why a `RiskHistoryEntry` was recorded."""

    INITIAL = "initial"
    RISK_INCREASE = "risk_increase"
    RISK_DECREASE = "risk_decrease"
    SEVERITY_CHANGE = "severity_change"
    CRITICAL_ESCALATION = "critical_escalation"


class RiskHistoryEntry(BaseModel):
    """One meaningful transition in the session's risk score/severity.

    Only recorded when the score or severity actually changed -- see
    `app.services.session_intelligence.risk_history`.
    """

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    previous_score: float = Field(ge=0.0, le=100.0)
    new_score: float = Field(ge=0.0, le=100.0)
    severity: ThreatSeverity
    state: ProtectionState
    trigger: RiskHistoryTrigger


class IncidentEventType(StrEnum):
    """The kind of entry on the incident timeline."""

    SESSION_STARTED = "session_started"
    EVIDENCE_DETECTED = "evidence_detected"
    THREAT_DETECTED = "threat_detected"
    RISK_ESCALATED = "risk_escalated"
    RISK_DECREASED = "risk_decreased"
    WARNING = "warning"
    CRITICAL_ALERT = "critical_alert"
    RECOMMENDED_ACTION = "recommended_action"
    STATE_CHANGED = "state_changed"


class IncidentTimelineEvent(BaseModel):
    """One chronological entry on the session's incident timeline."""

    timeline_event_id: UUID = Field(default_factory=uuid4)
    session_id: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: IncidentEventType
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    severity: ThreatSeverity | None = None
    risk_score: float | None = Field(default=None, ge=0.0, le=100.0)
    category: SecurityCategory | None = None
    evidence_ids: list[UUID] = Field(default_factory=list)


class SessionIntelligence(BaseModel):
    """The current, full security state of a session.

    Composed from the Protection Service's existing state plus this
    phase's evidence/risk-history/incident-timeline -- see
    `app.services.session_intelligence.SessionIntelligenceService.snapshot`.
    """

    session_id: str = Field(min_length=1)
    started_at: datetime
    updated_at: datetime
    current_state: ProtectionState
    current_risk_score: float = Field(ge=0.0, le=100.0)
    highest_risk_score: float = Field(ge=0.0, le=100.0)
    highest_severity: ThreatSeverity
    primary_category: SecurityCategory
    categories: list[SecurityCategory] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    timeline: list[IncidentTimelineEvent] = Field(default_factory=list)
    warnings: int = Field(ge=0)
    critical_alerts: int = Field(ge=0)
    recommended_actions: list[str] = Field(default_factory=list)
    risk_history: list[RiskHistoryEntry] = Field(default_factory=list)


class SessionIntelligenceSummary(BaseModel):
    """Deterministic end-of-session Session Intelligence summary.

    Extends -- and mostly reuses -- `app.models.protection.SessionSummary`
    rather than recomputing what the Protection Service already tracks.
    No LLM, no persistence, no invented information.
    """

    session_id: str = Field(min_length=1)
    session_duration_seconds: float | None = Field(default=None, ge=0.0)
    final_risk_score: float = Field(ge=0.0, le=100.0)
    highest_risk_score: float = Field(ge=0.0, le=100.0)
    final_state: ProtectionState
    highest_severity: ThreatSeverity
    primary_category: SecurityCategory
    categories: list[SecurityCategory] = Field(default_factory=list)
    key_signals: list[str] = Field(default_factory=list)
    evidence_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    critical_alert_count: int = Field(ge=0)
    risk_escalation_count: int = Field(ge=0)
    recommended_final_action: str = Field(min_length=1)
