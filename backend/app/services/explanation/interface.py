"""Explanation provider interface."""

from abc import ABC, abstractmethod

from app.models.explanation import SecurityExplanation
from app.models.risk import RiskResult


class ExplanationProvider(ABC):
    """Interface for generating security explanations."""

    @abstractmethod
    async def explain(
        self,
        risk_result: RiskResult,
    ) -> SecurityExplanation:
        """Explain a deterministic risk assessment."""
        raise NotImplementedError
