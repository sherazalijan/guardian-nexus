"""Phase 5 — Real-Time Intervention Engine.

Consumes the outputs of three *existing, unmodified* systems --
`app.services.risk_engine.run_risk_engine`'s `RiskResult`,
`app.services.voice_intelligence`'s `VoiceSignal`/`VoicePattern` list --
and produces a deterministic `InterventionDecision` plus, if warranted,
an `InterventionEvent`. It reads those outputs; it never recomputes risk
and never touches the Risk Engine, Voice Intelligence, or Session
Intelligence internals.

Stateless and side-effect free by design (mirrors
`app.services.voice_intelligence.detector`): callers that need
session-level history (e.g. counting urgency signals across the whole
call) pass in everything the engine needs for this decision; persistence
of past `InterventionEvent`s belongs to
`app.services.intervention_engine.history.ProtectionHistoryService`.
"""

from __future__ import annotations

from app.models.intervention_engine import (
    InterventionDecision,
    InterventionEvent,
    InterventionLevel,
)
from app.models.voice_intelligence import VoicePattern, VoiceSignal
from app.services.intervention_engine.rules import INTERVENTION_RULES, RuleContext

_SOURCE = "intervention-engine"


def decide(
    risk_score: float,
    confidence: float,
    voice_signals: list[VoiceSignal],
    voice_patterns: list[VoicePattern],
) -> InterventionDecision:
    """Evaluate `INTERVENTION_RULES` in order; the first match wins."""
    signal_types = frozenset(s.signal_type for s in voice_signals)
    urgency_count = sum(1 for s in voice_signals if s.signal_type.value == "urgency_pressure")
    pattern_types = frozenset(p.pattern_type for p in voice_patterns)

    ctx = RuleContext(
        risk_score=risk_score,
        signal_types=signal_types,
        urgency_count=urgency_count,
        pattern_types=pattern_types,
    )

    for rule in INTERVENTION_RULES:
        if rule.predicate(ctx):
            return InterventionDecision(
                should_intervene=True,
                level=rule.level,
                reason=rule.name,
                confidence=confidence,
            )

    return InterventionDecision(
        should_intervene=False,
        level=InterventionLevel.INFO,
        reason="risk_below_intervention_threshold",
        confidence=confidence,
    )


def _rule_by_name(name: str):
    for rule in INTERVENTION_RULES:
        if rule.name == name:
            return rule
    return None


def build_event(
    decision: InterventionDecision,
    risk_score: float,
    voice_signals: list[VoiceSignal],
) -> InterventionEvent | None:
    """Build the user-facing `InterventionEvent` for a decision that
    warrants intervention. Returns None for a no-intervene decision --
    there is nothing to show the user."""
    if not decision.should_intervene:
        return None

    rule = _rule_by_name(decision.reason)
    if rule is None:
        # Defensive: should be unreachable since decide() only ever sets
        # `reason` to a real rule name when should_intervene is True.
        title, message = "Suspicious Call", "This call shows signs of a scam."
    else:
        title, message = rule.title, rule.message

    category = voice_signals[0].category if voice_signals else None

    return InterventionEvent(
        level=decision.level,
        title=title,
        message=message,
        confidence=decision.confidence,
        source=_SOURCE,
        risk_score=risk_score,
        category=category,
    )
