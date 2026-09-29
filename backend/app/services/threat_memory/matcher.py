"""Phase 8 — deterministic Threat Memory matching.

Per the phase brief: "Implement a deterministic first version. Do NOT
introduce vector databases... Do NOT add an embedding model... Start
with structured matching."

Input: the CURRENT session's accumulated signal state — the set of
`VoiceSignalType` values seen so far (`VoiceIntelligenceService.
signal_types_seen()`) plus the set of `SecurityCategory` values detected
(`ProtectionSessionState.detected_categories`). Both are already
maintained in-memory by existing services; this module adds no new
detection, only a comparison against persisted `ThreatIndicator` rows.

Output: a 0.0-1.0 `match_score` per threat, using weighted Jaccard-style
overlap — NOT a re-run of the Risk Engine, and never fed into it (same
principle as `VoicePattern.confidence`, see `app.models.voice_intelligence`
docstring).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.db.threat_memory_models import Threat, ThreatIndicator

# Below this, a "match" is noise — two unrelated threats sharing one
# generic indicator (e.g. both involving "urgency_pressure") should not
# surface a known-threat alert on their own.
MATCH_THRESHOLD = 0.6


@dataclass(frozen=True)
class SessionSignature:
    """The current session's structured signal state, as seen by Threat
    Memory. Built by the caller (see `app.services.persistence.hooks`)
    from data the existing in-memory services already track — nothing
    new is detected here."""

    signal_types: frozenset[str]
    """VoiceSignalType values seen so far this session."""
    categories: frozenset[str]
    """SecurityCategory values detected so far this session."""


@dataclass(frozen=True)
class MatchResult:
    threat: Threat
    score: float
    matched_indicator_ids: list[str]
    matched_pattern_types: list[str]


def score_match(signature: SessionSignature, threat: Threat) -> MatchResult:
    """Weighted overlap between a session's signature and one threat's
    persisted indicators/patterns.

    score = (sum of weights of matched indicators) / (sum of weights of
    all indicators for this threat), bounded to [0, 1]. A threat with no
    indicators scores 0 rather than raising — a data-entry gap should
    never crash matching.
    """
    indicators = threat.indicators
    if not indicators:
        return MatchResult(threat=threat, score=0.0, matched_indicator_ids=[], matched_pattern_types=[])

    total_weight = sum(i.weight for i in indicators) or 1.0
    matched: list[ThreatIndicator] = []

    for indicator in indicators:
        if indicator.signal_type and indicator.signal_type in signature.signal_types:
            matched.append(indicator)
        elif indicator.category and indicator.category in signature.categories:
            matched.append(indicator)

    matched_weight = sum(i.weight for i in matched)
    score = min(1.0, matched_weight / total_weight)

    matched_pattern_types = [
        p.pattern_type
        for p in threat.patterns
        if set(p.required_signal_types).issubset(signature.signal_types)
    ]

    return MatchResult(
        threat=threat,
        score=round(score, 4),
        matched_indicator_ids=[str(i.id) for i in matched],
        matched_pattern_types=matched_pattern_types,
    )


def find_matches(
    signature: SessionSignature,
    candidate_threats: list[Threat],
    *,
    threshold: float = MATCH_THRESHOLD,
) -> list[MatchResult]:
    """Score every candidate threat and return those at/above `threshold`,
    highest score first. `candidate_threats` should be pre-filtered by the
    caller (e.g. only `status="active"` threats) — this function does no
    database access itself, keeping it trivially unit-testable."""
    results = [score_match(signature, t) for t in candidate_threats]
    return sorted(
        (r for r in results if r.score >= threshold),
        key=lambda r: r.score,
        reverse=True,
    )
