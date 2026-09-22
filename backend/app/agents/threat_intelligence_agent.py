"""Threat-intelligence LangGraph agent."""

from app.agents.state import GuardianGraphState
from app.models.graph import GraphError, NodeStatus
from app.services.threat_intelligence.converter import (
    convert_threat_intelligence,
)
from app.services.threat_intelligence.factory import (
    create_threat_intelligence_provider,
)


def _candidate_value(candidate: object) -> str:
    """Extract a candidate target from Pydantic or serialized state."""
    if isinstance(candidate, dict):
        return str(candidate.get("value", "")).strip()

    return str(getattr(candidate, "value", "")).strip()


async def threat_intelligence_agent(
    state: GuardianGraphState,
) -> GuardianGraphState:
    """Investigate candidate targets without making risk decisions."""

    targets = [
        value
        for candidate in state.get("candidate_targets", [])
        if (value := _candidate_value(candidate))
    ]

    status = dict(state.get("node_status", {}))
    errors = list(state.get("errors", []))

    if not targets:
        status["threat_intelligence"] = NodeStatus.SKIPPED

        return {
            **state,
            "threat_intelligence": None,
            "node_status": status,
            "errors": errors,
        }

    try:
        provider = create_threat_intelligence_provider()
        result = await provider.investigate(targets)

        ti_signals = convert_threat_intelligence(result)

        existing_signals = list(
            state.get("threat_signals", [])
        )

        status["threat_intelligence"] = NodeStatus.SUCCESS

        return {
            **state,
            "threat_intelligence": result,
            "threat_signals": existing_signals + ti_signals,
            "node_status": status,
            "errors": errors,
        }

    except Exception as exc:
        status["threat_intelligence"] = NodeStatus.FAILED

        errors.append(
            GraphError(
                node="threat_intelligence",
                code="THREAT_INTELLIGENCE_FAILED",
                message=str(exc),
            )
        )

        return {
            **state,
            "threat_intelligence": None,
            "node_status": status,
            "errors": errors,
        }
