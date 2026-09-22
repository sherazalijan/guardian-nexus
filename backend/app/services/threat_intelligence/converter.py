"""Convert untrusted threat-intelligence findings into trusted signals."""

from datetime import datetime, timezone

from app.models.enums import ThreatCategory
from app.models.threat import ThreatSignal
from app.models.threat_intelligence import ThreatIntelligenceResult

SOURCE_RELIABILITY = 0.80


def convert_threat_intelligence(
    result: ThreatIntelligenceResult,
) -> list[ThreatSignal]:
    """Convert validated TI findings into Risk Engine signals."""
    signals: list[ThreatSignal] = []

    for finding in result.findings:
        try:
            category = ThreatCategory(
                finding.category.strip().lower()
            )
        except ValueError:
            continue

        confidence = max(
            0.0,
            min(
                finding.provider_confidence * SOURCE_RELIABILITY,
                1.0,
            ),
        )

        signals.append(
            ThreatSignal(
                category=category,
                indicator=finding.indicator,
                evidence=finding.evidence,
                confidence=confidence,
                source=f"ti:{result.provider}",
                metadata={
                    "source_url": finding.source_url,
                },
                timestamp=datetime.now(timezone.utc),
            )
        )

    return signals
