"""Phase 6 — Guardian Alert Manager: creation, lookup, retrieval."""

from datetime import datetime, timezone

from app.models.enums import ThreatCategory
from app.models.guardian_alert import AlertStatus
from app.models.intervention_engine import InterventionEvent, InterventionLevel
from app.services.guardian_alerts.manager import GuardianAlertManager

SESSION = "test-session"
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _intervention(
    level: InterventionLevel = InterventionLevel.WARNING,
    category: ThreatCategory | None = ThreatCategory.PHISHING,
    title: str = "Potential OTP Scam",
    message: str = "Do not share verification codes.",
    risk_score: float = 55,
    confidence: float = 0.85,
) -> InterventionEvent:
    return InterventionEvent(
        level=level,
        title=title,
        message=message,
        confidence=confidence,
        source="intervention-engine",
        risk_score=risk_score,
        category=category,
    )


def test_creates_a_new_active_alert():
    manager = GuardianAlertManager(SESSION)
    outcome = manager.process(_intervention(), now=NOW)

    assert outcome.event_type == "created"
    assert outcome.alert.status == AlertStatus.ACTIVE
    assert outcome.alert.level == InterventionLevel.WARNING
    assert outcome.alert.title == "Potential OTP Scam"


def test_alert_lookup_by_id():
    manager = GuardianAlertManager(SESSION)
    outcome = manager.process(_intervention(), now=NOW)

    found = manager.get_alert(outcome.alert.id)
    assert found is not None
    assert found.id == outcome.alert.id


def test_lookup_of_unknown_id_returns_none():
    manager = GuardianAlertManager(SESSION)
    import uuid

    assert manager.get_alert(uuid.uuid4()) is None


def test_get_active_alerts_only_returns_active():
    manager = GuardianAlertManager(SESSION)
    outcome = manager.process(_intervention(), now=NOW)
    manager.dismiss_alert(outcome.alert.id, now=NOW)

    assert manager.get_active_alerts() == []
    assert len(manager.get_alert_history()) == 1


def test_get_alert_history_includes_every_status():
    manager = GuardianAlertManager(SESSION)
    active_outcome = manager.process(
        _intervention(category=ThreatCategory.PHISHING), now=NOW
    )
    dismissed_outcome = manager.process(
        _intervention(category=ThreatCategory.FRAUD), now=NOW
    )
    manager.dismiss_alert(dismissed_outcome.alert.id, now=NOW)

    history = manager.get_alert_history()
    assert len(history) == 2
    statuses = {a.status for a in history}
    assert statuses == {AlertStatus.ACTIVE, AlertStatus.DISMISSED}


def test_alert_with_no_category_uses_general_bucket_and_still_dedupes():
    manager = GuardianAlertManager(SESSION)
    first = manager.process(_intervention(category=None), now=NOW)
    second = manager.process(_intervention(category=None), now=NOW)

    assert first.alert.id == second.alert.id
    assert second.event_type is None
