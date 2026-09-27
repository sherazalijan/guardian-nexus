"""Phase 5/6 — Protection History Service.

In-memory only, one instance per session (mirrors the lifecycle of
`app.services.protection.ProtectionService` and the other per-connection
services already wired up in `app.api.routes`). Stores every
`InterventionEvent` the Phase 5 engine has raised this session.

Phase 6 addition (additive; nothing below this docstring's first
paragraph existed before Phase 5, and everything from Phase 5 is
unchanged): `record_alert()` / `all_alerts()` let `GuardianAlert`s
(Phase 6, `app.services.guardian_alerts`) appear in the same
per-session history alongside interventions, per the Phase 6 spec's
"Alerts should appear in history alongside interventions" requirement,
without changing `record()` / `all_events()` / `recent()` /
`count_by_level()`'s existing behavior or signatures.
"""

from __future__ import annotations

from app.models.guardian_alert import GuardianAlert
from app.models.intervention_engine import InterventionEvent


class ProtectionHistoryService:
    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        self._events: list[InterventionEvent] = []
        self._alerts: list[GuardianAlert] = []

    @property
    def session_id(self) -> str:
        return self._session_id

    # -- Phase 5: InterventionEvent history (unchanged) ---------------------

    def record(self, event: InterventionEvent) -> None:
        self._events.append(event)

    def all_events(self) -> list[InterventionEvent]:
        return list(self._events)

    def recent(self, limit: int = 10) -> list[InterventionEvent]:
        if limit <= 0:
            return []
        return list(self._events[-limit:])

    def count_by_level(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for event in self._events:
            counts[event.level.value] = counts.get(event.level.value, 0) + 1
        return counts

    # -- Phase 6: GuardianAlert history (additive) --------------------------

    def record_alert(self, alert: GuardianAlert) -> None:
        self._alerts.append(alert)

    def all_alerts(self) -> list[GuardianAlert]:
        return list(self._alerts)
