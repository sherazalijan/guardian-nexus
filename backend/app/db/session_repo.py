"""Phase 8 — plain persistence functions, one per existing Pydantic model.

Each function takes the exact Pydantic object the service layer already
produces (RiskResult, ProtectionEvent, EvidenceItem, ...) and writes the
matching ORM row. No transformation logic beyond field mapping — the
existing models remain the single source of truth for shape/validation.

Callers are expected to `db.add(...)`/await these inside a transaction
they control and commit once per analysis pass (see
`app.services.persistence.hooks.PersistenceHooks`) rather than committing
per-row, to keep the WebSocket hot path to one round-trip per pass.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as db_models


async def upsert_session(
    db: AsyncSession, *, session_id: str, started_at: datetime, client_id: uuid.UUID | None = None
) -> db_models.Session:
    existing = await db.get(db_models.Session, session_id)
    if existing is not None:
        return existing
    row = db_models.Session(
        id=session_id, client_id=client_id, status="active", started_at=started_at
    )
    db.add(row)
    return row


async def end_session(
    db: AsyncSession,
    *,
    session_id: str,
    ended_at: datetime,
    final_risk_score: float,
    highest_risk_score: float,
    highest_severity: str,
) -> None:
    row = await db.get(db_models.Session, session_id)
    if row is None:
        return
    row.status = "ended"
    row.ended_at = ended_at
    row.final_risk_score = final_risk_score
    row.highest_risk_score = highest_risk_score
    row.highest_severity = highest_severity


async def save_transcript_segment(
    db: AsyncSession, *, session_id: str, sequence: int, text: str, is_final: bool,
    confidence: float | None, timestamp: datetime,
) -> None:
    db.add(
        db_models.TranscriptSegment(
            id=uuid.uuid4(), session_id=session_id, sequence=sequence, text=text,
            is_final=is_final, confidence=confidence, timestamp=timestamp,
        )
    )


async def save_risk_result(
    db: AsyncSession, *, session_id: str, risk_result, timestamp: datetime
) -> None:
    """`RiskResult` (app.models.risk) carries no timestamp of its own —
    the caller passes the same `now` used for the ProtectionEvent(s) built
    from this same analysis pass, so the two stay correlated."""
    db.add(
        db_models.RiskEvent(
            id=uuid.uuid4(),
            session_id=session_id,
            score=risk_result.score,
            severity=risk_result.severity.value,
            confidence=risk_result.confidence,
            evidence_state=risk_result.evidence_state.value,
            explanation=risk_result.explanation,
            recommended_action=risk_result.recommended_action.value,
            risk_factors=[rf.model_dump(mode="json") for rf in risk_result.risk_factors],
            timestamp=timestamp,
        )
    )


async def save_evidence(db: AsyncSession, *, evidence_item) -> None:
    db.add(
        db_models.Evidence(
            id=evidence_item.evidence_id,
            session_id=evidence_item.session_id,
            timestamp=evidence_item.timestamp,
            source=evidence_item.source.value,
            text=evidence_item.text,
            signal=evidence_item.signal,
            category=evidence_item.category.value,
            severity=evidence_item.severity.value,
            risk_score=evidence_item.risk_score,
            confidence=evidence_item.confidence,
        )
    )


async def save_protection_event(db: AsyncSession, *, event) -> None:
    db.add(
        db_models.ProtectionEventRow(
            id=event.event_id,
            session_id=event.session_id,
            timestamp=event.timestamp,
            event_type=event.event_type.value,
            severity=event.severity.value,
            risk_score=event.risk_score,
            title=event.title,
            message=event.message,
            category=event.category.value,
            evidence=list(event.evidence),
            recommended_action=event.recommended_action,
            confidence=event.confidence,
        )
    )


async def save_timeline_event(db: AsyncSession, *, event) -> None:
    db.add(
        db_models.TimelineEventRow(
            id=event.event_id,
            session_id=event.session_id,
            timestamp=event.timestamp,
            label=event.label,
            category=event.category.value if event.category else None,
            severity=event.severity.value if event.severity else None,
            detail=event.detail,
            event_metadata=dict(event.metadata),
        )
    )


async def save_incident_event(db: AsyncSession, *, event) -> None:
    db.add(
        db_models.IncidentEventRow(
            id=event.timeline_event_id,
            session_id=event.session_id,
            timestamp=event.timestamp,
            event_type=event.event_type.value,
            title=event.title,
            description=event.description,
            severity=event.severity.value if event.severity else None,
            risk_score=event.risk_score,
            category=event.category.value if event.category else None,
            evidence_ids=[str(eid) for eid in event.evidence_ids],
        )
    )


async def save_risk_history_entry(db: AsyncSession, *, session_id: str, entry) -> None:
    db.add(
        db_models.RiskHistoryEntryRow(
            id=uuid.uuid4(),
            session_id=session_id,
            timestamp=entry.timestamp,
            previous_score=entry.previous_score,
            new_score=entry.new_score,
            severity=entry.severity.value,
            state=entry.state.value,
            trigger=entry.trigger.value,
        )
    )


async def save_voice_signal(db: AsyncSession, *, signal) -> None:
    db.add(
        db_models.VoiceSignalRow(
            id=signal.signal_id,
            session_id=signal.session_id,
            signal_type=signal.signal_type.value,
            category=signal.category.value,
            confidence=signal.confidence,
            severity=signal.severity.value,
            evidence_text=signal.evidence_text,
            timestamp=signal.timestamp,
            source=signal.source,
            signal_metadata=dict(signal.metadata),
        )
    )


async def save_voice_pattern(db: AsyncSession, *, pattern) -> None:
    db.add(
        db_models.VoicePatternRow(
            id=pattern.pattern_id,
            session_id=pattern.session_id,
            pattern_type=pattern.pattern_type,
            signals=[s.value for s in pattern.signals],
            confidence=pattern.confidence,
            evidence=list(pattern.evidence),
            timestamp=pattern.timestamp,
        )
    )


async def save_intervention(db: AsyncSession, *, intervention) -> None:
    """Upsert — a Phase 3 `Intervention` mutates in place (status,
    acknowledged_at, escalation) over its lifetime, so later calls for the
    same `intervention_id` must update, not duplicate."""
    existing = await db.get(db_models.InterventionRow, intervention.intervention_id)
    if existing is None:
        db.add(
            db_models.InterventionRow(
                intervention_id=intervention.intervention_id,
                session_id=intervention.session_id,
                timestamp=intervention.timestamp,
                priority=intervention.priority.value,
                risk_score=intervention.risk_score,
                title=intervention.title,
                message=intervention.message,
                category=intervention.category.value if intervention.category else None,
                recommended_action=intervention.recommended_action,
                requires_acknowledgement=intervention.requires_acknowledgement,
                status=intervention.status.value,
                source_event_id=intervention.source_event_id,
                evidence=list(intervention.evidence),
                expires_at=intervention.expires_at,
                escalated_from=intervention.escalated_from,
                acknowledged_at=getattr(intervention, "acknowledged_at", None),
                resolved_at=getattr(intervention, "resolved_at", None),
            )
        )
    else:
        existing.status = intervention.status.value
        existing.acknowledged_at = getattr(intervention, "acknowledged_at", None)
        existing.resolved_at = getattr(intervention, "resolved_at", None)
        existing.escalated_from = intervention.escalated_from


async def save_intervention_event(db: AsyncSession, *, session_id: str, event) -> None:
    """`InterventionEvent` (Phase 5, app.models.intervention_engine) carries
    no `session_id` field of its own — the caller (which already knows the
    session, since it built the event) supplies it explicitly."""
    db.add(
        db_models.InterventionEventRow(
            id=event.id,
            session_id=session_id,
            timestamp=event.timestamp,
            level=event.level.value,
            title=event.title,
            message=event.message,
            confidence=event.confidence,
            source=event.source,
            risk_score=event.risk_score,
            category=event.category.value if event.category else None,
        )
    )


async def save_guardian_alert(db: AsyncSession, *, session_id: str, alert) -> None:
    """Upsert — a `GuardianAlert` escalates/transitions in place (see
    `GuardianAlertManager`), same rationale as `save_intervention`.
    `GuardianAlert` carries no `session_id` field of its own — the caller
    (which owns the `GuardianAlertManager` instance for this session)
    supplies it explicitly."""
    existing = await db.get(db_models.GuardianAlertRow, alert.id)
    if existing is None:
        db.add(
            db_models.GuardianAlertRow(
                id=alert.id,
                session_id=session_id,
                timestamp=alert.timestamp,
                title=alert.title,
                message=alert.message,
                level=alert.level.value,
                status=alert.status.value,
                risk_score=alert.risk_score,
                confidence=alert.confidence,
                source=alert.source,
                category=alert.category.value if alert.category else None,
            )
        )
    else:
        existing.title = alert.title
        existing.message = alert.message
        existing.level = alert.level.value
        existing.status = alert.status.value
        existing.timestamp = alert.timestamp


async def save_guardian_alert_event(db: AsyncSession, *, event) -> None:
    db.add(
        db_models.GuardianAlertEventRow(
            id=uuid.uuid4(),
            alert_id=event.alert_id,
            event_type=event.event_type.value,
            timestamp=event.timestamp,
            details=dict(event.details),
        )
    )


async def save_session_summary(db: AsyncSession, *, session_id: str, summary, extra: dict) -> None:
    existing = await db.get(db_models.SessionSummaryRow, session_id)
    if existing is not None:
        return  # written once at session end; a second call is a no-op
    db.add(
        db_models.SessionSummaryRow(
            session_id=session_id,
            session_started_at=summary.session_started_at,
            session_ended_at=summary.session_ended_at,
            duration_seconds=summary.duration_seconds,
            highest_risk_score=summary.highest_risk_score,
            final_risk_score=summary.final_risk_score,
            highest_severity=summary.highest_severity.value,
            detected_categories=[c.value for c in summary.detected_categories],
            detected_signals=list(summary.detected_signals),
            warning_count=summary.warning_count,
            critical_alert_count=summary.critical_alert_count,
            recommended_final_action=summary.recommended_final_action,
            extra=extra,
        )
    )
