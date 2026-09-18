import pytest

from app.models.enums import ThreatSeverity
from app.services.severity import score_to_severity


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.0, ThreatSeverity.LOW),
        (29.0, ThreatSeverity.LOW),
        (29.01, ThreatSeverity.MEDIUM),
        (59.0, ThreatSeverity.MEDIUM),
        (59.01, ThreatSeverity.HIGH),
        (79.0, ThreatSeverity.HIGH),
        (79.01, ThreatSeverity.CRITICAL),
        (100.0, ThreatSeverity.CRITICAL),
    ],
)
def test_score_to_severity(score, expected):
    assert score_to_severity(score) == expected


@pytest.mark.parametrize("score", [-0.01, 100.01])
def test_score_outside_range_raises(score):
    with pytest.raises(ValueError):
        score_to_severity(score)