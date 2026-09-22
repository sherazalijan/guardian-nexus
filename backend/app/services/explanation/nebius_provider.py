"""Nebius Token Factory provider for Nemotron security explanations."""

import httpx

from app.core.config import get_settings
from app.models.explanation import SecurityExplanation
from app.models.risk import RiskResult
from app.services.explanation.interface import ExplanationProvider


EXPLANATION_SYSTEM_PROMPT = """
You are the explanation layer of Guardian Nexus.

You receive a deterministic security risk assessment produced by the
Guardian Nexus Risk Engine.

The risk score, severity, evidence state, and recommended action are
AUTHORITATIVE. Never change, reinterpret, or contradict them.

Your job is ONLY to explain the assessment clearly to a non-technical user.

Return ONLY valid JSON with exactly these fields:
{
  "summary": "...",
  "reasoning": "...",
  "recommended_action": "...",
  "model_version": "..."
}

Do not invent evidence.
Do not add new threats.
Do not change the recommended action.
""".strip()


def build_explanation_prompt(risk_result: RiskResult) -> str:
    """Build a prompt from the deterministic risk result."""

    return f"""
Explain this Guardian Nexus risk assessment.

Score: {risk_result.score}
Severity: {risk_result.severity.value}
Evidence state: {risk_result.evidence_state.value}
Recommended action: {risk_result.recommended_action.value}

Risk factors:
{[
    {
        "name": factor.name,
        "description": factor.description,
        "contribution": factor.contribution,
    }
    for factor in risk_result.risk_factors
]}

Deterministic explanation:
{risk_result.explanation}
""".strip()


class NebiusNemotronExplanationProvider(ExplanationProvider):
    """Generate explanations using NVIDIA Nemotron through Nebius."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("Nebius API key is required.")

        if not model:
            raise ValueError("Nebius model is required.")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def explain(
        self,
        risk_result: RiskResult,
    ) -> SecurityExplanation:
        """Explain a deterministic risk result using Nemotron."""

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": EXPLANATION_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": build_explanation_prompt(risk_result),
                },
            ],
            "temperature": 0.0,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
        ) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]

        return SecurityExplanation.model_validate_json(content)


def create_nebius_explanation_provider(
    ) -> NebiusNemotronExplanationProvider:
    """Create the Nemotron explanation provider from settings."""

    settings = get_settings()

    if not settings.nebius_api_key:
        raise ValueError(
            "NEBIUS_API_KEY is required for the Nebius provider."
        )

    if not settings.nebius_model:
        raise ValueError(
            "NEBIUS_MODEL is required for the Nebius provider."
        )

    return NebiusNemotronExplanationProvider(
        api_key=settings.nebius_api_key,
        base_url=settings.nebius_base_url,
        model=settings.nebius_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )
