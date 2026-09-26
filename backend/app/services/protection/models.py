"""Session-level state for the protection layer.

`ProtectionSessionState` is plain, in-memory, per-connection state (no
database, per Phase 1 scope). It tracks what the Protection Service needs
to interpret the Risk Engine's output over time: the current/highest
score and severity, which threats have already been surfaced (for
deduplication), and counters used to build the end-of-session summary.

The Risk Engine (`app.services.risk_engine`) remains the sole source of
score/severity calculation; nothing here recomputes it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models.enums import ThreatSeverity
from app.models.protection import ProtectionState, SecurityCategory, TimelineEvent

# Ordinal ranking used to detect escalation (a strict increase) vs. a
# lateral/decreasing severity change. Higher is more severe.
_SEVERITY_RANK: dict[ThreatSeverity, int] = {
    ThreatSeverity.LOW: 0,
    ThreatSeverity.MEDIUM: 1,
    ThreatSeverity.HIGH: 2,
    ThreatSeverity.CRITICAL: 3,
}

# The Protection State is derived from the Risk Engine's severity -- it is
# an interpretation of that result for user-facing intervention, not a
# second, independent risk calculation.
_SEVERITY_TO_STATE: dict[ThreatSeverity, ProtectionState] = {
    ThreatSeverity.LOW: ProtectionState.MONITORING,
    ThreatSeverity.MEDIUM: ProtectionState.SUSPICIOUS,
    ThreatSeverity.HIGH: ProtectionState.HIGH_RISK,
    ThreatSeverity.CRITICAL: ProtectionState.CRITICAL,
}


def severity_rank(severity: ThreatSeverity) -> int:
    """Return the ordinal rank of a severity level (higher = more severe)."""
    return _SEVERITY_RANK[severity]

def is_escalation(previous: ThreatSeverity, current: ThreatSeverity) -> bool:
    """True if `current` is strictly more severe than `previous`."""
    return severity_rank(current) > severity_rank(previous)


def severity_to_state(severity: ThreatSeverity) -> ProtectionState:
    """Derive the session `ProtectionState` from a Risk Engine severity."""
    return _SEVERITY_TO_STATE[severity]


@dataclass
class ProtectionSessionState:
    """Mutable, in-memory protection state for a single session.

    Not a database record -- lives for the lifetime of one Guardian Nexus
    session (e.g. one `/ws/audio` connection) and is discarded afterward,
    per Phase 1 scope ("Do NOT add a database yet").
    """

    session_id: str
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    ended_at: datetime | None = None

    state: ProtectionState = ProtectionState.MONITORING
    current_risk_score: float = 0.0
    highest_risk_score: float = 0.0
    current_severity: ThreatSeverity = ThreatSeverity.LOW
    highest_severity: ThreatSeverity = ThreatSeverity.LOW

    # Dedup keys already surfaced as a `threat_detected` protection event
    # this session -- `(SecurityCategory, normalized indicator)`. See
    # `app.services.protection.service.ProtectionService`.
    emitted_signal_keys: set[tuple[str, str]] = field(default_factory=set)

    detected_categories: set[SecurityCategory] = field(default_factory=set)
    detected_signal_indicators: set[str] = field(default_factory=set)

    warning_count: int = 0
    critical_alert_count: int = 0

    timeline: list[TimelineEvent] = field(default_factory=list)

    def duration_seconds(self) -> float | None:
        """Session duration so far (or total, once `ended_at` is set)."""
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at).total_seconds()
