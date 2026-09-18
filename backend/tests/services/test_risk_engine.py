from datetime import datetime, timezone

from app.models.enums import (
    EvidenceState,
    RecommendedAction,
    ThreatCategory,
    ThreatSeverity,
)
from app.services.risk_engine import run_risk_engine
from app.models.threat import ThreatSignal


def make_signal(
    category: ThreatCategory,
    indicator: str,
    confidence: float,
    source: str = "test-agent",
) -> ThreatSignal:
    return ThreatSignal(
        category=category,
        indicator=indicator,
        evidence=f"Evidence for {indicator}",
        confidence=confidence,
        source=source,
        timestamp=datetime.now(timezone.utc),
    )


def test_empty_input():
    result = run_risk_engine([])

    assert result.score == 0.0
    assert result.severity == ThreatSeverity.LOW
    assert result.confidence == 0.0
    assert result.evidence_state == EvidenceState.INSUFFICIENT
    assert result.recommended_action == RecommendedAction.MONITOR
    assert result.risk_factors == []


def test_single_strong_signal():
    signal = make_signal(
        ThreatCategory.MALWARE,
        "malware detected",
        1.0,
    )

    result = run_risk_engine([signal])

    assert result.score == 70.0
    assert result.severity == ThreatSeverity.HIGH
    assert result.evidence_state == EvidenceState.PARTIAL
    assert result.confidence == 1.0
    assert result.recommended_action == RecommendedAction.WARN
    assert len(result.risk_factors) == 1


def test_multiple_strong_signals():
    signals = [
        make_signal(
            ThreatCategory.MALWARE,
            "malware detected",
            1.0,
        ),
        make_signal(
            ThreatCategory.FRAUD,
            "fraud attempt",
            1.0,
        ),
    ]

    result = run_risk_engine(signals)

    assert result.score == 88.0
    assert result.severity == ThreatSeverity.CRITICAL
    assert result.evidence_state == EvidenceState.SUFFICIENT
    assert result.recommended_action == RecommendedAction.ESCALATE


def test_duplicate_signals_are_collapsed():
    signals = [
        make_signal(
            ThreatCategory.SCAM,
            "credential request",
            0.60,
        ),
        make_signal(
            ThreatCategory.SCAM,
            "  Credential   Request ",
            0.90,
        ),
    ]

    result = run_risk_engine(signals)

    assert len(result.risk_factors) == 1
    assert result.confidence == 0.90


def test_low_confidence_evidence_is_insufficient():
    signal = make_signal(
        ThreatCategory.SCAM,
        "uncertain signal",
        0.20,
    )

    result = run_risk_engine([signal])

    assert result.evidence_state == EvidenceState.INSUFFICIENT
    assert result.recommended_action == RecommendedAction.MONITOR