"""Deterministic mock threat-intelligence provider."""

from app.models.threat_intelligence import (
    ThreatIntelligenceFinding,
    ThreatIntelligenceResult,
)
from app.services.threat_intelligence.interface import (
    ThreatIntelligenceProvider,
)


class MockThreatIntelligenceProvider(ThreatIntelligenceProvider):
    """Provider used for deterministic local development and tests."""

    async def investigate(
        self,
        targets: list[str],
    ) -> ThreatIntelligenceResult:
        findings: list[ThreatIntelligenceFinding] = []

        for target in targets:
            normalized = target.strip().lower()

            if "example-phishing.com" in normalized:
                findings.append(
                    ThreatIntelligenceFinding(
                        category="phishing",
                        indicator=target,
                        evidence=(
                            "Mock intelligence identifies this domain "
                            "as a known phishing indicator."
                        ),
                        provider_confidence=0.95,
                        source_url=target
                        if target.startswith("http")
                        else None,
                    )
                )

        return ThreatIntelligenceResult(
            findings=findings,
            provider="mock-threat-intelligence",
        )
