"""Deterministic protection layer.

`ProtectionService` receives the *existing* risk analysis result
(`RiskResult`, from `app.services.risk_engine.run_risk_engine`) and the
threat signals it was built from, and converts them into the user-facing
contract defined in `app.models.protection`: protection events, timeline
events, and (on request) an end-of-session summary.

This module does not detect threats and does not calculate risk -- both
of those remain the responsibility of the existing scam detector and the
existing deterministic Risk Engine. This module only interprets their
output for user-facing intervention, and remembers enough session state
to avoid repeating the same warning every time a duplicate signal shows
up in a later transcript fragment.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models.enums import RecommendedAction, ThreatSeverity
from app.models.protection import (
    ProtectionEvent,
    ProtectionEventType,
    ProtectionState,
    SecurityCategory,
    SessionSummary,
    TimelineEvent,
)
from app.models.risk import RiskResult
from app.models.threat import ThreatSignal
from app.services.normalization import normalize_indicator
from app.services.protection.models import (
    ProtectionSessionState,
    is_escalation,
    severity_to_state,
)
from app.services.protection.rules import (
    classify_signal,
    message_for,
    recommended_action_for,
    risk_action_text,
    title_for,
)

# event_type used for a session-level severity increase into MEDIUM.
_ESCALATION_EVENT_BY_SEVERITY: dict[ThreatSeverity, ProtectionEventType] = {
    ThreatSeverity.MEDIUM: ProtectionEventType.RISK_ESCALATED,
    ThreatSeverity.HIGH: ProtectionEventType.WARNING,
    ThreatSeverity.CRITICAL: ProtectionEventType.CRITICAL_ALERT,
}

_ESCALATION_LABEL: dict[ProtectionEventType, str] = {
    ProtectionEventType.RISK_ESCALATED: "Risk escalated",
    ProtectionEventType.WARNING: "High-risk warning issued",
    ProtectionEventType.CRITICAL_ALERT: "Critical alert issued",
}


@dataclass
class ProtectionAnalysisResult:
    """Everything produced by one call to `ProtectionService.process`."""

    events: list[ProtectionEvent] = field(default_factory=list)
    timeline_events: list[TimelineEvent] = field(default_factory=list)
    state: ProtectionState = ProtectionState.MONITORING
    state_changed: bool = False


class ProtectionService:
    """Session-scoped protection layer built on top of the Risk Engine.

    One instance covers a single Guardian Nexus session (e.g. one
    `/ws/audio` connection). It holds no cross-session state and no
    database -- everything lives in `self._state` for the session's
    lifetime, per Phase 1 scope.
    """

    def __init__(
        self,
        session_id: str,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._state = ProtectionSessionState(
            session_id=session_id, started_at=self._now()
        )
        self._last_recommended_action: RecommendedAction = RecommendedAction.MONITOR

        start_event = TimelineEvent(
            session_id=session_id,
            timestamp=self._state.started_at,
            label="Session started",
        )
        self._state.timeline.append(start_event)

    @property
    def session_id(self) -> str:
        return self._state.session_id

    @property
    def state(self) -> ProtectionState:
        return self._state.state

    def process(
        self,
        *,
        threat_signals: Sequence[ThreatSignal],
        risk_result: RiskResult,
    ) -> ProtectionAnalysisResult:
        """Interpret one risk-analysis result for this session.

        Deterministic and side-effect-free beyond updating this session's
        own state: calling this twice with identical inputs after the
        first call's state has been applied will not re-emit the same
        `threat_detected` event (see deduplication below), but *will*
        recompute risk-escalation events based on the state at the time
        of the call.
        """
        now = self._now()
        events: list[ProtectionEvent] = []
        timeline_events: list[TimelineEvent] = []

        previous_severity = self._state.current_severity
        self._last_recommended_action = risk_result.recommended_action

        # --- Per-signal threat_detected events (deduplicated) ---
        for signal in threat_signals:
            category = classify_signal(signal)
            key = (category.value, normalize_indicator(signal.indicator))

            self._state.detected_categories.add(category)
            self._state.detected_signal_indicators.add(signal.indicator)

            if key in self._state.emitted_signal_keys:
                continue
            self._state.emitted_signal_keys.add(key)

            event = ProtectionEvent(
                session_id=self.session_id,
                timestamp=now,
                event_type=ProtectionEventType.THREAT_DETECTED,
                severity=risk_result.severity,
                risk_score=risk_result.score,
                title=title_for(category),
                message=message_for(category),
                category=category,
                evidence=[signal.evidence],
                recommended_action=recommended_action_for(category),
                confidence=signal.confidence,
            )
            events.append(event)

            timeline_events.append(
                TimelineEvent(
                    session_id=self.session_id,
                    timestamp=now,
                    label=title_for(category),
                    category=category,
                    severity=risk_result.severity,
                    detail=signal.evidence,
                )
            )

        # --- Update session risk state ---
        self._state.current_risk_score = risk_result.score
        self._state.current_severity = risk_result.severity
        if risk_result.score > self._state.highest_risk_score:
            self._state.highest_risk_score = risk_result.score
        if is_escalation(self._state.highest_severity, risk_result.severity):
            self._state.highest_severity = risk_result.severity

        new_protection_state = severity_to_state(risk_result.severity)
        state_changed = new_protection_state != self._state.state
        self._state.state = new_protection_state

        timeline_events.append(
            TimelineEvent(
                session_id=self.session_id,
                timestamp=now,
                label=f"Risk score updated to {risk_result.score:.0f}",
                severity=risk_result.severity,
                detail=risk_result.explanation,
            )
        )

        # --- Session-level escalation event (strict severity increase) ---
        if is_escalation(previous_severity, risk_result.severity):
            escalation_type = _ESCALATION_EVENT_BY_SEVERITY.get(risk_result.severity)
            if escalation_type is not None:
                if escalation_type == ProtectionEventType.WARNING:
                    self._state.warning_count += 1
                elif escalation_type == ProtectionEventType.CRITICAL_ALERT:
                    self._state.critical_alert_count += 1

                top_category = _dominant_category(self._state.detected_categories)

                escalation_event = ProtectionEvent(
                    session_id=self.session_id,
                    timestamp=now,
                    event_type=escalation_type,
                    severity=risk_result.severity,
                    risk_score=risk_result.score,
                    title=_ESCALATION_LABEL[escalation_type],
                    message=(
                        f"Risk level increased from {previous_severity.value} "
                        f"to {risk_result.severity.value} "
                        f"(score {risk_result.score:.0f})."
                    ),
                    category=top_category,
                    evidence=[s.value for s in sorted(self._state.detected_categories)],
                    recommended_action=risk_action_text(risk_result.recommended_action),
                    confidence=risk_result.confidence,
                )
                events.append(escalation_event)

                timeline_events.append(
                    TimelineEvent(
                        session_id=self.session_id,
                        timestamp=now,
                        label=_ESCALATION_LABEL[escalation_type],
                        category=top_category,
                        severity=risk_result.severity,
                        detail=escalation_event.message,
                    )
                )

        self._state.timeline.extend(timeline_events)

        return ProtectionAnalysisResult(
            events=events,
            timeline_events=timeline_events,
            state=self._state.state,
            state_changed=state_changed,
        )

    def end_session(self) -> None:
        """Mark the session as ended, fixing its duration for the summary."""
        if self._state.ended_at is None:
            self._state.ended_at = self._now()

    def build_session_summary(self) -> SessionSummary:
        """Build the deterministic end-of-session summary from session state.

        Safe to call at any point, not only after `end_session()` -- an
        in-progress summary simply has `session_ended_at`/`duration_seconds`
        unset.
        """
        return SessionSummary(
            session_id=self.session_id,
            session_started_at=self._state.started_at,
            session_ended_at=self._state.ended_at,
            duration_seconds=self._state.duration_seconds(),
            highest_risk_score=self._state.highest_risk_score,
            final_risk_score=self._state.current_risk_score,
            highest_severity=self._state.highest_severity,
            detected_categories=sorted(self._state.detected_categories),
            detected_signals=sorted(self._state.detected_signal_indicators),
            warning_count=self._state.warning_count,
            critical_alert_count=self._state.critical_alert_count,
            recommended_final_action=risk_action_text(self._last_recommended_action),
        )


def _dominant_category(categories: set[SecurityCategory]) -> SecurityCategory:
    """Deterministically pick a representative category for a session-level
    event, when one isn't tied to a specific signal."""
    if not categories:
        return SecurityCategory.UNKNOWN
    return sorted(categories)[0]
