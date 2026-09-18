from datetime import datetime, timezone

from app.models.enums import ThreatCategory
from app.models.threat import ThreatSignal
from app.services.aggregation import (
    aggregate_risk_score,
    signal_base_score,
)


def make_signal(
    category: ThreatCategory,
    confidence: float,
) -> ThreatSignal:
    return ThreatSignal(
        category=category,
        indicator="test indicator",
        evidence="test evidence",
        confidence=confidence,
        source="test-source",
        timestamp=datetime.now(timezone.utc),
    )


def test_empty_signals_produce_zero():
    assert aggregate_risk_score([]) == 0.0


def test_base_score_uses_category_weight_and_confidence():
    signal = make_signal(
        ThreatCategory.MALWARE,
        1.0,
    )

    assert signal_base_score(signal) == 70.0


def test_confidence_scales_base_score():
    signal = make_signal(
        ThreatCategory.MALWARE,
        0.5,
    )

    assert signal_base_score(signal) == 35.0


def test_single_signal_equals_base_score():
    signal = make_signal(
        ThreatCategory.PHISHING,
        1.0,
    )

    assert aggregate_risk_score([signal]) == 55.0


def test_multiple_signals_use_diminishing_returns():
    primary = make_signal(
        ThreatCategory.MALWARE,
        1.0,
    )

    secondary = make_signal(
        ThreatCategory.FRAUD,
        1.0,
    )

    score = aggregate_risk_score(
        [primary, secondary]
    )

    # 70 + (60 * 0.30) = 88
    assert score == 88.0


def test_weak_signals_do_not_overwhelm_primary_signal():
    primary = make_signal(
        ThreatCategory.MALWARE,
        1.0,
    )

    weak_signals = [
        make_signal(
            ThreatCategory.SUSPICIOUS_CALL,
            0.1,
        )
        for _ in range(20)
    ]

    score = aggregate_risk_score(
        [primary, *weak_signals]
    )

    assert score < 100.0
    assert score > 70.0


def test_score_is_capped_at_100():
    signals = [
        make_signal(
            ThreatCategory.MALWARE,
            1.0,
        ),
        make_signal(
            ThreatCategory.FRAUD,
            1.0,
        ),
        make_signal(
            ThreatCategory.PHISHING,
            1.0,
        ),
        make_signal(
            ThreatCategory.IMPERSONATION,
            1.0,
        ),
        make_signal(
            ThreatCategory.MALICIOUS_LINK,
            1.0,
        ),
    ]

    assert aggregate_risk_score(signals) <= 100.0