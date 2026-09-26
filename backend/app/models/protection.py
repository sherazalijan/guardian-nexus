"""Models for the Guardian Nexus real-time protection layer.

These models sit one layer above `app.models.risk.RiskResult` and
`app.models.threat.ThreatSignal`: they translate deterministic risk/threat
analysis into a stable, user-facing contract the frontend can render
directly (warnings, recommended actions, a session timeline, and an
end-of-session summary), without the frontend needing to know anything
about the underlying rule engine.

Nothing here duplicates the Risk Engine (`app.services.risk_engine`) or
the scam detectors -- these models are pure data, populated by
`app.services.protection`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.models.enums import ThreatSeverity


class ProtectionEventType(StrEnum):
    """The kind of protection event being reported to the frontend."""

    THREAT_DETECTED = "threat_detected"
    RISK_ESCALATED = "risk_escalated"
    WARNING = "warning"
    CRITICAL_ALERT = "critical_alert"
    SENSITIVE_INFORMATION_DETECTED = "sensitive_information_detected"
    RECOMMENDED_ACTION = "recommended_action"
    SESSION_SUMMARY = "session_summary"


class ProtectionState(StrEnum):
    """Session-level protection posture, derived from the Risk Engine's
    severity, not calculated independently of it."""

    MONITORING = "monitoring"
    SUSPICIOUS = "suspicious"
    HIGH_RISK = "high_risk"
    CRITICAL = "critical"


class SecurityCategory(StrEnum):
    """User-facing threat category shown to the person being protected.

    This is deliberately a different vocabulary from `ThreatCategory`
    (`app.models.enums`), which describes the *technical* classification a
    detector assigns. `SecurityCategory` describes the *scam pattern* in
    terms a non-technical user recognizes immediately.
    """

    OTP_THEFT = "otp_theft"
    BANK_IMPERSONATION = "bank_impersonation"
    ACCOUNT_COMPROMISE = "account_compromise"
    URGENT_PAYMENT = "urgent_payment"
    GIFT_CARD_SCAM = "gift_card_scam"
    CRYPTOCURRENCY_SCAM = "cryptocurrency_scam"
    REMOTE_ACCESS_SCAM = "remote_access_scam"
    PHISHING = "phishing"
    CREDENTIAL_THEFT = "credential_theft"
    SOCIAL_ENGINEERING = "social_engineering"
    UNKNOWN = "unknown"


class ProtectionEvent(BaseModel):
    """A single, user-facing protection event.

    This is the structured contract the frontend renders as a warning,
    intervention banner, or timeline entry -- built from a `RiskResult`
    and/or `ThreatSignal`(s), never a replacement for them.
    """

    event_id: UUID = Field(default_factory=uuid4)
    session_id: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: ProtectionEventType
    severity: ThreatSeverity
    risk_score: float = Field(ge=0.0, le=100.0)
    title: str = Field(min_length=1)
    message: str = Field(min_length=1)
    category: SecurityCategory
    evidence: list[str] = Field(default_factory=list)
    recommended_action: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class TimelineEvent(BaseModel):
    """A single structured entry on the session timeline.

    The backend intentionally supplies structured data only (a label plus
    optional category/detail/metadata) -- not a formatted UI string. The
    frontend decides how each entry is rendered.
    """

    event_id: UUID = Field(default_factory=uuid4)
    session_id: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    label: str = Field(min_length=1)
    category: SecurityCategory | None = None
    severity: ThreatSeverity | None = None
    detail: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SessionSummary(BaseModel):
    """Deterministic end-of-session summary.

    Built entirely from in-memory session state accumulated by the
    protection service -- no LLM, no persistence.
    """

    session_id: str = Field(min_length=1)
    session_started_at: datetime | None = None
    session_ended_at: datetime | None = None
    duration_seconds: float | None = Field(default=None, ge=0.0)
    highest_risk_score: float = Field(ge=0.0, le=100.0)
    final_risk_score: float = Field(ge=0.0, le=100.0)
    highest_severity: ThreatSeverity
    detected_categories: list[SecurityCategory] = Field(default_factory=list)
    detected_signals: list[str] = Field(default_factory=list)
    warning_count: int = Field(ge=0)
    critical_alert_count: int = Field(ge=0)
    recommended_final_action: str = Field(min_length=1)
