"""Phase 6 — Live Guardian Alert System.

Deterministic, in-memory, session-scoped. Consumes
`app.services.intervention_engine`'s `InterventionEvent` output (itself
unmodified) and turns it into deduplicated, escalating, lifecycle-managed
`GuardianAlert`s -- see `manager.GuardianAlertManager` for the dedup/
escalation design and `ws.alert_to_ws_frame` for the WebSocket shape.
"""

from app.services.guardian_alerts.manager import (
    ALERT_EXPIRATION_SECONDS,
    AlertOutcome,
    GuardianAlertManager,
)
from app.services.guardian_alerts.ws import alert_to_ws_frame

__all__ = [
    "GuardianAlertManager",
    "AlertOutcome",
    "ALERT_EXPIRATION_SECONDS",
    "alert_to_ws_frame",
]
