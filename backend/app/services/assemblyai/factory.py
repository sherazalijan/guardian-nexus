"""Factory for constructing AssemblyAIClient instances.

Mirrors the convention established by the other Guardian Nexus provider
factories (see `app/services/llm_analysis/factory.py`,
`app/services/threat_intelligence/factory.py`,
`app/services/explanation/factory.py`): a single `create_*` function that
reads `app.core.config.get_settings()` and returns a concrete instance of
the relevant interface, raising `ValueError` for an unsupported provider
value -- the same error type every other provider factory in this codebase
already uses for this exact situation.

Provider selection is driven by `Settings.assemblyai_provider`
(env var `ASSEMBLYAI_PROVIDER`):

    ASSEMBLYAI_PROVIDER=mock      -> MockAssemblyAIClient
    ASSEMBLYAI_PROVIDER=realtime  -> RealtimeAssemblyAIProvider

`RealtimeAssemblyAIProvider` itself validates `ASSEMBLYAI_API_KEY` (via
`ConfigurationError`) when `connect()` is called -- not here at
construction time -- consistent with the interface only defining
`connect()` as the point where a session actually needs credentials.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.services.assemblyai.interface import AssemblyAIClient
from app.services.assemblyai.mock_provider import MockAssemblyAIClient
from app.services.assemblyai.realtime_provider import RealtimeAssemblyAIProvider

_MOCK = "mock"
_REALTIME = "realtime"


def create_assemblyai_provider() -> AssemblyAIClient:
    """Create the configured AssemblyAIClient provider."""

    settings = get_settings()

    provider = settings.assemblyai_provider.strip().lower()

    if provider == _MOCK:
        return MockAssemblyAIClient()

    if provider == _REALTIME:
        return RealtimeAssemblyAIProvider(api_key=settings.assemblyai_api_key)

    raise ValueError(
        f"Unsupported ASSEMBLYAI_PROVIDER: {settings.assemblyai_provider}"
    )


def get_assemblyai_client() -> AssemblyAIClient:
    """Deprecated alias for `create_assemblyai_provider()`.

    Phase 7.2 introduced this factory under the name `get_assemblyai_client`.
    Phase 7.3 renames the canonical entry point to `create_assemblyai_provider`
    to match the rest of the codebase's `create_*_provider()` convention.
    This alias is kept only so any existing call sites (if any) and the
    Phase 7.2 tests referencing the old name don't break. New code should
    call `create_assemblyai_provider()` directly; once nothing references
    this alias, it can be deleted.
    """
    return create_assemblyai_provider()
