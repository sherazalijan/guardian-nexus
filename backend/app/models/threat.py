from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ThreatCategory


class ThreatSignal(BaseModel):
    """Structured evidence describing a detected threat signal."""

    category: ThreatCategory
    indicator: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    source: str = Field(min_length=1)
    metadata: dict[str, object] = Field(default_factory=dict)
    timestamp: datetime
