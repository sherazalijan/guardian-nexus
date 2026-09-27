"""Phase 6 — `guardian_alert` WebSocket frame shape.

Unit-tests the pure frame-building function directly (see
`app.services.guardian_alerts.ws.alert_to_ws_frame`'s docstring for why
this is kept separate from `app.api.routes`), rather than spinning up a
real WebSocket/AssemblyAI connection -- consistent with the "no
AssemblyAI dependency, no network calls" testing constraint.
"""

from datetime import datetime, timezone

from app.models.enums import ThreatCategory
from app.models.guardian_alert import AlertStatus, GuardianAlert
from app.models.intervention_engine import InterventionLevel
from app.services.guardian_alerts.ws import alert_to_ws_frame


def _alert() -> GuardianAlert:
    return GuardianAlert(
        timestamp=datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc),
        title="Potential Bank Impersonation",
        message="Do not share your OTP.",
        level=InterventionLevel.CRITICAL,
        status=AlertStatus.ACTIVE,
        risk_score=91,
        confidence=0.95,
        source="intervention-engine",
        category=ThreatCategory.IMPERSONATION,
    )


def test_frame_has_correct_type_and_top_level_shape():
    frame = alert_to_ws_frame(_alert())
    assert frame["type"] == "guardian_alert"
    assert "data" not in frame  # flat shape, per the Phase 6 spec example


def test_frame_contains_all_required_fields():
    frame = alert_to_ws_frame(_alert())
    for key in (
        "alert_id",
        "level",
        "status",
        "title",
        "message",
        "risk_score",
        "confidence",
        "timestamp",
    ):
        assert key in frame


def test_frame_field_values_match_the_alert():
    alert = _alert()
    frame = alert_to_ws_frame(alert)

    assert frame["alert_id"] == str(alert.id)
    assert frame["level"] == "critical"
    assert frame["status"] == "active"
    assert frame["title"] == "Potential Bank Impersonation"
    assert frame["message"] == "Do not share your OTP."
    assert frame["risk_score"] == 91
    assert frame["confidence"] == 0.95
    assert frame["timestamp"] == "2026-09-30T12:00:00+00:00"


def test_frame_is_compatible_with_other_existing_frame_shapes():
    # This frame's keys must not collide with keys other frame types rely
    # on existing/not-existing at the top level (e.g. no stray "data" key
    # that a generic frame handler might expect to always be a dict of a
    # different shape).
    frame = alert_to_ws_frame(_alert())
    assert isinstance(frame["type"], str)
    assert frame["type"] not in ("transcript", "risk", "protection", "timeline",
                                  "evidence", "intervention", "voice_intelligence",
                                  "intervention_alert", "session_summary", "error")
