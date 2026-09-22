"""Deterministic mock LLM provider for tests and local development."""

from app.models.llm_analysis import LLMAnalysis, LLMSignal
from app.services.llm_analysis.interface import LLMAnalysisProvider


class MockLLMProvider(LLMAnalysisProvider):
    """Deterministic provider that never makes external API calls."""

    async def analyze(
        self,
        transcript: str,
    ) -> LLMAnalysis:
        """Return deterministic analysis based on transcript content."""

        normalized = transcript.lower()

        if "otp" in normalized or "verification code" in normalized:
            return LLMAnalysis(
                model_version="mock-v1",
                signals=[
                    LLMSignal(
                        category="scam",
                        evidence_quote=transcript,
                        model_confidence=0.95,
                        reasoning="The transcript contains a request for a verification code.",
                    )
                ],
                raw_model_notes="Deterministic mock analysis.",
            )

        if "click this link" in normalized or "click the link" in normalized:
            return LLMAnalysis(
                model_version="mock-v1",
                signals=[
                    LLMSignal(
                        category="malicious_link",
                        evidence_quote=transcript,
                        model_confidence=0.90,
                        reasoning="The transcript contains a suspicious link-click request.",
                    )
                ],
                raw_model_notes="Deterministic mock analysis.",
            )

        return LLMAnalysis(
            model_version="mock-v1",
            signals=[],
            raw_model_notes="No recognized threat pattern in mock provider.",
        )