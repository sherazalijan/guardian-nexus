"""Phase 6 — Guardian Alert lifecycle (acknowledge / dismiss / expire) and
the alert-event timeline each transition generates."""

from datetime import datetime, timedelta, timezone

from app.models.enums import ThreatCategory
from app.models.guardian_alert import AlertStatus
from app.models.intervention_engine import InterventionEvent, InterventionLevel
from app.services.guardian_alerts.manager import ALERT_EXPIRATION_SECONDS, GuardianAlertManager

SESSION = "test-session"
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _intervention(level: InterventionLevel = InterventionLevel.WARNING) -> InterventionEvent:
    return InterventionEvent(
        level=level,
        title="title",
        message="message",
        confidence=0.8,
        source="intervention-engine",
        risk_score=55,
        category=ThreatCategory.FRAUD,
    )


def test_acknowledge_transitions_status_and_removes_from_active():
    manager = GuardianAlertManager(SESSION)
    outcome = manager.process(_intervention(), now=NOW)

    acked = manager.acknowledge_alert(outcome.alert.id, now=NOW)
    assert acked.status == AlertStatus.ACKNOWLEDGED
    assert manager.get_active_alerts() == []


def test_dismiss_transitions_status_and_removes_from_active():
    manager = GuardianAlertManager(SESSION)
    outcome = manager.process(_intervention(), now=NOW)

    dismissed = manager.dismiss_alert(outcome.alert.id, now=NOW)
    assert dismissed.status == AlertStatus.DISMISSED
    assert manager.get_active_alerts() == []


def test_manual_expire_transitions_status():
    manager = GuardianAlertManager(SESSION)
    outcome = manager.process(_intervention(), now=NOW)

    expired = manager.expire_alert(outcome.alert.id, now=NOW)
    assert expired.status == AlertStatus.EXPIRED
    assert manager.get_active_alerts() == []


def test_dismissing_and_reoffending_creates_a_new_alert_not_a_reactivation():
    manager = GuardianAlertManager(SESSION)
    first = manager.process(_intervention(), now=NOW)
    manager.dismiss_alert(first.alert.id, now=NOW)

    second = manager.process(_intervention(), now=NOW + timedelta(seconds=1))
    assert second.event_type == "created"
    assert second.alert.id != first.alert.id
    assert len(manager.get_active_alerts()) == 1


# --- timeline (AlertEvent) coverage for every lifecycle transition --------

def test_created_generates_a_created_event():
    manager = GuardianAlertManager(SESSION)
    manager.process(_intervention(), now=NOW)
    types = [e.event_type.value for e in manager.get_alert_events()]
    assert types == ["created"]


def test_escalated_generates_an_escalated_event():
    manager = GuardianAlertManager(SESSION)
    manager.process(_intervention(InterventionLevel.WARNING), now=NOW)
    manager.process(_intervention(InterventionLevel.CRITICAL), now=NOW)
    types = [e.event_type.value for e in manager.get_alert_events()]
    assert types == ["created", "escalated"]


def test_acknowledged_generates_an_acknowledged_event():
    manager = GuardianAlertManager(SESSION)
    outcome = manager.process(_intervention(), now=NOW)
    manager.acknowledge_alert(outcome.alert.id, now=NOW)
    types = [e.event_type.value for e in manager.get_alert_events()]
    assert types == ["created", "acknowledged"]


def test_dismissed_generates_a_dismissed_event():
    manager = GuardianAlertManager(SESSION)
    outcome = manager.process(_intervention(), now=NOW)
    manager.dismiss_alert(outcome.alert.id, now=NOW)
    types = [e.event_type.value for e in manager.get_alert_events()]
    assert types == ["created", "dismissed"]


def test_expired_generates_an_expired_event():
    manager = GuardianAlertManager(SESSION)
    outcome = manager.process(_intervention(), now=NOW)
    manager.expire_alert(outcome.alert.id, now=NOW)
    types = [e.event_type.value for e in manager.get_alert_events()]
    assert types == ["created", "expired"]


# --- auto expiration, using injectable `now` (no real waiting) ------------

def test_active_alert_not_yet_expired_just_before_threshold():
    manager = GuardianAlertManager(SESSION)
    manager.process(_intervention(), now=NOW)

    just_before = NOW + timedelta(seconds=ALERT_EXPIRATION_SECONDS - 1)
    expired = manager.expire_stale_alerts(now=just_before)
    assert expired == []
    assert len(manager.get_active_alerts()) == 1


def test_active_alert_expires_at_threshold():
    manager = GuardianAlertManager(SESSION)
    manager.process(_intervention(), now=NOW)

    at_threshold = NOW + timedelta(seconds=ALERT_EXPIRATION_SECONDS)
    expired = manager.expire_stale_alerts(now=at_threshold)
    assert len(expired) == 1
    assert expired[0].status == AlertStatus.EXPIRED
    assert manager.get_active_alerts() == []


def test_expired_alert_remains_in_history():
    manager = GuardianAlertManager(SESSION)
    outcome = manager.process(_intervention(), now=NOW)
    manager.expire_stale_alerts(now=NOW + timedelta(seconds=ALERT_EXPIRATION_SECONDS))

    history = manager.get_alert_history()
    assert any(a.id == outcome.alert.id and a.status == AlertStatus.EXPIRED for a in history)


def test_acknowledged_alerts_are_not_auto_expired():
    manager = GuardianAlertManager(SESSION)
    outcome = manager.process(_intervention(), now=NOW)
    manager.acknowledge_alert(outcome.alert.id, now=NOW)

    expired = manager.expire_stale_alerts(now=NOW + timedelta(seconds=ALERT_EXPIRATION_SECONDS))
    assert expired == []
