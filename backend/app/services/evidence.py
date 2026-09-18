"""Deterministic evidence sufficiency policy."""

from collections.abc import Sequence

from app.models.enums import EvidenceState
from app.models.threat import ThreatSignal


MIN_SIGNAL_CONFIDENCE = 0.50
SUFFICIENT_SIGNAL_COUNT = 2


def assess_evidence_state(
    signals: Sequence[ThreatSignal],
) -> EvidenceState:
    """
    Determine whether the available threat evidence is sufficient.

    Evidence sufficiency is independent of numerical risk.
    """
    meaningful_signals = [
        signal
        for signal in signals
        if signal.confidence >= MIN_SIGNAL_CONFIDENCE
    ]

    if not meaningful_signals:
        return EvidenceState.INSUFFICIENT

    if len(meaningful_signals) < SUFFICIENT_SIGNAL_COUNT:
        return EvidenceState.PARTIAL

    return EvidenceState.SUFFICIENT