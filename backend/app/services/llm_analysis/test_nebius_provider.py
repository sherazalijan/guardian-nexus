"""Tests for the Nebius/Nemotron provider."""

import asyncio
import json

import httpx

from app.services.llm_analysis.nebius_provider import (
    NebiusNemotronProvider,
)


def make_response_content() -> str:
    return json.dumps(
        {
            "signals": [
                {
                    "category": "scam",
                    "evidence_quote": (
                        "Please send me the verification code."
                    ),
                    "model_confidence": 0.95,
                    "reasoning": (
                        "The caller requests a verification code."
                    ),
                }
            ],
            "raw_model_notes": "Potential scam detected.",
            "model_version": "test-nemotron",
        }
    )


class MockTransport:
    """Capture outgoing HTTP requests without making network calls."""

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.request: httpx.Request | None = None

    async def __call__(
        self,
        request: httpx.Request,
    ) -> httpx.Response:
        self.request = request
        return self.response


def test_nebius_provider_parses_valid_response():
    response = httpx.Response(
        status_code=200,
        json={
            "choices": [
                {
                    "message": {
                        "content": make_response_content(),
                    }
                }
            ]
        },
    )

    transport = MockTransport(response)

    provider = NebiusNemotronProvider(
        api_key="test-key",
        base_url="https://api.tokenfactory.nebius.com/v1",
        model="test-model",
    )

    original_client = httpx.AsyncClient

    class TestClient:
        def __init__(self, *args, **kwargs):
            self.client = original_client(
                transport=httpx.MockTransport(transport),
                *args,
                **kwargs,
            )

        async def __aenter__(self):
            return await self.client.__aenter__()

        async def __aexit__(self, *args):
            return await self.client.__aexit__(*args)

    import app.services.llm_analysis.nebius_provider as module

    original_async_client = module.httpx.AsyncClient
    module.httpx.AsyncClient = TestClient

    try:
        result = asyncio.run(
            provider.analyze("Please send me the verification code.")
        )
    finally:
        module.httpx.AsyncClient = original_async_client

    assert result.model_version == "test-nemotron"
    assert len(result.signals) == 1
    assert result.signals[0].category == "scam"

    assert transport.request is not None
    assert transport.request.url.path == "/v1/chat/completions"
    assert transport.request.headers["authorization"] == "Bearer test-key"


def test_nebius_provider_rejects_http_errors():
    response = httpx.Response(
        status_code=401,
        json={"error": "unauthorized"},
    )

    transport = MockTransport(response)

    provider = NebiusNemotronProvider(
        api_key="bad-key",
        base_url="https://api.tokenfactory.nebius.com/v1",
        model="test-model",
    )

    original_client = httpx.AsyncClient

    class TestClient:
        def __init__(self, *args, **kwargs):
            self.client = original_client(
                transport=httpx.MockTransport(transport),
                *args,
                **kwargs,
            )

        async def __aenter__(self):
            return await self.client.__aenter__()

        async def __aexit__(self, *args):
            return await self.client.__aexit__(*args)

    import app.services.llm_analysis.nebius_provider as module

    original_async_client = module.httpx.AsyncClient
    module.httpx.AsyncClient = TestClient

    try:
        failed = False
        try:
            asyncio.run(provider.analyze("test transcript"))
        except httpx.HTTPStatusError:
            failed = True
        assert failed
    finally:
        module.httpx.AsyncClient = original_async_client


def test_provider_requires_api_key():
    failed = False
    try:
        NebiusNemotronProvider(
            api_key="",
            base_url="https://api.tokenfactory.nebius.com/v1",
            model="test-model",
        )
    except ValueError as e:
        if "API key" in str(e):
            failed = True
    assert failed


def test_provider_requires_model():
    failed = False
    try:
        NebiusNemotronProvider(
            api_key="test-key",
            base_url="https://api.tokenfactory.nebius.com/v1",
            model="",
        )
    except ValueError as e:
        if "model" in str(e):
            failed = True
    assert failed