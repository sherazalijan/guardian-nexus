"""Phase 5 — Real-Time Intervention Engine models.

Deliberately named/namespaced apart from the *existing* Phase 3
intervention system (`app.services.intervention.InterventionPolicyService`,
`app.models.intervention` -- whatever that module is actually called in
this repo -- which already emits a `{"type": "intervention", ...}`
WebSocket frame with its own priority/cooldown/acknowledgement
lifecycle). This module implements the Phase 5 spec's own
`InterventionEvent` / `InterventionDecision` shape without touching or
replacing that system -- see `app.services.intervention_engine` for how
the two coexist on the wire (`intervention_alert`, not `intervention`).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.models.enums import ThreatCategory


class InterventionLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    HIGH_RISK = "high_risk"
    CRITICAL = "critical"


class InterventionEvent(BaseModel):
    """A single protective alert surfaced to the user in real time."""

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    level: InterventionLevel
    title: str = Field(min_length=1)
    message: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    source: str = Field(min_length=1)
    risk_score: float = Field(ge=0.0, le=100.0)
    category: ThreatCategory | None = None


class InterventionDecision(BaseModel):
    """The engine's deterministic verdict for one analysis pass."""

    should_intervene: bool
    level: InterventionLevel
    reason: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
