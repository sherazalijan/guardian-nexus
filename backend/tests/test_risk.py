import pytest
from pydantic import ValidationError

from app.models.enums import RecommendedAction, ThreatSeverity
from app.models.risk import RiskFactor, RiskResult


def make_risk(**overrides):
    data = {
        "score": 80,
        "severity": ThreatSeverity.HIGH,
        "confidence": 0.9,
        "risk_factors": [],
        "explanation": "Potential scam detected.",
        "recommended_action": RecommendedAction.WARN,
    }
    data.update(overrides)
    return data


def test_valid_risk_result():
    result = RiskResult(**make_risk())

    assert result.score == 80
    assert result.severity == ThreatSeverity.HIGH
    assert result.recommended_action == RecommendedAction.WARN


@pytest.mark.parametrize("score", [0, 100, 0.0, 100.0])
def test_score_boundary_values_are_valid(score):
    result = RiskResult(**make_risk(score=score))

    assert result.score == score


@pytest.mark.parametrize("score", [-0.01, 100.01])
def test_score_outside_range_is_rejected(score):
    with pytest.raises(ValidationError):
        RiskResult(**make_risk(score=score))


@pytest.mark.parametrize("confidence", [0, 1, 0.0, 1.0])
def test_confidence_boundary_values_are_valid(confidence):
    result = RiskResult(**make_risk(confidence=confidence))

    assert result.confidence == confidence


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_outside_range_is_rejected(confidence):
    with pytest.raises(ValidationError):
        RiskResult(**make_risk(confidence=confidence))


def test_risk_factor_structure():
    factor = RiskFactor(
        name="Urgency",
        description="Caller demanded immediate action.",
        contribution=25,
    )

    result = RiskResult(
        **make_risk(risk_factors=[factor])
    )

    assert result.risk_factors[0].name == "Urgency"
    assert result.risk_factors[0].contribution == 25
