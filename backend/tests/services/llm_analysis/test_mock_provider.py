import asyncio

from app.services.llm_analysis.mock_provider import MockLLMProvider


def test_mock_detects_otp_request():
    provider = MockLLMProvider()

    result = asyncio.run(
        provider.analyze(
            "Please send me the verification code you received."
        )
    )

    assert result.model_version == "mock-v1"
    assert len(result.signals) == 1
    assert result.signals[0].category == "scam"
    assert result.signals[0].model_confidence == 0.95


def test_mock_detects_suspicious_link():
    provider = MockLLMProvider()

    result = asyncio.run(
        provider.analyze(
            "Click this link immediately to verify your account."
        )
    )

    assert len(result.signals) == 1
    assert result.signals[0].category == "malicious_link"


def test_mock_returns_no_signal_for_unknown_input():
    provider = MockLLMProvider()

    result = asyncio.run(
        provider.analyze(
            "Hello, how are you today?"
        )
    )

    assert result.signals == []