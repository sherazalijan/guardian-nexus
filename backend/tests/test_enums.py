from app.models.enums import (
    EventType,
    RecommendedAction,
    ThreatCategory,
    ThreatSeverity,
)


def test_threat_severity_values():
    assert ThreatSeverity.LOW.value == "low"
    assert ThreatSeverity.MEDIUM.value == "medium"
    assert ThreatSeverity.HIGH.value == "high"
    assert ThreatSeverity.CRITICAL.value == "critical"


def test_threat_categories():
    expected = {
        "scam",
        "phishing",
        "impersonation",
        "malware",
        "fraud",
        "suspicious_call",
        "malicious_link",
        "unknown",
    }

    assert {category.value for category in ThreatCategory} == expected


def test_recommended_actions():
    expected = {
        "ignore",
        "monitor",
        "warn",
        "block",
        "escalate",
    }

    assert {action.value for action in RecommendedAction} == expected


def test_event_types():
    expected = {
        "transcript",
        "risk",
        "threat",
        "alert",
    }

    assert {event_type.value for event_type in EventType} == expected
