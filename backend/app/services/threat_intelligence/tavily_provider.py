"""Tavily-backed threat-intelligence provider."""

from typing import Any

import httpx

from app.core.config import get_settings
from app.models.threat_intelligence import (
    ThreatIntelligenceFinding,
    ThreatIntelligenceResult,
)
from app.services.threat_intelligence.interface import (
    ThreatIntelligenceProvider,
)


class TavilyThreatIntelligenceProvider(ThreatIntelligenceProvider):
    """Investigate candidate targets using Tavily Search."""

    endpoint = "https://api.tavily.com/search"

    async def investigate(
        self,
        targets: list[str],
    ) -> ThreatIntelligenceResult:
        settings = get_settings()

        if not settings.tavily_api_key:
            raise RuntimeError("TAVILY_API_KEY is not configured")

        findings: list[ThreatIntelligenceFinding] = []

        async with httpx.AsyncClient(timeout=15.0) as client:
            for target in targets:
                target = target.strip()

                if not target:
                    continue

                response = await client.post(
                    self.endpoint,
                    json={
                        "api_key": settings.tavily_api_key,
                        "query": (
                            f"Is this threat indicator associated with "
                            f"scams, phishing, fraud, malware, or impersonation? "
                            f"Indicator: {target}"
                        ),
                        "search_depth": "advanced",
                        "max_results": 5,
                        "include_answer": True,
                        "include_raw_content": False,
                    },
                )
                response.raise_for_status()

                payload: dict[str, Any] = response.json()

                answer = str(payload.get("answer") or "").strip()

                if answer:
                    findings.append(
                        ThreatIntelligenceFinding(
                            category="unknown",
                            indicator=target,
                            evidence=answer,
                            provider_confidence=0.5,
                            source_url=None,
                        )
                    )

                for result in payload.get("results", []):
                    if not isinstance(result, dict):
                        continue

                    content = str(result.get("content") or "").strip()
                    url = result.get("url")

                    if not content:
                        continue

                    findings.append(
                        ThreatIntelligenceFinding(
                            category="unknown",
                            indicator=target,
                            evidence=content,
                            provider_confidence=0.5,
                            source_url=str(url) if url else None,
                        )
                    )

        return ThreatIntelligenceResult(
            findings=findings,
            provider="tavily",
        )
