"""Explanation provider factory."""

from app.core.config import get_settings
from app.services.explanation.interface import ExplanationProvider
from app.services.explanation.mock_provider import MockExplanationProvider


def create_explanation_provider() -> ExplanationProvider:
    """Create the configured explanation provider."""

    settings = get_settings()

    if settings.llm_provider == "mock":
        return MockExplanationProvider()

    if settings.llm_provider == "nebius":
        from app.services.explanation.nebius_provider import (
            create_nebius_explanation_provider,
        )

        return create_nebius_explanation_provider()

    raise ValueError(
        f"Unsupported explanation provider: {settings.llm_provider}"
    )
