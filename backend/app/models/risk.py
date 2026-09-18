from pydantic import BaseModel, Field

from app.models.enums import EvidenceState, RecommendedAction, ThreatSeverity


class RiskFactor(BaseModel):
    """A structured factor contributing to a risk assessment."""

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    contribution: float


class RiskResult(BaseModel):
    """Structured result produced by the deterministic risk engine."""

    score: float = Field(ge=0.0, le=100.0)
    severity: ThreatSeverity
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_state: EvidenceState = EvidenceState.INSUFFICIENT
    risk_factors: list[RiskFactor] = Field(default_factory=list)
    explanation: str = Field(min_length=1)
    recommended_action: RecommendedAction
