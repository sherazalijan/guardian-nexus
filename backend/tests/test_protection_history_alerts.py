"""Phase 6 — Protection History integration with GuardianAlert.

Confirms the Phase 5 -> Phase 6 extension of `ProtectionHistoryService`
is purely additive: existing `record()`/`all_events()` behavior is
unchanged, and the new `record_alert()`/`all_alerts()` work alongside it.
"""

from datetime import datetime, timezone

from app.models.enums import ThreatCategory
from app.models.guardian_alert import AlertStatus, GuardianAlert
from app.models.intervention_engine import InterventionEvent, InterventionLevel
from app.services.intervention_engine.history import ProtectionHistoryService

SESSION = "test-session"


def _intervention_event() -> InterventionEvent:
    return InterventionEvent(
        level=InterventionLevel.WARNING,
        title="title",
        message="message",
        confidence=0.8,
        source="intervention-engine",
        risk_score=55,
    )


def _alert() -> GuardianAlert:
    return GuardianAlert(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        title="title",
        message="message",
        level=InterventionLevel.WARNING,
        status=AlertStatus.ACTIVE,
        risk_score=55,
        confidence=0.8,
        source="intervention-engine",
        category=ThreatCategory.FRAUD,
    )


def test_existing_intervention_event_recording_is_unchanged():
    history = ProtectionHistoryService(SESSION)
    history.record(_intervention_event())

    assert len(history.all_events()) == 1
    assert history.count_by_level() == {"warning": 1}


def test_alerts_can_be_recorded_alongside_interventions():
    history = ProtectionHistoryService(SESSION)
    history.record(_intervention_event())
    history.record_alert(_alert())

    assert len(history.all_events()) == 1
    assert len(history.all_alerts()) == 1


def test_all_alerts_preserves_insertion_order():
    history = ProtectionHistoryService(SESSION)
    first = _alert()
    second = _alert()
    history.record_alert(first)
    history.record_alert(second)

    stored = history.all_alerts()
    assert stored[0].id == first.id
    assert stored[1].id == second.id


def test_empty_history_has_no_alerts():
    history = ProtectionHistoryService(SESSION)
    assert history.all_alerts() == []
