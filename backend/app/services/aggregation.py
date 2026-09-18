"""Deterministic risk-score aggregation."""

from collections.abc import Sequence

from app.models.threat import ThreatSignal
from app.services.constants import (
    CATEGORY_WEIGHTS,
    CORROBORATION_CAP,
    CORROBORATION_DECAY,
    CORROBORATION_FACTOR,
    MAX_SCORE,
    MIN_SCORE,
)


def signal_base_score(signal: ThreatSignal) -> float:
    """
    Calculate the base contribution of a single threat signal.

    Confidence scales the configured category weight. The result is
    bounded to the global score range.
    """
    weight = CATEGORY_WEIGHTS.get(signal.category, 0.0)

    score = weight * signal.confidence

    return max(MIN_SCORE, min(score, MAX_SCORE))


def aggregate_risk_score(
    signals: Sequence[ThreatSignal],
) -> float:
    """
    Aggregate threat signals into a deterministic 0–100 risk score.

    The strongest signal establishes the base score. Additional signals
    contribute using diminishing returns so repeated weak evidence cannot
    overwhelm a strong primary signal.
    """
    if not signals:
        return MIN_SCORE

    contributions = sorted(
        (signal_base_score(signal) for signal in signals),
        reverse=True,
    )

    base_score = contributions[0]

    additional_contributions = contributions[1:]

    corroboration = 0.0

    for index, contribution in enumerate(additional_contributions, start=1):
        corroboration += (
            contribution
            * (CORROBORATION_DECAY ** (index - 1))
            * CORROBORATION_FACTOR
        )

    corroboration = min(corroboration, CORROBORATION_CAP)

    return max(
        MIN_SCORE,
        min(base_score + corroboration, MAX_SCORE),
    )