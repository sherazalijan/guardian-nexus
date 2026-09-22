from app.models.threat_intelligence import (
    ThreatIntelligenceFinding,
    ThreatIntelligenceResult,
)
from app.services.threat_intelligence.converter import (
    convert_threat_intelligence,
)


def test_convert_threat_intelligence():
    result = ThreatIntelligenceResult(
        provider="mock-threat-intelligence",
        findings=[
            ThreatIntelligenceFinding(
                category="phishing",
                indicator="example-phishing.com",
                evidence="Known phishing indicator.",
                provider_confidence=0.95,
                source_url="https://example-phishing.com",
            )
        ],
    )

    signals = convert_threat_intelligence(result)

    assert len(signals) == 1
    assert signals[0].category.value == "phishing"
    assert signals[0].indicator == "example-phishing.com"
    assert signals[0].source == "ti:mock-threat-intelligence"
    assert signals[0].confidence == 0.76


def test_invalid_category_is_ignored():
    result = ThreatIntelligenceResult(
        provider="mock-threat-intelligence",
        findings=[
            ThreatIntelligenceFinding(
                category="not-a-real-category",
                indicator="something",
                evidence="Evidence.",
                provider_confidence=1.0,
            )
        ],
    )

    assert convert_threat_intelligence(result) == []
