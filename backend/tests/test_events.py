from datetime import datetime, timezone

import pytest
from pydantic import TypeAdapter, ValidationError

from app.models.enums import (
    EventType,
    RecommendedAction,
    ThreatCategory,
    ThreatSeverity,
)
from app.models.events import (
    AlertEvent,
    EventEnvelope,
    GuardianEvent,
    RiskEvent,
    ThreatEvent,
    TranscriptEvent,
)
from app.models.risk import RiskResult
from app.models.threat import ThreatSignal


SESSION_ID = "session-test-001"
NOW = datetime.now(timezone.utc)


def test_event_envelope_defaults():
    event = EventEnvelope(
        event_type=EventType.TRANSCRIPT,
        session_id=SESSION_ID,
    )

    assert event.event_id is not None
    assert event.timestamp is not None
    assert event.session_id == SESSION_ID
    assert event.payload == {}


def test_transcript_event():
    event = TranscriptEvent(
        session_id=SESSION_ID,
        payload={
            "text": "Your account has been compromised.",
            "speaker": "caller",
        },
    )

    assert event.event_type == EventType.TRANSCRIPT
    assert event.payload["speaker"] == "caller"


def test_threat_event():
    signal = ThreatSignal(
        category=ThreatCategory.SCAM,
        indicator="urgent_payment",
        evidence="Immediate payment demanded.",
        confidence=0.95,
        source="test",
        timestamp=NOW,
    )

    event = ThreatEvent(
        session_id=SESSION_ID,
        payload=signal,
    )

    assert event.event_type == EventType.THREAT
    assert event.payload.category == ThreatCategory.SCAM


def test_risk_event():
    result = RiskResult(
        score=80,
        severity=ThreatSeverity.HIGH,
        confidence=0.9,
        explanation="Potential scam detected.",
        recommended_action=RecommendedAction.WARN,
    )

    event = RiskEvent(
        session_id=SESSION_ID,
        payload=result,
    )

    assert event.event_type == EventType.RISK
    assert event.payload.score == 80


def test_alert_event():
    event = AlertEvent(
        session_id=SESSION_ID,
        payload={
            "message": "Potential scam detected.",
            "severity": "high",
        },
    )

    assert event.event_type == EventType.ALERT
    assert event.payload["severity"] == "high"


def test_empty_session_id_is_rejected():
    with pytest.raises(ValidationError):
        TranscriptEvent(session_id="")


def test_guardian_event_discriminator():
    adapter = TypeAdapter(GuardianEvent)

    event = adapter.validate_python(
        {
            "event_type": "transcript",
            "session_id": SESSION_ID,
            "payload": {
                "text": "Test transcript",
            },
        }
    )

    assert isinstance(event, TranscriptEvent)
    assert event.event_type == EventType.TRANSCRIPT


def test_guardian_event_rejects_unknown_event_type():
    adapter = TypeAdapter(GuardianEvent)

    with pytest.raises(ValidationError):
        adapter.validate_python(
            {
                "event_type": "unknown_event",
                "session_id": SESSION_ID,
                "payload": {},
            }
        )
