"""Phase 4 — stateless voice-scam-behavior detector.
 
Mirrors `app.agents.scam_agent`: a pure function over a transcript string,
no session state, no LLM, no network access. Cross-call deduplication
(so a live, growing accumulated transcript doesn't re-emit the same
signal every pass) is handled one layer up, by
`app.services.voice_intelligence.service.VoiceIntelligenceService`, the
same way `ProtectionService` dedupes `ThreatSignal`s -- not here.
"""
 
from __future__ import annotations
 
import re
 
from app.models.voice_intelligence import VoiceSignal
from app.services.voice_intelligence.rules import VOICE_RULES, VOICE_INTELLIGENCE_SOURCE
 
 
def detect_voice_signals(transcript: str, session_id: str) -> list[VoiceSignal]:
    """Detect behavioral voice-scam signals in a transcript.
 
    Never raises: an empty/whitespace-only transcript simply yields no
    signals. A rule can produce more than one signal per call if two of
    its patterns match textually distinct spans (e.g. "verification
    code" earlier in the call and "PIN number" later) -- this is what
    lets `VoiceIntelligenceService`'s evidence-level dedup (Phase 4 spec,
    section 7) recognize a genuinely new request of the same
    `signal_type` on a growing, re-scanned accumulated transcript,
    instead of only ever reporting whichever pattern happens to be
    listed first for that rule. Multiple *distinct* rules can, of
    course, also fire on the same call (e.g. "give me the code now" ->
    both urgency_pressure and sensitive_information_request).
    """
    text = (transcript or "").strip()
    if not text:
        return []
 
    signals: list[VoiceSignal] = []
    for rule in VOICE_RULES:
        for evidence in _all_distinct_matches(rule.patterns, text):
            signals.append(
                VoiceSignal(
                    session_id=session_id,
                    signal_type=rule.signal_type,
                    category=rule.category,
                    confidence=rule.confidence,
                    severity=rule.severity,
                    evidence_text=evidence,
                    source=VOICE_INTELLIGENCE_SOURCE,
                    metadata={"rule": rule.name},
                )
            )
 
    return signals
 
 
def _all_distinct_matches(patterns: tuple[str, ...], text: str) -> list[str]:
    """Every distinct (case-insensitive) matched span across all of a
    rule's patterns, in pattern/appearance order, deduplicated."""
    seen: set[str] = set()
    results: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            evidence = match.group(0)
            key = " ".join(evidence.strip().lower().split())
            if key in seen:
                continue
            seen.add(key)
            results.append(evidence)
    return results
