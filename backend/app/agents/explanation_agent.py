"""Guardian Nexus security explanation agent."""

from app.agents.state import GuardianGraphState
from app.models.graph import GraphError, NodeStatus
from app.services.explanation.factory import create_explanation_provider


async def explanation_agent(
    state: GuardianGraphState,
) -> GuardianGraphState:
    """Generate a human-readable explanation of the risk result."""

    risk_result = state.get("risk_result")

    status = dict(state.get("node_status", {}))
    errors = list(state.get("errors", []))

    if risk_result is None:
        status["explanation"] = NodeStatus.SKIPPED

        return {
            **state,
            "node_status": status,
            "errors": errors,
        }

    try:
        provider = create_explanation_provider()
        explanation = await provider.explain(risk_result)

        status["explanation"] = NodeStatus.SUCCESS

        return {
            **state,
            "explanation": explanation,
            "node_status": status,
            "errors": errors,
        }

    except Exception as exc:
        status["explanation"] = NodeStatus.FAILED

        errors.append(
            GraphError(
                node="explanation",
                code="EXPLANATION_FAILED",
                message=str(exc),
            )
        )

        return {
            **state,
            "node_status": status,
            "errors": errors,
        }
