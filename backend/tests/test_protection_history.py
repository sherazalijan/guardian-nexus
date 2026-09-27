"""Phase 5 — Protection History Service tests."""

from app.models.intervention_engine import InterventionEvent, InterventionLevel
from app.services.intervention_engine.history import ProtectionHistoryService

SESSION = "test-session"


def _event(level: InterventionLevel = InterventionLevel.WARNING) -> InterventionEvent:
    return InterventionEvent(
        level=level,
        title="Test",
        message="Test message",
        confidence=0.8,
        source="test",
        risk_score=60,
    )


def test_recording_and_retrieving_events():
    history = ProtectionHistoryService(SESSION)
    history.record(_event())
    history.record(_event(InterventionLevel.CRITICAL))

    events = history.all_events()
    assert len(events) == 2
    assert events[1].level == InterventionLevel.CRITICAL


def test_recent_returns_most_recent_events_in_order():
    history = ProtectionHistoryService(SESSION)
    for _ in range(5):
        history.record(_event())

    recent = history.recent(limit=2)
    assert len(recent) == 2


def test_recent_handles_fewer_events_than_limit():
    history = ProtectionHistoryService(SESSION)
    history.record(_event())

    assert len(history.recent(limit=10)) == 1


def test_empty_history_returns_empty_lists():
    history = ProtectionHistoryService(SESSION)
    assert history.all_events() == []
    assert history.recent() == []


def test_count_by_level():
    history = ProtectionHistoryService(SESSION)
    history.record(_event(InterventionLevel.WARNING))
    history.record(_event(InterventionLevel.WARNING))
    history.record(_event(InterventionLevel.CRITICAL))

    counts = history.count_by_level()
    assert counts["warning"] == 2
    assert counts["critical"] == 1
