"""Phase 4 — deterministic signal correlation.

Identifies combinations of `VoiceSignal`s that represent stronger,
named scam patterns (Phase 4 spec, section 4). This is explicitly NOT a
second risk score: `VoicePattern.confidence` is a 0.0-1.0 corroboration
strength, never a 0-100 value, and it is never fed into
`app.services.risk_engine` -- only the underlying `ThreatSignal`s are
(see `app.services.voice_intelligence.bridge`).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.voice_intelligence import VoiceSignal, VoicePattern, VoiceSignalType

_T = VoiceSignalType


@dataclass(frozen=True)
class CorrelationRule:
    pattern_type: str
    required: frozenset[VoiceSignalType]
    """Every one of these signal types must be present for a match."""
    any_of: tuple[frozenset[VoiceSignalType], ...] = ()
    """If non-empty, at least one signal type from each group must be present."""


CORRELATION_RULES: tuple[CorrelationRule, ...] = (
    CorrelationRule(
        pattern_type="bank_credential_scam",
        required=frozenset({_T.URGENCY_PRESSURE, _T.SENSITIVE_INFORMATION_REQUEST}),
        any_of=(
            frozenset({_T.AUTHORITY_IMPERSONATION, _T.ACCOUNT_COMPROMISE_CLAIM}),
        ),
    ),
    CorrelationRule(
        pattern_type="remote_access_scam",
        required=frozenset(
            {
                _T.TECHNICAL_SUPPORT_IMPERSONATION,
                _T.REMOTE_ACCESS_REQUEST,
                _T.URGENCY_PRESSURE,
            }
        ),
    ),
    CorrelationRule(
        pattern_type="coercive_payment_scam",
        required=frozenset({_T.AUTHORITY_IMPERSONATION, _T.THREAT_INTIMIDATION}),
        any_of=(
            frozenset(
                {_T.PAYMENT_REQUEST, _T.GIFT_CARD_REQUEST, _T.CRYPTO_REQUEST}
            ),
        ),
    ),
    CorrelationRule(
        pattern_type="isolation_scam",
        required=frozenset({_T.SECRECY_ISOLATION, _T.VERIFICATION_BYPASS}),
    ),
)


def correlate_signals(
    signals: list[VoiceSignal], session_id: str
) -> list[VoicePattern]:
    """Find every `CorrelationRule` fully satisfied by the given signals.

    `signals` should be every distinct signal seen so far *this session*
    (see `VoiceIntelligenceService`), not just the latest transcript
    fragment -- correlation is a conversation-level property.
    """
    by_type: dict[VoiceSignalType, VoiceSignal] = {}
    for signal in signals:
        # Keep the highest-confidence signal per type as the pattern's
        # representative evidence.
        existing = by_type.get(signal.signal_type)
        if existing is None or signal.confidence > existing.confidence:
            by_type[signal.signal_type] = signal

    present_types = set(by_type.keys())
    patterns: list[VoicePattern] = []

    for rule in CORRELATION_RULES:
        if not rule.required.issubset(present_types):
            continue
        if not all(present_types & group for group in rule.any_of):
            continue

        matched_types = set(rule.required)
        for group in rule.any_of:
            matched_types |= present_types & group

        matched_signals = [by_type[t] for t in sorted(matched_types, key=lambda x: x.value)]
        confidence = min(
            1.0, sum(s.confidence for s in matched_signals) / len(matched_signals)
        )

        patterns.append(
            VoicePattern(
                session_id=session_id,
                pattern_type=rule.pattern_type,
                signals=[s.signal_type for s in matched_signals],
                confidence=round(confidence, 4),
                evidence=[s.evidence_text for s in matched_signals],
            )
        )

    return patterns
