"""Session Intelligence orchestrator (Phase 2).

`SessionIntelligenceService` sits one layer above the existing
`ProtectionService` (Phase 1): it does not detect threats, does not
score risk, and does not decide protection state -- it only turns the
existing Risk Engine / Protection Service output into the richer
evidence + risk-history + incident-timeline + session-summary contract
described in the Phase 2 spec. One instance per session, in-memory only,
no persistence, mirroring `ProtectionService`'s lifecycle exactly.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models.enums import ThreatSeverity
from app.models.protection import (
    ProtectionEventType,
    ProtectionState,
    SecurityCategory,
    SessionSummary,
)
from app.models.risk import RiskResult
from app.models.session_intelligence import (
    EvidenceItem,
    IncidentEventType,
    IncidentTimelineEvent,
    RiskHistoryEntry,
    RiskHistoryTrigger,
    SessionIntelligence,
    SessionIntelligenceSummary,
)
from app.models.threat import ThreatSignal
from app.services.protection.models import severity_rank
from app.services.protection.service import ProtectionAnalysisResult
from app.services.session_intelligence import timeline as timeline_builders
from app.services.session_intelligence.evidence import extract_evidence
from app.services.session_intelligence.risk_history import build_risk_history_entry

# Protection-event types that represent a genuine severity escalation
# (a strict increase crossing into MEDIUM/HIGH/CRITICAL). Counted toward
# the session's "risk escalations" total alongside same-severity score
# increases from risk history (see `process` below).
_ESCALATION_PROTECTION_TYPES = {
    ProtectionEventType.RISK_ESCALATED,
    ProtectionEventType.WARNING,
    ProtectionEventType.CRITICAL_ALERT,
}


@dataclass
class SessionIntelligenceUpdate:
    """Everything new produced by one call to `SessionIntelligenceService.process`."""

    evidence: list[EvidenceItem] = field(default_factory=list)
    timeline_events: list[IncidentTimelineEvent] = field(default_factory=list)
    risk_history_entry: RiskHistoryEntry | None = None


class SessionIntelligenceService:
    """Session-scoped Session Intelligence layer.

    Holds no cross-session state and no database -- everything lives in
    this instance for the session's lifetime, exactly like
    `app.services.protection.ProtectionService`.
    """

    def __init__(self, session_id: str, *, now=None) -> None:
        self._session_id = session_id
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._started_at = self._now()

        self._evidence: list[EvidenceItem] = []
        self._evidence_keys: set[tuple[str, str]] = set()
        self._risk_history: list[RiskHistoryEntry] = []
        self._timeline: list[IncidentTimelineEvent] = [
            timeline_builders.session_started_event(session_id, self._started_at)
        ]
        self._categories: set[SecurityCategory] = set()
        self._signals: set[str] = set()
        self._recommended_actions: list[str] = []
        self._seen_actions: set[str] = set()

        self._current_score: float = 0.0
        self._current_severity: ThreatSeverity | None = None
        self._current_state: ProtectionState = ProtectionState.MONITORING
        self._highest_score: float = 0.0
        self._highest_severity: ThreatSeverity | None = None
        self._risk_escalations: int = 0

    @property
    def session_id(self) -> str:
        return self._session_id

    def process(
        self,
        *,
        threat_signals: Sequence[ThreatSignal],
        risk_result: RiskResult,
        protection_result: ProtectionAnalysisResult,
    ) -> SessionIntelligenceUpdate:
        """Turn one analysis pass into new evidence/timeline/history entries.

        Deterministic given identical inputs and prior state: every new
        evidence item is deduplicated against the whole session's
        history (see `extract_evidence`), and a risk-history entry is
        only recorded when the score or severity actually changed since
        the previous call (see `build_risk_history_entry`).
        """
        for signal in threat_signals:
            self._signals.add(signal.indicator)

        new_evidence = extract_evidence(
            self._session_id, threat_signals, risk_result, self._evidence_keys
        )
        self._evidence.extend(new_evidence)
        for item in new_evidence:
            self._categories.add(item.category)

        for event in protection_result.events:
            self._categories.add(event.category)
            if event.recommended_action not in self._seen_actions:
                self._seen_actions.add(event.recommended_action)
                self._recommended_actions.append(event.recommended_action)
            if event.event_type in _ESCALATION_PROTECTION_TYPES:
                self._risk_escalations += 1

        previous_score = None if self._current_severity is None else self._current_score
        previous_severity = self._current_severity

        history_entry = build_risk_history_entry(
            previous_score=previous_score,
            previous_severity=previous_severity,
            risk_result=risk_result,
            state=protection_result.state,
        )

        self._current_score = risk_result.score
        self._current_severity = risk_result.severity
        self._current_state = protection_result.state
        if risk_result.score > self._highest_score:
            self._highest_score = risk_result.score
        if (
            self._highest_severity is None
            or severity_rank(risk_result.severity) > severity_rank(self._highest_severity)
        ):
            self._highest_severity = risk_result.severity

        new_timeline: list[IncidentTimelineEvent] = []
        new_timeline.extend(
            timeline_builders.evidence_events(self._session_id, new_evidence)
        )
        new_timeline.extend(
            timeline_builders.protection_events_to_incident(
                self._session_id, protection_result.events
            )
        )

        if history_entry is not None:
            self._risk_history.append(history_entry)
            if history_entry.trigger == RiskHistoryTrigger.RISK_INCREASE:
                self._risk_escalations += 1
            new_timeline.extend(
                timeline_builders.risk_history_to_incident(
                    self._session_id, [history_entry]
                )
            )

        self._timeline.extend(new_timeline)

        return SessionIntelligenceUpdate(
            evidence=new_evidence,
            timeline_events=new_timeline,
            risk_history_entry=history_entry,
        )

    def _dominant_category(self) -> SecurityCategory:
        """Deterministically pick a representative category for
        session-level fields, mirroring `ProtectionService._dominant_category`."""
        if not self._categories:
            return SecurityCategory.UNKNOWN
        return sorted(self._categories)[0]

    def snapshot(self) -> SessionIntelligence:
        """The full, current Session Intelligence state for this session."""
        return SessionIntelligence(
            session_id=self._session_id,
            started_at=self._started_at,
            updated_at=self._now(),
            current_state=self._current_state,
            current_risk_score=self._current_score,
            highest_risk_score=self._highest_score,
            highest_severity=self._highest_severity or ThreatSeverity.LOW,
            primary_category=self._dominant_category(),
            categories=sorted(self._categories),
            signals=sorted(self._signals),
            evidence=list(self._evidence),
            timeline=list(self._timeline),
            warnings=sum(
                1 for e in self._timeline if e.event_type == IncidentEventType.WARNING
            ),
            critical_alerts=sum(
                1
                for e in self._timeline
                if e.event_type == IncidentEventType.CRITICAL_ALERT
            ),
            recommended_actions=list(self._recommended_actions),
            risk_history=list(self._risk_history),
        )

    def build_summary(
        self, protection_summary: SessionSummary
    ) -> SessionIntelligenceSummary:
        """Build the deterministic Session Intelligence summary.

        Reuses `protection_summary` (from
        `ProtectionService.build_session_summary`) for everything the
        Protection Service already tracks -- duration, final/highest risk
        score, highest severity, warning/critical counts, recommended
        final action -- rather than recomputing it. No LLM, no database.
        """
        return SessionIntelligenceSummary(
            session_id=self._session_id,
            session_duration_seconds=protection_summary.duration_seconds,
            final_risk_score=protection_summary.final_risk_score,
            highest_risk_score=protection_summary.highest_risk_score,
            final_state=self._current_state,
            highest_severity=protection_summary.highest_severity,
            primary_category=self._dominant_category(),
            categories=sorted(self._categories),
            key_signals=sorted(self._signals),
            evidence_count=len(self._evidence),
            warning_count=protection_summary.warning_count,
            critical_alert_count=protection_summary.critical_alert_count,
            risk_escalation_count=self._risk_escalations,
            recommended_final_action=protection_summary.recommended_final_action,
        )
