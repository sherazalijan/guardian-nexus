"""
Phase 3 — Intervention models.

Deterministic data model for the real-time intervention layer. Reuses
`SecurityCategory` from `app.models.protection` directly rather than
inventing a parallel category vocabulary. `InterventionPriority` has no
`LOW` tier: `ThreatSeverity.LOW` maps straight to `InterventionPriority.NONE`
(no intervention) in `services/intervention/policy.py`, so a `LOW`
intervention state would never be reachable -- only states that are
actually useful exist here, per the Phase 3 brief.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field

from app.models.protection import SecurityCategory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_intervention_id() -> str:
    return f"int_{uuid.uuid4().hex[:12]}"


class InterventionPriority(StrEnum):
    NONE = "none"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


_PRIORITY_ORDER: list[InterventionPriority] = [
    InterventionPriority.NONE,
    InterventionPriority.MEDIUM,
    InterventionPriority.HIGH,
    InterventionPriority.CRITICAL,
]


def priority_rank(p: InterventionPriority) -> int:
    return _PRIORITY_ORDER.index(p)


class InterventionStatus(StrEnum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    EXPIRED = "expired"


class Intervention(BaseModel):
    intervention_id: str = Field(default_factory=_new_intervention_id)
    session_id: str
    timestamp: datetime = Field(default_factory=_utcnow)

    priority: InterventionPriority
    risk_score: float = Field(ge=0.0, le=100.0)

    # title/message/recommended_action are copied verbatim from the
    # ProtectionEvent that triggered this intervention (see policy.py) --
    # Phase 3 never generates its own copy or reclassifies anything.
    title: str
    message: str
    category: SecurityCategory
    recommended_action: str

    requires_acknowledgement: bool = False
    status: InterventionStatus = InterventionStatus.ACTIVE

    source_event_id: Optional[str] = None
    evidence: list[str] = Field(default_factory=list)

    expires_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    # set when this intervention supersedes an earlier one for the same
    # category in this session
    escalated_from: Optional[str] = None

    def to_ws_event(self) -> dict:
        return {
            "type": "intervention",
            "data": {
                "intervention_id": self.intervention_id,
                "session_id": self.session_id,
                "timestamp": self.timestamp.isoformat(),
                "priority": self.priority.value,
                "risk_score": self.risk_score,
                "title": self.title,
                "message": self.message,
                "category": self.category.value,
                "recommended_action": self.recommended_action,
                "requires_acknowledgement": self.requires_acknowledgement,
                "status": self.status.value,
                "source_event_id": self.source_event_id,
                "evidence": self.evidence,
                "escalated_from": self.escalated_from,
            },
        }


class InterventionAckResult(BaseModel):
    """Structured result for acknowledge() — never raises for bad input."""
    success: bool
    reason: str
    intervention_id: Optional[str] = None
    status: Optional[InterventionStatus] = None


class InterventionHistory(BaseModel):
    """Per-session record, mirroring SessionIntelligence's summary style."""
    session_id: str
    interventions: list[Intervention] = Field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.interventions)

    @property
    def acknowledged_count(self) -> int:
        return sum(1 for i in self.interventions if i.acknowledged_at is not None)

    @property
    def escalated_count(self) -> int:
        return sum(1 for i in self.interventions if i.status == InterventionStatus.ESCALATED)

    @property
    def resolved_count(self) -> int:
        return sum(1 for i in self.interventions if i.status == InterventionStatus.RESOLVED)

    @property
    def highest_priority(self) -> InterventionPriority:
        if not self.interventions:
            return InterventionPriority.NONE
        return max((i.priority for i in self.interventions), key=priority_rank)

    @property
    def has_critical(self) -> bool:
        return any(i.priority == InterventionPriority.CRITICAL for i in self.interventions)

    @property
    def categories(self) -> list[SecurityCategory]:
        seen: list[SecurityCategory] = []
        for i in self.interventions:
            if i.category not in seen:
                seen.append(i.category)
        return seen

    @property
    def most_recent(self) -> Optional[Intervention]:
        return self.interventions[-1] if self.interventions else None

    def summary(self) -> dict:
        mr = self.most_recent
        return {
            "session_id": self.session_id,
            "total_interventions": self.count,
            "acknowledged_count": self.acknowledged_count,
            "escalated_count": self.escalated_count,
            "resolved_count": self.resolved_count,
            "highest_priority": self.highest_priority.value,
            "categories": [c.value for c in self.categories],
            "has_critical": self.has_critical,
            "most_recent_intervention_id": mr.intervention_id if mr else None,
        }
