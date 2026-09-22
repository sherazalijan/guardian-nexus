"""Models for untrusted LLM threat-analysis output."""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class LLMSignal(BaseModel):
    """A candidate threat signal proposed by an LLM."""

    category: str = Field(min_length=1)
    evidence_quote: str = Field(min_length=1)
    model_confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(min_length=1)


class LLMAnalysis(BaseModel):
    """Structured, untrusted analysis returned by an LLM provider."""

    signals: list[LLMSignal] = Field(default_factory=list)
    raw_model_notes: str = ""
    model_version: str = Field(min_length=1)
    analysis_id: UUID = Field(default_factory=uuid4)