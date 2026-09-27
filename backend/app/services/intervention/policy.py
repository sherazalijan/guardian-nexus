"""
Phase 3 — InterventionPolicyService.

Session-scoped, in-memory, deterministic — mirrors the lifecycle of
`app.services.protection.ProtectionService` and
`app.services.session_intelligence.SessionIntelligenceService`: one
instance per Guardian Nexus session, discarded when the session ends.

Consumes `ProtectionEvent` objects already produced by
`ProtectionService.process()` (see `app.services.protection.service`).
It does NOT classify threats, does NOT score risk, and does NOT invent
new copy: `title`, `message`, `category`, and `recommended_action` are
carried over verbatim from the triggering `ProtectionEvent`, which
already went through `app.services.protection.rules` for that.

Priority is derived directly from the existing `ThreatSeverity` on each
event -- never a second, competing risk scale.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.models.enums import ThreatSeverity
from app.models.intervention import (
    Intervention,
    InterventionAckResult,
    InterventionHistory,
    InterventionPriority,
    InterventionStatus,
    priority_rank,
)
from app.models.protection import ProtectionEvent, ProtectionEventType, SecurityCategory
from app.services.protection.service import ProtectionAnalysisResult

logger = logging.getLogger("guardian_nexus.intervention")


# ---------------------------------------------------------------------------
# Configuration (deterministic constants)
# ---------------------------------------------------------------------------

# Derived from the EXISTING ThreatSeverity enum -- LOW collapses to NONE
# (no intervention for benign/low risk, per the Phase 3 brief).
SEVERITY_TO_PRIORITY: dict[ThreatSeverity, InterventionPriority] = {
    ThreatSeverity.LOW: InterventionPriority.NONE,
    ThreatSeverity.MEDIUM: InterventionPriority.MEDIUM,
    ThreatSeverity.HIGH: InterventionPriority.HIGH,
    ThreatSeverity.CRITICAL: InterventionPriority.CRITICAL,
}

COOLDOWN_SECONDS: dict[InterventionPriority, int] = {
    InterventionPriority.MEDIUM: 30,
    InterventionPriority.HIGH: 45,
    InterventionPriority.CRITICAL: 20,
}
DEFAULT_COOLDOWN_SECONDS = 30

EXPIRY_SECONDS: dict[InterventionPriority, int] = {
    InterventionPriority.MEDIUM: 120,
    InterventionPriority.HIGH: 180,
    InterventionPriority.CRITICAL: 300,
}
DEFAULT_EXPIRY_SECONDS = 120

REQUIRES_ACK_PRIORITIES = {InterventionPriority.HIGH, InterventionPriority.CRITICAL}

# Which ProtectionEvent types can trigger an intervention. RECOMMENDED_ACTION
# and SESSION_SUMMARY exist in the enum for other purposes and are not
# currently emitted by ProtectionService.process() as live warnings.
_ELIGIBLE_EVENT_TYPES = {
    ProtectionEventType.THREAT_DETECTED,
    ProtectionEventType.RISK_ESCALATED,
    ProtectionEventType.WARNING,
    ProtectionEventType.CRITICAL_ALERT,
    ProtectionEventType.SENSITIVE_INFORMATION_DETECTED,
}


@dataclass
class _EmissionRecord:
    time: datetime
    priority: InterventionPriority


class InterventionPolicyService:
    """
    Usage, per finalized transcript chunk, right after
    `ProtectionService.process()` has already run:

        analysis = protection_service.process(...)
        for intervention in intervention_service.decide(analysis):
            await websocket.send_json(intervention.to_ws_event())

    Acknowledge:

        result = intervention_service.acknowledge(intervention_id)

    Session end:

        intervention_service.resolve()
    """

    def __init__(
        self,
        session_id: str,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_id = session_id
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._history = InterventionHistory(session_id=session_id)
        # last non-resolved intervention per category, for escalation checks
        self._active_by_category: dict[SecurityCategory, Intervention] = {}
        # last emission time/priority per category (kept even after
        # resolve/expire, to prevent immediate re-spam of a just-closed warning)
        self._last_emission: dict[SecurityCategory, _EmissionRecord] = {}

    @property
    def session_id(self) -> str:
        return self._session_id

    # -- public API -----------------------------------------------------

    def decide(self, protection_result: ProtectionAnalysisResult) -> list[Intervention]:
        """Turn this pass's new ProtectionEvents into 0+ Interventions.

        Never raises: an intervention failure must not interrupt the live
        transcript/risk stream.
        """
        try:
            return self._decide(protection_result)
        except Exception:
            logger.exception(
                "intervention_failed session_id=%s -- transcript/risk flow continues",
                self._session_id,
            )
            return []

    def acknowledge(self, intervention_id: str) -> InterventionAckResult:
        target: Optional[Intervention] = next(
            (i for i in self._history.interventions if i.intervention_id == intervention_id),
            None,
        )
        if target is None:
            return InterventionAckResult(success=False, reason="not_found")

        if target.status == InterventionStatus.RESOLVED:
            return InterventionAckResult(
                success=False, reason="already_resolved",
                intervention_id=intervention_id, status=target.status,
            )
        if target.status == InterventionStatus.EXPIRED:
            return InterventionAckResult(
                success=False, reason="expired",
                intervention_id=intervention_id, status=target.status,
            )
        if target.status == InterventionStatus.ACKNOWLEDGED:
            return InterventionAckResult(
                success=True, reason="already_acknowledged",
                intervention_id=intervention_id, status=target.status,
            )

        target.status = InterventionStatus.ACKNOWLEDGED
        target.acknowledged_at = self._now()
        return InterventionAckResult(
            success=True, reason="acknowledged",
            intervention_id=intervention_id, status=target.status,
        )

    def resolve(self) -> None:
        """Call on session end. Finalizes any still-open interventions."""
        now = self._now()
        for iv in self._history.interventions:
            if iv.status in (InterventionStatus.ACTIVE, InterventionStatus.ACKNOWLEDGED):
                iv.status = InterventionStatus.RESOLVED
                iv.resolved_at = now
        self._active_by_category.clear()

    def history(self) -> InterventionHistory:
        return self._history

    def summary(self) -> dict:
        return self._history.summary()

    # -- internals --------------------------------------------------------

    def _decide(self, protection_result: ProtectionAnalysisResult) -> list[Intervention]:
        self._expire_stale()

        created: list[Intervention] = []
        for event in protection_result.events:
            if event.event_type not in _ELIGIBLE_EVENT_TYPES:
                continue

            priority = SEVERITY_TO_PRIORITY.get(event.severity, InterventionPriority.NONE)
            if priority == InterventionPriority.NONE:
                continue

            intervention = self._decide_for_event(event, priority)
            if intervention is not None:
                created.append(intervention)

        return created

    def _decide_for_event(
        self, event: ProtectionEvent, priority: InterventionPriority
    ) -> Optional[Intervention]:
        now = self._now()
        category = event.category
        existing = self._active_by_category.get(category)
        cooldown = COOLDOWN_SECONDS.get(priority, DEFAULT_COOLDOWN_SECONDS)
        last_emit = self._last_emission.get(category)
        escalated_from: Optional[str] = None

        if existing is not None and existing.status in (
            InterventionStatus.ACTIVE,
            InterventionStatus.ACKNOWLEDGED,
        ):
            if priority_rank(priority) <= priority_rank(existing.priority):
                # same/lower severity while an unresolved warning is live --
                # always suppress, acknowledgement does not mean "clear"
                return None
            # materially higher priority -> escalate, bypassing cooldown
            existing.status = InterventionStatus.ESCALATED
            escalated_from = existing.intervention_id
        elif last_emit is not None and (now - last_emit.time) < timedelta(seconds=cooldown):
            if priority_rank(priority) <= priority_rank(last_emit.priority):
                return None  # inside cooldown, not a genuine escalation

        intervention = Intervention(
            session_id=self._session_id,
            timestamp=now,
            priority=priority,
            risk_score=event.risk_score,
            title=event.title,
            message=event.message,
            category=category,
            recommended_action=event.recommended_action,
            requires_acknowledgement=priority in REQUIRES_ACK_PRIORITIES,
            status=InterventionStatus.ACTIVE,
            source_event_id=str(event.event_id),
            evidence=list(event.evidence),
            expires_at=now + timedelta(
                seconds=EXPIRY_SECONDS.get(priority, DEFAULT_EXPIRY_SECONDS)
            ),
            escalated_from=escalated_from,
        )

        self._history.interventions.append(intervention)
        self._active_by_category[category] = intervention
        self._last_emission[category] = _EmissionRecord(time=now, priority=priority)
        return intervention

    def _expire_stale(self) -> None:
        now = self._now()
        for category, iv in list(self._active_by_category.items()):
            if iv.status == InterventionStatus.ACTIVE and iv.expires_at and now > iv.expires_at:
                iv.status = InterventionStatus.EXPIRED
                del self._active_by_category[category]
