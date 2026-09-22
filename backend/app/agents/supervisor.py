from app.agents.state import GuardianGraphState
from app.models.graph import NodeStatus


async def supervisor(state: GuardianGraphState) -> GuardianGraphState:
    status = dict(state.get("node_status", {}))

    status["supervisor"] = NodeStatus.SUCCESS

    return {
        **state,
        "node_status": status,
    }
