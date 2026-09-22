
"""Factory for Guardian Nexus LLM analysis providers."""

from app.core.config import get_settings
from app.services.llm_analysis.interface import LLMAnalysisProvider
from app.services.llm_analysis.mock_provider import MockLLMProvider
from app.services.llm_analysis.nebius_provider import (
    create_nebius_provider,
)


def create_llm_provider() -> LLMAnalysisProvider:
    """Create the configured LLM analysis provider."""

    settings = get_settings()

    provider = settings.llm_provider.strip().lower()

    if provider == "mock":
        return MockLLMProvider()

    if provider == "nebius":
        return create_nebius_provider()

    raise ValueError(
        f"Unsupported LLM_PROVIDER: {settings.llm_provider}"
    )
