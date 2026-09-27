"""Phase 6 — Live Guardian Alert System models.

`AlertLevel` is an alias for `app.models.intervention_engine.InterventionLevel`,
not a new enum -- the two are the exact same four values (INFO / WARNING /
HIGH_RISK / CRITICAL) and giving them separate enum classes would just
create a second source of truth to keep in sync. Import `AlertLevel` from
here; it *is* `InterventionLevel`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.models.enums import ThreatCategory
from app.models.intervention_engine import InterventionLevel

AlertLevel = InterventionLevel


class AlertStatus(StrEnum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class AlertEventType(StrEnum):
    CREATED = "created"
    ESCALATED = "escalated"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class GuardianAlert(BaseModel):
    """A live, user-facing protective alert.

    `timestamp` doubles as "last meaningfully updated at" -- it advances
    on escalation as well as creation, which is what
    `GuardianAlertManager`'s auto-expiration compares against, so a
    still-escalating alert never expires mid-conversation.
    """

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    title: str = Field(min_length=1)
    message: str = Field(min_length=1)
    level: AlertLevel
    status: AlertStatus = AlertStatus.ACTIVE
    risk_score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    source: str = Field(min_length=1)
    category: ThreatCategory | None = None


class AlertEvent(BaseModel):
    """One lifecycle event for a `GuardianAlert` -- this alert layer's
    own timeline, mirrored into `ProtectionHistoryService` additively
    (see `app.services.intervention_engine.history`)."""

    alert_id: UUID
    event_type: AlertEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: dict[str, Any] = Field(default_factory=dict)
