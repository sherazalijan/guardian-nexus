import asyncio
from uuid import uuid4

from app.agents.graph import build_guardian_graph
from app.models.graph import NodeStatus


def test_graph_processes_transcript():
    graph = build_guardian_graph()

    state = {
        "session_id": uuid4(),
        "transcript": "The caller says I need to provide my OTP verification code.",
        "metadata": {},
        "node_status": {},
        "errors": [],
    }

    result = asyncio.run(graph.ainvoke(state))

    assert result["node_status"]["supervisor"] == NodeStatus.SUCCESS
    assert result["node_status"]["scam_detection"] == NodeStatus.SUCCESS

    assert result["llm_analysis"] is not None
    assert len(result["threat_signals"]) == 1
    assert result["threat_signals"][0].category.value == "scam"


def test_graph_handles_empty_transcript():
    graph = build_guardian_graph()

    state = {
        "session_id": uuid4(),
        "transcript": "",
        "metadata": {},
        "node_status": {},
        "errors": [],
    }

    result = asyncio.run(graph.ainvoke(state))

    assert result["node_status"]["supervisor"] == NodeStatus.SUCCESS
    assert result["node_status"]["scam_detection"] == NodeStatus.SKIPPED
    assert result["threat_signals"] == []
