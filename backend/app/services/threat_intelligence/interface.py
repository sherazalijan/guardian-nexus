"""Abstract threat-intelligence provider interface."""

from abc import ABC, abstractmethod

from app.models.threat_intelligence import ThreatIntelligenceResult


class ThreatIntelligenceProvider(ABC):
    """Interface implemented by threat-intelligence providers."""

    @abstractmethod
    async def investigate(
        self,
        targets: list[str],
    ) -> ThreatIntelligenceResult:
        """Investigate candidate threat targets."""
        raise NotImplementedError
