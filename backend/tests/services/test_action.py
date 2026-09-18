import pytest

from app.models.enums import EvidenceState, RecommendedAction, ThreatSeverity
from app.services.actions import determine_action


@pytest.mark.parametrize(
    "severity",
    list(ThreatSeverity),
)
def test_insufficient_evidence_always_monitors(severity):
    assert (
        determine_action(
            severity,
            EvidenceState.INSUFFICIENT,
        )
        == RecommendedAction.MONITOR
    )


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        (ThreatSeverity.LOW, RecommendedAction.MONITOR),
        (ThreatSeverity.MEDIUM, RecommendedAction.MONITOR),
        (ThreatSeverity.HIGH, RecommendedAction.WARN),
        (ThreatSeverity.CRITICAL, RecommendedAction.WARN),
    ],
)
def test_partial_evidence_policy(severity, expected):
    assert (
        determine_action(
            severity,
            EvidenceState.PARTIAL,
        )
        == expected
    )


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        (ThreatSeverity.LOW, RecommendedAction.MONITOR),
        (ThreatSeverity.MEDIUM, RecommendedAction.WARN),
        (ThreatSeverity.HIGH, RecommendedAction.BLOCK),
        (ThreatSeverity.CRITICAL, RecommendedAction.ESCALATE),
    ],
)
def test_sufficient_evidence_policy(severity, expected):
    assert (
        determine_action(
            severity,
            EvidenceState.SUFFICIENT,
        )
        == expected
    )