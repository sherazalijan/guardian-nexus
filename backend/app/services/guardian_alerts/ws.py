"""Phase 6 — `guardian_alert` WebSocket frame construction.

A pure function, kept separate from `app.api.routes` so its exact shape
(flat, not nested under `"data"`, matching the Phase 6 spec's example
verbatim) is directly unit-testable without a real WebSocket connection
or AssemblyAI provider.
"""

from __future__ import annotations

from typing import Any

from app.models.guardian_alert import GuardianAlert


def alert_to_ws_frame(alert: GuardianAlert) -> dict[str, Any]:
    """Build the `guardian_alert` frame payload for one alert.

    Matches the Phase 6 spec's example exactly: flat top-level fields
    (not wrapped in a `"data"` key, unlike most of this codebase's other
    frame types), `alert_id`/`level`/`status` as plain strings, and an
    ISO-8601 `timestamp`.
    """
    return {
        "type": "guardian_alert",
        "alert_id": str(alert.id),
        "level": alert.level.value,
        "status": alert.status.value,
        "title": alert.title,
        "message": alert.message,
        "risk_score": alert.risk_score,
        "confidence": alert.confidence,
        "timestamp": alert.timestamp.isoformat(),
    }
