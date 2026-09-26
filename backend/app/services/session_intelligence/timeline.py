"""Incident timeline assembly for Session Intelligence.

Combines the *existing* protection layer's output (`ProtectionEvent`s)
with this phase's own evidence and risk-history entries into one
coherent, chronological `IncidentTimelineEvent` list. This module does
not detect anything or compute risk -- it only narrates what the
existing Risk Engine / Protection Service already produced.

Severity *increases* (Risk Engine crossing MEDIUM/HIGH/CRITICAL) are
already represented by a `ProtectionEvent` from the Protection Service
(`RISK_ESCALATED` / `WARNING` / `CRITICAL_ALERT`), so those are mapped
here from `protection_events_to_incident` and intentionally *not*
duplicated from risk history. `risk_history_to_incident` only ever
contributes same-severity score movement or a severity *decrease*
(which the Protection Service does not emit an event for), so nothing
is ever double-counted on the timeline.
"""

from __future__ import annotations

from app.models.protection import ProtectionEvent, ProtectionEventType
from app.models.session_intelligence import (
    EvidenceItem,
    IncidentEventType,
    IncidentTimelineEvent,
    RiskHistoryEntry,
    RiskHistoryTrigger,
)

_PROTECTION_TO_INCIDENT: dict[ProtectionEventType, IncidentEventType] = {
    ProtectionEventType.THREAT_DETECTED: IncidentEventType.THREAT_DETECTED,
    ProtectionEventType.RISK_ESCALATED: IncidentEventType.RISK_ESCALATED,
    ProtectionEventType.WARNING: IncidentEventType.WARNING,
    ProtectionEventType.CRITICAL_ALERT: IncidentEventType.CRITICAL_ALERT,
}

_RISK_TRIGGER_TO_INCIDENT: dict[RiskHistoryTrigger, IncidentEventType] = {
    RiskHistoryTrigger.RISK_INCREASE: IncidentEventType.RISK_ESCALATED,
    RiskHistoryTrigger.RISK_DECREASE: IncidentEventType.RISK_DECREASED,
}


def session_started_event(session_id: str, started_at) -> IncidentTimelineEvent:
    """The first entry on every session's incident timeline."""
    return IncidentTimelineEvent(
        session_id=session_id,
        timestamp=started_at,
        event_type=IncidentEventType.SESSION_STARTED,
        title="Session started",
        description="Guardian Nexus began monitoring this session.",
    )


def evidence_events(
    session_id: str, evidence: list[EvidenceItem]
) -> list[IncidentTimelineEvent]:
    """One incident-timeline entry per new evidence item, in order."""
    return [
        IncidentTimelineEvent(
            session_id=session_id,
            timestamp=item.timestamp,
            event_type=IncidentEventType.EVIDENCE_DETECTED,
            title=f"Evidence detected: {item.signal}",
            description=item.text,
            severity=item.severity,
            risk_score=item.risk_score,
            category=item.category,
            evidence_ids=[item.evidence_id],
        )
        for item in evidence
    ]


def protection_events_to_incident(
    session_id: str, events: list[ProtectionEvent]
) -> list[IncidentTimelineEvent]:
    """Translate this pass's new `ProtectionEvent`s into incident events.

    Any `ProtectionEventType` with no mapping (e.g. a future event type)
    is silently skipped rather than raising -- the incident timeline is
    additive narration, not a strict 1:1 mirror.
    """
    incident_events: list[IncidentTimelineEvent] = []
    for event in events:
        incident_type = _PROTECTION_TO_INCIDENT.get(event.event_type)
        if incident_type is None:
            continue

        incident_events.append(
            IncidentTimelineEvent(
                session_id=session_id,
                timestamp=event.timestamp,
                event_type=incident_type,
                title=event.title,
                description=event.message,
                severity=event.severity,
                risk_score=event.risk_score,
                category=event.category,
            )
        )
    return incident_events


def risk_history_to_incident(
    session_id: str, entries: list[RiskHistoryEntry]
) -> list[IncidentTimelineEvent]:
    """Translate risk-history entries not already covered by a protection
    event (same-severity score movement, or any severity decrease)."""
    incident_events: list[IncidentTimelineEvent] = []
    for entry in entries:
        incident_type = _RISK_TRIGGER_TO_INCIDENT.get(entry.trigger)
        if incident_type is None:
            continue

        incident_events.append(
            IncidentTimelineEvent(
                session_id=session_id,
                timestamp=entry.timestamp,
                event_type=incident_type,
                title=f"Risk {entry.trigger.value.replace('_', ' ')}",
                description=(
                    f"Risk score changed from {entry.previous_score:.0f} "
                    f"to {entry.new_score:.0f} ({entry.severity.value})."
                ),
                severity=entry.severity,
                risk_score=entry.new_score,
            )
        )
    return incident_events
