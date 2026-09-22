import asyncio
from uuid import uuid4

from app.agents.threat_intelligence_agent import (
    threat_intelligence_agent,
)
from app.models.graph import CandidateTarget, NodeStatus


def test_threat_intelligence_agent_finds_mock_indicator():
    state = {
        "session_id": uuid4(),
        "transcript": "Visit example-phishing.com",
        "metadata": {},
        "candidate_targets": [
            CandidateTarget(
                target_type="phishing",
                value="example-phishing.com",
                source="test",
            )
        ],
        "node_status": {},
        "errors": [],
    }

    result = asyncio.run(threat_intelligence_agent(state))

    assert (
        result["node_status"]["threat_intelligence"]
        == NodeStatus.SUCCESS
    )

    intelligence = result["threat_intelligence"]

    assert intelligence is not None
    assert intelligence.provider == "mock-threat-intelligence"
    assert len(intelligence.findings) == 1
    assert intelligence.findings[0].category == "phishing"


def test_threat_intelligence_agent_skips_without_targets():
    state = {
        "session_id": uuid4(),
        "transcript": "Hello",
        "metadata": {},
        "candidate_targets": [],
        "node_status": {},
        "errors": [],
    }

    result = asyncio.run(threat_intelligence_agent(state))

    assert (
        result["node_status"]["threat_intelligence"]
        == NodeStatus.SKIPPED
    )
    assert result["threat_intelligence"] is None
    assert result["errors"] == []
