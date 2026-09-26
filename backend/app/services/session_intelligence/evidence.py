"""Evidence extraction for Session Intelligence.

Turns existing `ThreatSignal`s (from the existing scam detector, via the
Risk Engine) into `EvidenceItem`s for the frontend's evidence panel.
Never fabricates evidence -- every item is traceable to a real
`ThreatSignal` produced upstream by the existing pipeline.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.models.risk import RiskResult
from app.models.session_intelligence import EvidenceItem
from app.models.threat import ThreatSignal
from app.services.normalization import normalize_indicator
from app.services.protection.rules import classify_signal


def _dedup_key(signal: ThreatSignal) -> tuple[str, str]:
    """Dedup key: same indicator + same normalized evidence text.

    Repeated identical transcript chunks (the same signal re-detected on
    every re-analysis of a growing accumulated transcript) must not
    produce duplicate evidence, but two distinct pieces of evidence for
    the same signal (e.g. an OTP request followed by a PIN request) must
    both be kept -- see Phase 2 spec section 16.
    """
    normalized_text = " ".join(signal.evidence.strip().lower().split())
    return (normalize_indicator(signal.indicator), normalized_text)


def extract_evidence(
    session_id: str,
    signals: Sequence[ThreatSignal],
    risk_result: RiskResult,
    seen_keys: set[tuple[str, str]],
) -> list[EvidenceItem]:
    """Extract new, deduplicated evidence items from this analysis pass.

    `seen_keys` is the caller's session-scoped dedup set; it is mutated
    in place so subsequent calls in the same session never re-emit an
    already-seen (indicator, text) pair. Returns only the *new* items
    produced by this call.
    """
    new_items: list[EvidenceItem] = []

    for signal in signals:
        key = _dedup_key(signal)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        category = classify_signal(signal)
        new_items.append(
            EvidenceItem(
                session_id=session_id,
                timestamp=signal.timestamp,
                text=signal.evidence,
                signal=signal.indicator,
                category=category,
                severity=risk_result.severity,
                risk_score=risk_result.score,
                confidence=signal.confidence,
            )
        )

    return new_items
