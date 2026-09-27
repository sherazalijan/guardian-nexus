"""Phase 6 — Guardian Alert deduplication.

Deduplication key is `category` (see manager.py's module docstring for
why). These tests exercise the exact spec examples: three consecutive
OTP warnings collapsing to one active alert, and the same for bank and
crypto alerts.
"""

from datetime import datetime, timezone

from app.models.enums import ThreatCategory
from app.models.intervention_engine import InterventionEvent, InterventionLevel
from app.services.guardian_alerts.manager import GuardianAlertManager

SESSION = "test-session"
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _intervention(category: ThreatCategory, title: str) -> InterventionEvent:
    return InterventionEvent(
        level=InterventionLevel.WARNING,
        title=title,
        message="message",
        confidence=0.8,
        source="intervention-engine",
        risk_score=55,
        category=category,
    )


def test_three_consecutive_otp_warnings_produce_one_active_alert():
    manager = GuardianAlertManager(SESSION)
    outcomes = [
        manager.process(_intervention(ThreatCategory.PHISHING, "Potential OTP Scam"), now=NOW)
        for _ in range(3)
    ]

    assert outcomes[0].event_type == "created"
    assert outcomes[1].event_type is None
    assert outcomes[2].event_type is None
    assert len(manager.get_active_alerts()) == 1


def test_three_consecutive_bank_alerts_produce_one_active_alert():
    manager = GuardianAlertManager(SESSION)
    for _ in range(3):
        manager.process(
            _intervention(ThreatCategory.IMPERSONATION, "Potential Bank Impersonation"), now=NOW
        )

    assert len(manager.get_active_alerts()) == 1


def test_three_consecutive_crypto_alerts_produce_one_active_alert():
    manager = GuardianAlertManager(SESSION)
    for _ in range(3):
        manager.process(_intervention(ThreatCategory.FRAUD, "Cryptocurrency Scam Risk"), now=NOW)

    assert len(manager.get_active_alerts()) == 1


def test_different_categories_are_not_deduplicated_together():
    manager = GuardianAlertManager(SESSION)
    manager.process(_intervention(ThreatCategory.PHISHING, "OTP"), now=NOW)
    manager.process(_intervention(ThreatCategory.IMPERSONATION, "Bank"), now=NOW)

    assert len(manager.get_active_alerts()) == 2


def test_duplicate_does_not_generate_a_new_alert_event():
    manager = GuardianAlertManager(SESSION)
    manager.process(_intervention(ThreatCategory.PHISHING, "OTP"), now=NOW)
    manager.process(_intervention(ThreatCategory.PHISHING, "OTP"), now=NOW)

    events = manager.get_alert_events()
    assert len(events) == 1
    assert events[0].event_type.value == "created"
