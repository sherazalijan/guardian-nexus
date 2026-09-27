"""Phase 6 — Guardian Alert escalation."""

from datetime import datetime, timezone

from app.models.enums import ThreatCategory
from app.models.intervention_engine import InterventionEvent, InterventionLevel
from app.services.guardian_alerts.manager import GuardianAlertManager

SESSION = "test-session"
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _intervention(level: InterventionLevel, risk_score: float = 55) -> InterventionEvent:
    return InterventionEvent(
        level=level,
        title=f"{level.value} title",
        message="message",
        confidence=0.8,
        source="intervention-engine",
        risk_score=risk_score,
        category=ThreatCategory.FRAUD,
    )


def test_warning_escalates_to_high_risk_on_the_same_alert():
    manager = GuardianAlertManager(SESSION)
    first = manager.process(_intervention(InterventionLevel.WARNING), now=NOW)
    second = manager.process(_intervention(InterventionLevel.HIGH_RISK), now=NOW)

    assert second.event_type == "escalated"
    assert second.alert.id == first.alert.id
    assert second.alert.level == InterventionLevel.HIGH_RISK
    assert len(manager.get_active_alerts()) == 1


def test_high_risk_escalates_to_critical_on_the_same_alert():
    manager = GuardianAlertManager(SESSION)
    manager.process(_intervention(InterventionLevel.WARNING), now=NOW)
    manager.process(_intervention(InterventionLevel.HIGH_RISK), now=NOW)
    third = manager.process(_intervention(InterventionLevel.CRITICAL), now=NOW)

    assert third.event_type == "escalated"
    assert third.alert.level == InterventionLevel.CRITICAL
    assert len(manager.get_active_alerts()) == 1


def test_lower_level_after_escalation_does_not_deescalate():
    manager = GuardianAlertManager(SESSION)
    manager.process(_intervention(InterventionLevel.HIGH_RISK), now=NOW)
    followup = manager.process(_intervention(InterventionLevel.WARNING), now=NOW)

    # A WARNING arriving after HIGH_RISK is a duplicate at the lower
    # level, not a de-escalation -- the alert stays at HIGH_RISK.
    assert followup.event_type is None
    assert followup.alert.level == InterventionLevel.HIGH_RISK


def test_escalation_is_recorded_in_alert_events_history():
    manager = GuardianAlertManager(SESSION)
    manager.process(_intervention(InterventionLevel.WARNING), now=NOW)
    manager.process(_intervention(InterventionLevel.HIGH_RISK), now=NOW)

    events = manager.get_alert_events()
    event_types = [e.event_type.value for e in events]
    assert event_types == ["created", "escalated"]
    assert events[1].details == {"from": "warning", "to": "high_risk"}


def test_escalation_updates_title_message_and_risk_score():
    manager = GuardianAlertManager(SESSION)
    manager.process(_intervention(InterventionLevel.WARNING, risk_score=55), now=NOW)
    outcome = manager.process(_intervention(InterventionLevel.CRITICAL, risk_score=92), now=NOW)

    assert outcome.alert.risk_score == 92
    assert outcome.alert.title == "critical title"
