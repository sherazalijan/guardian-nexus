"""Phase 4 — session-scoped Voice Intelligence Service.

Mirrors the lifecycle of `app.services.protection.ProtectionService`,
`app.services.session_intelligence.SessionIntelligenceService`, and
`app.services.intervention.InterventionPolicyService`: one plain,
in-memory instance per Guardian Nexus session (e.g. one `/ws/audio`
connection), discarded when the session ends. No database, per Phase 4
scope.

This service owns exactly one responsibility: turning the *stateless*
per-call detector output into a deduplicated, session-level view for the
`voice_intelligence` WebSocket frame (Phase 4 spec, sections 7, 8, 13).
It does not touch the Risk Engine -- that integration happens earlier,
inside the LangGraph node (`app.agents.voice_intelligence_agent`), via
`app.services.voice_intelligence.bridge`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.voice_intelligence import VoiceSignal, VoicePattern, VoiceSignalType
from app.services.voice_intelligence.correlation import correlate_signals
from app.services.voice_intelligence.detector import detect_voice_signals


def _normalize_evidence(text: str) -> str:
    return " ".join(text.strip().lower().split())


@dataclass
class VoiceIntelligenceUpdate:
    """Result of one `VoiceIntelligenceService.process()` call.

    Only *new* signals/patterns not already surfaced this session --
    exactly what should go into the next `voice_intelligence` WS frame.
    Empty on a pass with nothing new to report (a valid, common result).
    """

    new_signals: list[VoiceSignal] = field(default_factory=list)
    new_patterns: list[VoicePattern] = field(default_factory=list)


class VoiceIntelligenceService:
    """Deduplicated, session-scoped view over the stateless detector."""

    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        self._all_signals: list[VoiceSignal] = []
        # Dedup key: (signal_type, normalized evidence). A genuinely new
        # evidence string for an already-seen signal type is allowed to
        # create a new event (Phase 4 spec, section 7).
        self._seen_signal_keys: set[tuple[str, str]] = set()
        self._seen_pattern_types: set[str] = set()

    @property
    def session_id(self) -> str:
        return self._session_id

    def process(self, transcript: str) -> VoiceIntelligenceUpdate:
        """Run detection + correlation over the current accumulated
        transcript and return only what's new since the last call.

        Never raises: callers (see `app.api.routes`) should still wrap
        this in their own try/except and use the stable
        `voice_intelligence_failed` error code, but a malformed/empty
        transcript here is itself a normal, zero-signal result.
        """
        detected = detect_voice_signals(transcript, self._session_id)

        new_signals: list[VoiceSignal] = []
        for signal in detected:
            key = (signal.signal_type.value, _normalize_evidence(signal.evidence_text))
            if key in self._seen_signal_keys:
                continue
            self._seen_signal_keys.add(key)
            self._all_signals.append(signal)
            new_signals.append(signal)

        patterns = correlate_signals(self._all_signals, self._session_id)
        new_patterns = [p for p in patterns if p.pattern_type not in self._seen_pattern_types]
        for p in new_patterns:
            self._seen_pattern_types.add(p.pattern_type)

        return VoiceIntelligenceUpdate(new_signals=new_signals, new_patterns=new_patterns)

    def all_signals(self) -> list[VoiceSignal]:
        return list(self._all_signals)

    def signal_types_seen(self) -> set[VoiceSignalType]:
        return {s.signal_type for s in self._all_signals}
