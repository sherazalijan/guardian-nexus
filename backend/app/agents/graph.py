"""Guardian Nexus LangGraph orchestration.

This module defines two independent graphs:

- `build_guardian_graph()` -- the advanced pipeline (supervisor ->
  LLM-backed scam detection -> optional Tavily threat intelligence ->
  risk engine -> LLM-backed explanation). Requires `LLM_PROVIDER`/
  `TAVILY_API_KEY` configuration for full functionality.
- `build_rule_based_guardian_graph()` -- the offline pipeline (rule-based
  scam agent -> risk engine). Fully deterministic, no external API keys
  or network access required. See `app.agents.scam_agent` and
  `app.agents.rule_based_state`.

Both pipelines reuse the same deterministic risk engine
(`app.services.risk_engine.run_risk_engine`); only the scam-detection
step differs between them.
"""

from langgraph.graph import END, START, StateGraph

from app.agents.explanation_agent import explanation_agent
from app.agents.rule_based_state import GuardianState
from app.agents.scam_agent import scam_agent
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


# ---------------------------------------------------------------------
# Offline pipeline: START -> scam_agent -> risk_engine -> END
#
# No LLM, no Tavily, no API keys, no network access. Reuses the exact
# same deterministic risk engine as the advanced pipeline above.
# ---------------------------------------------------------------------


async def rule_based_risk_engine_node(state: GuardianState) -> GuardianState:
    """Run the existing deterministic risk engine against rule-based signals.

    This calls `run_risk_engine` unmodified -- the same function the
    advanced pipeline's `risk_engine_node` above calls -- so scoring
    logic is never duplicated between the two pipelines.
    """
    signals = list(state.get("threat_signals", []))

    result = run_risk_engine(signals)

    return {
        **state,
        "risk_level": result.severity.value,
        "risk_result": result,
    }


def build_rule_based_guardian_graph():
    """Build Guardian Nexus's offline, no-API-key analysis graph.

    Flow: START -> scam_agent -> risk_engine -> END

    Every node here is deterministic and requires no external API key or
    network access, unlike `build_guardian_graph()`. It reuses the same
    risk engine as the advanced pipeline -- only the scam-detection step
    differs.
    """
    graph = StateGraph(GuardianState)

    graph.add_node("scam_agent", scam_agent)
    graph.add_node("risk_engine", rule_based_risk_engine_node)

    graph.add_edge(START, "scam_agent")
    graph.add_edge("scam_agent", "risk_engine")
    graph.add_edge("risk_engine", END)

    return graph.compile()