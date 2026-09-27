"""Phase 4 — Voice Scam Intelligence graph node.

Slots into the *existing* offline pipeline between `scam_agent` and the
risk-engine node (see `app.agents.graph.build_rule_based_guardian_graph`):

    scam_agent -> voice_intelligence_agent -> risk_engine

It does not replace `scam_agent` and does not compute risk. It runs the
deterministic behavioral detector over the same transcript, converts any
detected `VoiceSignal`s into `ThreatSignal`s via
`app.services.voice_intelligence.bridge`, and *appends* them to the same
`threat_signals` list `scam_agent` already populated on `state` -- so the
unmodified `risk_engine` node (and its unmodified deduplication/
aggregation) sees one combined signal list, exactly per Phase 4 spec
section 9 ("extend the existing input mechanism, do not create a second
risk engine").

Also stores the raw `VoiceSignal`/`VoicePattern` objects on
`state["voice_signals"]` / `state["voice_patterns"]` (new, additive keys
on `GuardianState`) purely so `app.api.routes` can read them back for the
`voice_intelligence` WebSocket frame without re-running detection.

Never raises: an internal failure here must not break the existing
scam_agent -> risk_engine flow. On failure, `threat_signals` is left
exactly as `scam_agent` produced it, and empty voice_signals/voice_patterns
are recorded -- the transcript/risk pipeline continues uninterrupted, per
Phase 4 spec section 15. Callers that need to surface this failure to a
connected client (as the `voice_intelligence_failed` error code) should
still wrap the call site in their own try/except, since a graph node
cannot itself emit a WebSocket frame.
"""

from __future__ import annotations

import logging

from app.agents.rule_based_state import GuardianState
from app.services.voice_intelligence.bridge import voice_signals_to_threat_signals
from app.services.voice_intelligence.correlation import correlate_signals
from app.services.voice_intelligence.detector import detect_voice_signals

logger = logging.getLogger(__name__)


async def voice_intelligence_agent(state: GuardianState) -> GuardianState:
    """Detect voice-scam behavioral signals and feed them into the
    existing threat-signal pipeline."""
    transcript = (state.get("transcript") or "").strip()
    existing_threat_signals = list(state.get("threat_signals", []))

    if not transcript:
        return {
            **state,
            "voice_signals": [],
            "voice_patterns": [],
            "threat_signals": existing_threat_signals,
        }

    session_id = str(state.get("session_id") or "unknown-session")

    try:
        voice_signals = detect_voice_signals(transcript, session_id)
        voice_patterns = correlate_signals(voice_signals, session_id)
        bridged = voice_signals_to_threat_signals(voice_signals)

        return {
            **state,
            "voice_signals": voice_signals,
            "voice_patterns": voice_patterns,
            "threat_signals": existing_threat_signals + bridged,
        }
    except Exception:
        logger.exception(
            "voice_intelligence_failed: detection error for session %s; "
            "continuing with scam_agent signals only.",
            session_id,
        )
        return {
            **state,
            "voice_signals": [],
            "voice_patterns": [],
            "threat_signals": existing_threat_signals,
        }
