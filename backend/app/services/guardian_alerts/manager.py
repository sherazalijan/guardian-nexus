"""Phase 6 — Guardian Alert Manager.

In-memory, one instance per session (same lifecycle as every other
per-connection service in `app.api.routes`). Turns `InterventionEvent`s
(from `app.services.intervention_engine`, itself unmodified and only
consumed here) into deduplicated, escalating, lifecycle-managed
`GuardianAlert`s.

Deduplication / escalation key: `category` (a `ThreatCategory`, falling
back to the literal string "general" when an event carries no category).
`category` is used rather than `title`/`message` text because the title
and message *change* across an escalation (e.g. "Potential OTP Scam" ->
"Critical Fraud Risk") while the underlying threat category is what
actually stays constant across repeated/escalating evidence of the same
kind of scam. This is documented here because it's the one non-obvious
design decision in this module -- see also section "Deduplication" in
the Phase 6 spec, which asks for this decision to be explicit.

Auto-expiration is comparison-based, not timer-based (`now` is always an
explicit, injectable parameter, defaulting to `datetime.now(timezone.utc)`
only at the call site) -- this is what makes it testable without a real
5-minute wait, per the spec's "Must be testable without waiting 5 real
minutes" requirement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.models.guardian_alert import AlertEvent, AlertEventType, AlertStatus, GuardianAlert
from app.models.intervention_engine import InterventionEvent, InterventionLevel

ALERT_EXPIRATION_SECONDS = 300

_LEVEL_RANK: dict[InterventionLevel, int] = {
    InterventionLevel.INFO: 0,
    InterventionLevel.WARNING: 1,
    InterventionLevel.HIGH_RISK: 2,
    InterventionLevel.CRITICAL: 3,
}

_GENERAL_KEY = "general"


def _dedup_key(event_category: str | None) -> str:
    return event_category or _GENERAL_KEY


@dataclass
class AlertOutcome:
    """Result of one `GuardianAlertManager.process()` call."""

    alert: GuardianAlert
    event_type: AlertEventType | None
    """None means a pure duplicate: no new alert, no escalation, and --
    per the anti-spam requirement -- nothing that should be re-streamed
    over the WebSocket."""


class GuardianAlertManager:
    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        self._alerts: dict[UUID, GuardianAlert] = {}
        self._active_key_to_id: dict[str, UUID] = {}
        self._events: list[AlertEvent] = []

    @property
    def session_id(self) -> str:
        return self._session_id

    # -- creation / dedup / escalation -----------------------------------

    def process(
        self, intervention_event: InterventionEvent, now: datetime | None = None
    ) -> AlertOutcome:
        """Feed one `InterventionEvent` in. Creates a new alert, escalates
        an existing active one, or is a no-op duplicate."""
        now = now or datetime.now(timezone.utc)
        category_value = (
            intervention_event.category.value if intervention_event.category else None
        )
        key = _dedup_key(category_value)

        existing_id = self._active_key_to_id.get(key)
        existing = self._alerts.get(existing_id) if existing_id else None

        if existing is not None and existing.status == AlertStatus.ACTIVE:
            if _LEVEL_RANK[intervention_event.level] > _LEVEL_RANK[existing.level]:
                previous_level = existing.level
                existing.level = intervention_event.level
                existing.title = intervention_event.title
                existing.message = intervention_event.message
                existing.risk_score = intervention_event.risk_score
                existing.confidence = intervention_event.confidence
                existing.timestamp = now
                self._record_event(
                    existing.id,
                    AlertEventType.ESCALATED,
                    {"from": previous_level.value, "to": existing.level.value},
                    now,
                )
                return AlertOutcome(alert=existing, event_type=AlertEventType.ESCALATED)

            # Same or lower level than the already-active alert for this
            # category: a duplicate. No new alert, no event, no re-stream.
            return AlertOutcome(alert=existing, event_type=None)

        alert = GuardianAlert(
            timestamp=now,
            title=intervention_event.title,
            message=intervention_event.message,
            level=intervention_event.level,
            status=AlertStatus.ACTIVE,
            risk_score=intervention_event.risk_score,
            confidence=intervention_event.confidence,
            source=intervention_event.source,
            category=intervention_event.category,
        )
        self._alerts[alert.id] = alert
        self._active_key_to_id[key] = alert.id
        self._record_event(alert.id, AlertEventType.CREATED, {"level": alert.level.value}, now)
        return AlertOutcome(alert=alert, event_type=AlertEventType.CREATED)

    # -- lifecycle ---------------------------------------------------------

    def acknowledge_alert(self, alert_id: UUID, now: datetime | None = None) -> GuardianAlert:
        return self._transition(alert_id, AlertStatus.ACKNOWLEDGED, AlertEventType.ACKNOWLEDGED, now)

    def dismiss_alert(self, alert_id: UUID, now: datetime | None = None) -> GuardianAlert:
        return self._transition(alert_id, AlertStatus.DISMISSED, AlertEventType.DISMISSED, now)

    def expire_alert(self, alert_id: UUID, now: datetime | None = None) -> GuardianAlert:
        return self._transition(alert_id, AlertStatus.EXPIRED, AlertEventType.EXPIRED, now)

    def expire_stale_alerts(
        self, now: datetime | None = None, expiration_seconds: int = ALERT_EXPIRATION_SECONDS
    ) -> list[GuardianAlert]:
        """Expire every ACTIVE alert last updated more than
        `expiration_seconds` before `now`. Leaves ACKNOWLEDGED/DISMISSED
        alerts untouched -- expiration only applies to alerts nobody has
        acted on."""
        now = now or datetime.now(timezone.utc)
        cutoff = timedelta(seconds=expiration_seconds)
        expired: list[GuardianAlert] = []
        for alert in list(self._alerts.values()):
            if alert.status == AlertStatus.ACTIVE and (now - alert.timestamp) >= cutoff:
                self._transition(alert.id, AlertStatus.EXPIRED, AlertEventType.EXPIRED, now)
                expired.append(alert)
        return expired

    def _transition(
        self,
        alert_id: UUID,
        new_status: AlertStatus,
        event_type: AlertEventType,
        now: datetime | None,
    ) -> GuardianAlert:
        now = now or datetime.now(timezone.utc)
        alert = self._alerts[alert_id]
        alert.status = new_status
        self._active_key_to_id = {
            k: v for k, v in self._active_key_to_id.items() if v != alert_id
        }
        self._record_event(alert_id, event_type, {"status": new_status.value}, now)
        return alert

    def _record_event(
        self, alert_id: UUID, event_type: AlertEventType, details: dict, now: datetime
    ) -> None:
        self._events.append(
            AlertEvent(alert_id=alert_id, event_type=event_type, timestamp=now, details=details)
        )

    # -- retrieval -----------------------------------------------------------

    def get_active_alerts(self) -> list[GuardianAlert]:
        return [a for a in self._alerts.values() if a.status == AlertStatus.ACTIVE]

    def get_alert_history(self) -> list[GuardianAlert]:
        """Every alert this session has ever produced, any status."""
        return list(self._alerts.values())

    def get_alert(self, alert_id: UUID) -> GuardianAlert | None:
        return self._alerts.get(alert_id)

    def get_alert_events(self) -> list[AlertEvent]:
        return list(self._events)
