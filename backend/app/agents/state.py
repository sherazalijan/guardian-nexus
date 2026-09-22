from typing import Any, TypedDict
from uuid import UUID

from app.models.graph import CandidateTarget, GraphError, NodeStatus
from app.models.explanation import SecurityExplanation
from app.models.llm_analysis import LLMAnalysis
from app.models.threat_intelligence import ThreatIntelligenceResult
from app.models.threat import ThreatSignal
from app.models.risk import RiskResult


class GuardianGraphState(TypedDict, total=False):
    # Immutable request/session context
    session_id: UUID
    transcript: str
    metadata: dict[str, Any]

    # Analysis outputs
    llm_analysis: LLMAnalysis | None
    threat_signals: list[ThreatSignal]
    candidate_targets: list[CandidateTarget]

    # Threat intelligence
    threat_intelligence: ThreatIntelligenceResult | None

    # Final deterministic decision
    risk_result: RiskResult | None
    explanation: SecurityExplanation | None

    # Operational state
    errors: list[GraphError]
    node_status: dict[str, NodeStatus]
