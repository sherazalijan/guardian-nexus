"""Deterministic risk severity mapping."""

from app.models.enums import ThreatSeverity
from app.services.constants import HIGH_MAX, LOW_MAX, MEDIUM_MAX, MIN_SCORE, MAX_SCORE


def score_to_severity(score: float) -> ThreatSeverity:
    """Map a bounded 0–100 risk score to a deterministic severity."""
    if not MIN_SCORE <= score <= MAX_SCORE:
        raise ValueError("Risk score must be between 0 and 100.")

    if score <= LOW_MAX:
        return ThreatSeverity.LOW

    if score <= MEDIUM_MAX:
        return ThreatSeverity.MEDIUM

    if score <= HIGH_MAX:
        return ThreatSeverity.HIGH

    return ThreatSeverity.CRITICAL