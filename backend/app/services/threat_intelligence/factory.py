"""Threat-intelligence provider factory."""

from app.core.config import get_settings
from app.services.threat_intelligence.interface import (
    ThreatIntelligenceProvider,
)
from app.services.threat_intelligence.mock_provider import (
    MockThreatIntelligenceProvider,
)
from app.services.threat_intelligence.tavily_provider import (
    TavilyThreatIntelligenceProvider,
)


def create_threat_intelligence_provider() -> ThreatIntelligenceProvider:
    """Create the configured threat-intelligence provider."""
    settings = get_settings()

    provider = settings.threat_intelligence_provider

    if provider == "mock":
        return MockThreatIntelligenceProvider()

    if provider == "tavily":
        return TavilyThreatIntelligenceProvider()

    raise ValueError(
        f"Unsupported threat-intelligence provider: {provider}"
    )
