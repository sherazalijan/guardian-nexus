"""Models for untrusted threat-intelligence provider output."""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ThreatIntelligenceFinding(BaseModel):
    """A candidate finding returned by a threat-intelligence provider."""

    category: str = Field(min_length=1)
    indicator: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    provider_confidence: float = Field(ge=0.0, le=1.0)
    source_url: str | None = None


class ThreatIntelligenceResult(BaseModel):
    """Structured, untrusted threat-intelligence provider output."""

    findings: list[ThreatIntelligenceFinding] = Field(
        default_factory=list
    )
    provider: str = Field(min_length=1)
    result_id: UUID = Field(default_factory=uuid4)
