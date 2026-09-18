"""Deterministic recommended-action policy."""

from app.models.enums import EvidenceState, RecommendedAction, ThreatSeverity


def determine_action(
    severity: ThreatSeverity,
    evidence_state: EvidenceState,
) -> RecommendedAction:
    """Determine the recommended action from severity and evidence."""

    if evidence_state == EvidenceState.INSUFFICIENT:
        return RecommendedAction.MONITOR

    if evidence_state == EvidenceState.PARTIAL:
        if severity in {
            ThreatSeverity.HIGH,
            ThreatSeverity.CRITICAL,
        }:
            return RecommendedAction.WARN

        return RecommendedAction.MONITOR

    # Sufficient evidence.
    if severity == ThreatSeverity.LOW:
        return RecommendedAction.MONITOR

    if severity == ThreatSeverity.MEDIUM:
        return RecommendedAction.WARN

    if severity == ThreatSeverity.HIGH:
        return RecommendedAction.BLOCK

    return RecommendedAction.ESCALATE