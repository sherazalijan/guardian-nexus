"""Phase 4 — bridge `VoiceSignal` into the *existing* `ThreatSignal` model.

This is the entire integration point with the Risk Engine (Phase 4 spec,
section 9). It creates no new risk input mechanism: it just produces the
exact same `app.models.threat.ThreatSignal` objects `app.agents.scam_agent`
already produces, so `app.services.risk_engine.run_risk_engine` -- and its
existing normalization/deduplication (`app.services.normalization`) --
handles them identically, with no code changes to the Risk Engine itself.
"""

from __future__ import annotations

from app.models.threat import ThreatSignal
from app.models.voice_intelligence import VoiceSignal


def voice_signal_to_threat_signal(signal: VoiceSignal) -> ThreatSignal:
    """Convert one `VoiceSignal` into a `ThreatSignal` for the Risk Engine."""
    return ThreatSignal(
        category=signal.category,
        indicator=signal.signal_type.value,
        evidence=signal.evidence_text,
        confidence=signal.confidence,
        source=signal.source,
        metadata={**signal.metadata, "voice_signal_id": str(signal.signal_id)},
        timestamp=signal.timestamp,
    )


def voice_signals_to_threat_signals(signals: list[VoiceSignal]) -> list[ThreatSignal]:
    return [voice_signal_to_threat_signal(s) for s in signals]
