"""Deterministic mock explanation provider."""

from app.models.explanation import SecurityExplanation
from app.models.risk import RiskResult
from app.services.explanation.interface import ExplanationProvider


class MockExplanationProvider(ExplanationProvider):
    """Local deterministic explanation provider."""

    async def explain(
        self,
        risk_result: RiskResult,
    ) -> SecurityExplanation:
        return SecurityExplanation(
            summary=(
                f"Risk assessment: {risk_result.severity.value} "
                f"with a score of {risk_result.score:.1f}/100."
            ),
            reasoning=risk_result.explanation,
            recommended_action=risk_result.recommended_action.value,
            model_version="mock-explanation-v1",
        )
