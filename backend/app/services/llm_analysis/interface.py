"""Provider interface for LLM-based threat analysis."""

from abc import ABC, abstractmethod

from app.models.llm_analysis import LLMAnalysis


class LLMAnalysisProvider(ABC):
    """Abstract interface for Guardian Nexus LLM analysis providers."""

    @abstractmethod
    async def analyze(
        self,
        transcript: str,
    ) -> LLMAnalysis:
        """Analyze transcript content and return structured LLM analysis."""
        raise NotImplementedError