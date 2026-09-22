from app.services.llm_analysis.interface import LLMAnalysisProvider
from app.services.llm_analysis.mock_provider import MockLLMProvider


def test_mock_provider_implements_llm_provider():
    assert isinstance(MockLLMProvider(), LLMAnalysisProvider)