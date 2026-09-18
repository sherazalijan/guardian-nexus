"""Deterministic Guardian Nexus risk engine."""

from collections.abc import Sequence

from app.models.enums import EvidenceState
from app.models.risk import RiskFactor, RiskResult
from app.models.threat import ThreatSignal
from app.services.actions import determine_action
from app.services.aggregation import aggregate_risk_score
from app.services.evidence import assess_evidence_state
from app.services.severity import score_to_severity
from app.services.normalization import deduplicate_signals


def calculate_evidence_confidence(
    signals: Sequence[ThreatSignal],
) -> float:
    """Calculate overall evidence confidence from retained signals."""
    if not signals:
        return 0.0

    return sum(signal.confidence for signal in signals) / len(signals)


def build_risk_factors(
    signals: Sequence[ThreatSignal],
) -> list[RiskFactor]:
    """Convert retained threat signals into structured risk factors."""
    return [
        RiskFactor(
            name=signal.indicator,
            description=signal.evidence,
            contribution=signal.confidence,
        )
        for signal in signals
    ]


def run_risk_engine(
    signals: Sequence[ThreatSignal],
) -> RiskResult:
    """
    Run the complete deterministic risk pipeline.

    Pipeline:
    normalization → deduplication → evidence assessment →
    aggregation → severity → action.
    """
    normalized_signals = deduplicate_signals(signals)

    evidence_state = assess_evidence_state(normalized_signals)

    score = aggregate_risk_score(normalized_signals)

    severity = score_to_severity(score)

    action = determine_action(
        severity,
        evidence_state,
    )

    confidence = calculate_evidence_confidence(
        normalized_signals
    )

    if evidence_state == EvidenceState.INSUFFICIENT:
        explanation = "Insufficient threat evidence for a reliable assessment."
    elif evidence_state == EvidenceState.PARTIAL:
        explanation = "Partial threat evidence supports a preliminary assessment."
    else:
        explanation = "Sufficient threat evidence supports the risk assessment."

    return RiskResult(
        score=score,
        severity=severity,
        confidence=confidence,
        evidence_state=evidence_state,
        risk_factors=build_risk_factors(normalized_signals),
        explanation=explanation,
        recommended_action=action,
    )