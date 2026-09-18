from datetime import datetime, timezone

from app.models.enums import EvidenceState, ThreatCategory
from app.models.threat import ThreatSignal
from app.services.evidence import assess_evidence_state


def make_signal(confidence: float) -> ThreatSignal:
    return ThreatSignal(
        category=ThreatCategory.SCAM,
        indicator="suspicious request",
        evidence="Test evidence",
        confidence=confidence,
        source="test-agent",
        timestamp=datetime.now(timezone.utc),
    )


def test_no_signals_are_insufficient():
    assert assess_evidence_state([]) == EvidenceState.INSUFFICIENT


def test_low_confidence_signal_is_insufficient():
    signals = [
        make_signal(0.40),
    ]

    assert assess_evidence_state(signals) == EvidenceState.INSUFFICIENT


def test_one_meaningful_signal_is_partial():
    signals = [
        make_signal(0.80),
    ]

    assert assess_evidence_state(signals) == EvidenceState.PARTIAL


def test_two_meaningful_signals_are_sufficient():
    signals = [
        make_signal(0.80),
        make_signal(0.90),
    ]

    assert assess_evidence_state(signals) == EvidenceState.SUFFICIENT


def test_low_confidence_signals_do_not_count():
    signals = [
        make_signal(0.80),
        make_signal(0.40),
        make_signal(0.30),
    ]

    assert assess_evidence_state(signals) == EvidenceState.PARTIAL