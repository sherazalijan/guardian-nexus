"""Deterministic risk-history tracking for Session Intelligence.

Records meaningful transitions in the *existing* Risk Engine's output
(`RiskResult`) -- it does not compute risk itself and does not duplicate
`app.services.risk_engine`. "Meaningful" means the score or severity
actually changed since the last recorded entry; repeated identical
results produce no new history entry (Phase 2 spec section 17).
"""

from __future__ import annotations

from app.models.enums import ThreatSeverity
from app.models.protection import ProtectionState
from app.models.risk import RiskResult
from app.models.session_intelligence import RiskHistoryEntry, RiskHistoryTrigger
from app.services.protection.models import is_escalation


def build_risk_history_entry(
    *,
    previous_score: float | None,
    previous_severity: ThreatSeverity | None,
    risk_result: RiskResult,
    state: ProtectionState,
) -> RiskHistoryEntry | None:
    """Return a new `RiskHistoryEntry`, or None if nothing meaningful changed.

    `previous_severity` (and `previous_score`) being None means this is
    the first analysis pass of the session -> always record an `initial`
    entry. Otherwise, an unchanged score AND severity records nothing.
    """
    if previous_severity is None:
        return RiskHistoryEntry(
            previous_score=0.0,
            new_score=risk_result.score,
            severity=risk_result.severity,
            state=state,
            trigger=RiskHistoryTrigger.INITIAL,
        )

    assert previous_score is not None  # invariant: set together with severity

    score_changed = risk_result.score != previous_score
    severity_changed = risk_result.severity != previous_severity

    if not score_changed and not severity_changed:
        return None

    if severity_changed and is_escalation(previous_severity, risk_result.severity):
        trigger = (
            RiskHistoryTrigger.CRITICAL_ESCALATION
            if risk_result.severity == ThreatSeverity.CRITICAL
            else RiskHistoryTrigger.SEVERITY_CHANGE
        )
    elif severity_changed:
        # Severity dropped. The Protection Service only emits an
        # escalation event on a strict *increase*, so a decrease has no
        # protection-event equivalent -- it still needs a history entry.
        trigger = RiskHistoryTrigger.RISK_DECREASE
    elif risk_result.score > previous_score:
        trigger = RiskHistoryTrigger.RISK_INCREASE
    else:
        trigger = RiskHistoryTrigger.RISK_DECREASE

    return RiskHistoryEntry(
        previous_score=previous_score,
        new_score=risk_result.score,
        severity=risk_result.severity,
        state=state,
        trigger=trigger,
    )
