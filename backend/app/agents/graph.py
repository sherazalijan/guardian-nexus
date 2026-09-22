"""Guardian Nexus LangGraph orchestration."""

from langgraph.graph import END, START, StateGraph

from app.agents.explanation_agent import explanation_agent
from app.agents.scam_detection_agent import scam_detection_agent
from app.agents.state import GuardianGraphState
from app.agents.supervisor import supervisor
from app.agents.threat_intelligence_agent import threat_intelligence_agent
from app.models.graph import NodeStatus
from app.services.risk_engine import run_risk_engine


def should_investigate(state: GuardianGraphState) -> str:
    """Route to threat intelligence only when candidate targets exist."""
    if state.get("candidate_targets"):
        return "threat_intelligence"

    return "risk_engine"


async def risk_engine_node(
    state: GuardianGraphState,
) -> GuardianGraphState:
    """Run the deterministic risk engine."""
    signals = list(state.get("threat_signals", []))

    result = run_risk_engine(signals)

    status = dict(state.get("node_status", {}))
    status["risk_engine"] = NodeStatus.SUCCESS

    return {
        **state,
        "risk_result": result,
        "node_status": status,
    }


def build_guardian_graph():
    """Build the complete Guardian Nexus analysis graph."""
    graph = StateGraph(GuardianGraphState)

    graph.add_node("supervisor", supervisor)
    graph.add_node("scam_detection", scam_detection_agent)
    graph.add_node(
        "threat_intelligence",
        threat_intelligence_agent,
    )
    graph.add_node("risk_engine", risk_engine_node)
    graph.add_node("explanation", explanation_agent)

    graph.add_edge(START, "supervisor")
    graph.add_edge("supervisor", "scam_detection")

    graph.add_conditional_edges(
        "scam_detection",
        should_investigate,
        {
            "threat_intelligence": "threat_intelligence",
            "risk_engine": "risk_engine",
        },
    )

    graph.add_edge("threat_intelligence", "risk_engine")
    graph.add_edge("risk_engine", "explanation")
    graph.add_edge("explanation", END)

    return graph.compile()