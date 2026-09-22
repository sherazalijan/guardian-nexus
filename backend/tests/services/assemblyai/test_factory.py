"""Tests for create_assemblyai_provider() provider selection.

Constructing the realtime provider here does not connect to AssemblyAI --
it only builds a RealtimeAssemblyAIProvider instance. No network access.
"""

from __future__ import annotations

import pytest

from app.core.config import Settings, get_settings
from app.services.assemblyai.factory import (
    create_assemblyai_provider,
    get_assemblyai_client,
)
from app.services.assemblyai.mock_provider import MockAssemblyAIClient
from app.services.assemblyai.realtime_provider import RealtimeAssemblyAIProvider


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


def test_mock_provider_selected_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setattr(
        "app.services.assemblyai.factory.get_settings",
        lambda: _settings(assemblyai_provider="mock"),
    )

    provider = create_assemblyai_provider()

    assert isinstance(provider, MockAssemblyAIClient)


def test_realtime_provider_selected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.assemblyai.factory.get_settings",
        lambda: _settings(assemblyai_provider="realtime", assemblyai_api_key="test-key"),
    )

    provider = create_assemblyai_provider()

    assert isinstance(provider, RealtimeAssemblyAIProvider)


def test_provider_value_is_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.assemblyai.factory.get_settings",
        lambda: _settings(assemblyai_provider="  Realtime  ", assemblyai_api_key="test-key"),
    )

    provider = create_assemblyai_provider()

    assert isinstance(provider, RealtimeAssemblyAIProvider)


def test_unsupported_provider_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.assemblyai.factory.get_settings",
        lambda: _settings(assemblyai_provider="not-a-real-provider"),
    )

    with pytest.raises(ValueError):
        create_assemblyai_provider()


def test_deprecated_alias_still_returns_configured_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.assemblyai.factory.get_settings",
        lambda: _settings(assemblyai_provider="mock"),
    )

    provider = get_assemblyai_client()

    assert isinstance(provider, MockAssemblyAIClient)
