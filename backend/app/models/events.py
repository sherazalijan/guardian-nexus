from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.models.enums import EventType
from app.models.risk import RiskResult
from app.models.threat import ThreatSignal


class EventEnvelope(BaseModel):
    """Common metadata shared by every Guardian Nexus event."""

    event_type: EventType
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    session_id: str = Field(min_length=1)
    payload: dict[str, object] = Field(default_factory=dict)


class TranscriptEvent(EventEnvelope):
    """Event containing speech-to-text transcript information."""

    event_type: Literal[EventType.TRANSCRIPT] = EventType.TRANSCRIPT
    payload: dict[str, object] = Field(default_factory=dict)


class RiskEvent(EventEnvelope):
    """Event containing a structured risk assessment."""

    event_type: Literal[EventType.RISK] = EventType.RISK
    payload: RiskResult


class ThreatEvent(EventEnvelope):
    """Event containing a detected threat signal."""

    event_type: Literal[EventType.THREAT] = EventType.THREAT
    payload: ThreatSignal


class AlertEvent(EventEnvelope):
    """Event representing an actionable Guardian Nexus alert."""

    event_type: Literal[EventType.ALERT] = EventType.ALERT
    payload: dict[str, object] = Field(default_factory=dict)


GuardianEvent = Annotated[
    TranscriptEvent | RiskEvent | ThreatEvent | AlertEvent,
    Field(discriminator="event_type"),
]
