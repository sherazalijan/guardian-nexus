from datetime import datetime, timezone

from app.models.enums import ThreatCategory
from app.models.threat import ThreatSignal
from app.services.normalization import (
    deduplicate_signals,
    normalize_indicator,
    normalize_source,
)


def make_signal(
    *,
    indicator: str,
    confidence: float,
    source: str = "Agent-A",
) -> ThreatSignal:
    return ThreatSignal(
        category=ThreatCategory.SCAM,
        indicator=indicator,
        evidence="Test evidence",
        confidence=confidence,
        source=source,
        timestamp=datetime.now(timezone.utc),
    )


def test_normalize_indicator():
    assert normalize_indicator("  Credential   Request  ") == "credential request"


def test_normalize_source():
    assert normalize_source("  Agent-A  ") == "agent-a"


def test_deduplicate_signals_keeps_highest_confidence():
    signals = [
        make_signal(
            indicator="Credential Request",
            confidence=0.60,
        ),
        make_signal(
            indicator="  credential   request ",
            confidence=0.90,
        ),
    ]

    result = deduplicate_signals(signals)

    assert len(result) == 1
    assert result[0].confidence == 0.90
    assert result[0].indicator == "credential request"


def test_deduplicate_signals_keeps_distinct_sources():
    signals = [
        make_signal(
            indicator="Credential Request",
            confidence=0.80,
            source="Agent-A",
        ),
        make_signal(
            indicator="Credential Request",
            confidence=0.80,
            source="Agent-B",
        ),
    ]

    result = deduplicate_signals(signals)

    assert len(result) == 2


def test_deduplicate_signals_preserves_distinct_indicators():
    signals = [
        make_signal(
            indicator="Credential Request",
            confidence=0.80,
        ),
        make_signal(
            indicator="Payment Request",
            confidence=0.80,
        ),
    ]

    result = deduplicate_signals(signals)

    assert len(result) == 2