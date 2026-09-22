
"""Nebius Token Factory provider for NVIDIA Nemotron."""

import httpx

from app.core.config import get_settings
from app.models.llm_analysis import LLMAnalysis
from app.services.llm_analysis.interface import LLMAnalysisProvider
from app.services.llm_analysis.prompts import (
    SYSTEM_PROMPT,
    build_analysis_prompt,
)


class NebiusNemotronProvider(LLMAnalysisProvider):
    """Call NVIDIA Nemotron through Nebius Token Factory."""

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

    async def analyze(
        self,
        transcript: str,
    ) -> LLMAnalysis:
        """Analyze a transcript using Nemotron."""

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": build_analysis_prompt(transcript),
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

        return LLMAnalysis.model_validate_json(content)


def create_nebius_provider() -> NebiusNemotronProvider:
    """Create the Nebius provider from application settings."""

    settings = get_settings()

    if not settings.nebius_api_key:
        raise ValueError(
            "NEBIUS_API_KEY is required for the Nebius provider."
        )

    if not settings.nebius_model:
        raise ValueError(
            "NEBIUS_MODEL is required for the Nebius provider."
        )

    return NebiusNemotronProvider(
        api_key=settings.nebius_api_key,
        base_url=settings.nebius_base_url,
        model=settings.nebius_model,
        timeout_seconds=settings.llm_timeout_seconds,
    )
