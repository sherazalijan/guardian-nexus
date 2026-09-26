from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.enums import ThreatSeverity
from app.models.protection import (
    ProtectionEvent,
    ProtectionEventType,
    ProtectionState,
    SecurityCategory,
    SessionSummary,
    TimelineEvent,
)

SESSION_ID = "session-protection-001"
NOW = datetime.now(timezone.utc)


def test_protection_event_defaults_generate_id_and_timestamp():
    event = ProtectionEvent(
        session_id=SESSION_ID,
        event_type=ProtectionEventType.THREAT_DETECTED,
        severity=ThreatSeverity.HIGH,
        risk_score=82.0,
        title="Possible OTP theft attempt",
        message="The caller is requesting a one-time password.",
        category=SecurityCategory.OTP_THEFT,
        evidence=["otp"],
        recommended_action="Do not share your OTP.",
        confidence=0.85,
    )

    assert event.event_id is not None
    assert event.timestamp is not None
    assert event.session_id == SESSION_ID
    assert event.category == SecurityCategory.OTP_THEFT


def test_protection_event_rejects_out_of_range_risk_score():
    with pytest.raises(ValidationError):
        ProtectionEvent(
            session_id=SESSION_ID,
            event_type=ProtectionEventType.WARNING,
            severity=ThreatSeverity.HIGH,
            risk_score=150.0,
            title="t",
            message="m",
            category=SecurityCategory.UNKNOWN,
            recommended_action="a",
            confidence=0.5,
        )


def test_protection_event_rejects_empty_title():
    with pytest.raises(ValidationError):
        ProtectionEvent(
            session_id=SESSION_ID,
            event_type=ProtectionEventType.WARNING,
            severity=ThreatSeverity.HIGH,
            risk_score=50.0,
            title="",
            message="m",
            category=SecurityCategory.UNKNOWN,
            recommended_action="a",
            confidence=0.5,
        )


def test_timeline_event_minimal_construction():
    event = TimelineEvent(session_id=SESSION_ID, label="Session started")

    assert event.label == "Session started"
    assert event.category is None
    assert event.metadata == {}


def test_session_summary_round_trip():
    summary = SessionSummary(
        session_id=SESSION_ID,
        session_started_at=NOW,
        session_ended_at=NOW,
        duration_seconds=12.5,
        highest_risk_score=92.0,
        final_risk_score=92.0,
        highest_severity=ThreatSeverity.CRITICAL,
        detected_categories=[SecurityCategory.OTP_THEFT],
        detected_signals=["otp_request"],
        warning_count=1,
        critical_alert_count=1,
        recommended_final_action="End the call immediately.",
    )

    payload = summary.model_dump_json()
    restored = SessionSummary.model_validate_json(payload)

    assert restored == summary


def test_session_summary_rejects_negative_counts():
    with pytest.raises(ValidationError):
        SessionSummary(
            session_id=SESSION_ID,
            highest_risk_score=10.0,
            final_risk_score=10.0,
            highest_severity=ThreatSeverity.LOW,
            warning_count=-1,
            critical_alert_count=0,
            recommended_final_action="monitor",
        )


def test_all_protection_event_types_are_constructible():
    for event_type in ProtectionEventType:
        event = ProtectionEvent(
            session_id=SESSION_ID,
            event_type=event_type,
            severity=ThreatSeverity.LOW,
            risk_score=0.0,
            title="t",
            message="m",
            category=SecurityCategory.UNKNOWN,
            recommended_action="a",
            confidence=0.0,
        )
        assert event.event_type == event_type


def test_protection_state_values():
    assert {s.value for s in ProtectionState} == {
        "monitoring",
        "suspicious",
        "high_risk",
        "critical",
    }
