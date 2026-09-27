"""Phase 4 — Voice Scam Intelligence.

Turns a call transcript into structured behavioral signals
(`app.models.voice_intelligence.VoiceSignal`) and deterministic
multi-signal patterns (`VoicePattern`), then feeds the signals into the
*existing* Risk Engine via `app.services.voice_intelligence.bridge` and
exposes a deduplicated, session-scoped view via
`VoiceIntelligenceService` for the `voice_intelligence` WebSocket frame.

This package does not classify risk and does not replace
`app.services.risk_engine` -- see `app.agents.voice_intelligence_agent`
for how it plugs into the existing offline pipeline.
"""

from app.services.voice_intelligence.service import (
    VoiceIntelligenceService,
    VoiceIntelligenceUpdate,
)

__all__ = ["VoiceIntelligenceService", "VoiceIntelligenceUpdate"]
