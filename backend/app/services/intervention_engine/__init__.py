"""Phase 5 — Real-Time Intervention Engine.

Deterministic, rule-based (no LLMs, no external APIs). Consumes the
existing Risk Engine's `RiskResult.score`/`.confidence` and the existing
Voice Intelligence layer's `VoiceSignal`/`VoicePattern` output to decide
whether, and at what `InterventionLevel`, to surface a protective alert
to the user -- see `engine.decide` / `engine.build_event`.

Named `intervention_engine` (not `intervention`) and wired to a
dedicated `intervention_alert` WebSocket frame, deliberately apart from
the existing Phase 3 `app.services.intervention` /
`InterventionPolicyService` system already emitting `{"type":
"intervention", ...}` frames -- the two are independent and this package
does not modify that one.
"""

from app.services.intervention_engine.engine import build_event, decide
from app.services.intervention_engine.history import ProtectionHistoryService

__all__ = ["decide", "build_event", "ProtectionHistoryService"]
