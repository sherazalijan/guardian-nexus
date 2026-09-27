"""Phase 4 — voice_intelligence_agent graph-node tests.

These exercise the node function directly (no full graph compile needed)
to keep the test fast and focused on the node's contract: it must never
remove existing threat_signals, must never raise, and must append
bridged signals additively.
"""

import asyncio

from app.agents.voice_intelligence_agent import voice_intelligence_agent
from app.models.enums import ThreatCategory
from app.models.threat import ThreatSignal
from datetime import datetime, timezone


def _run(state: dict) -> dict:
    return asyncio.run(voice_intelligence_agent(state))


def _existing_signal() -> ThreatSignal:
    return ThreatSignal(
        category=ThreatCategory.PHISHING,
        indicator="otp_request",
        evidence="give me the otp",
        confidence=0.85,
        source="rule-based-scam-agent",
        timestamp=datetime.now(timezone.utc),
    )


def test_appends_to_existing_threat_signals_without_removing_them():
    existing = _existing_signal()
    state = {
        "session_id": "s1",
        "transcript": "I'm calling from your bank's security department.",
        "threat_signals": [existing],
    }
    result = _run(state)

    assert existing in result["threat_signals"]
    assert len(result["threat_signals"]) > 1


def test_populates_voice_signals_and_patterns_keys():
    state = {
        "session_id": "s1",
        "transcript": (
            "I'm calling from your bank's security department. "
            "Your account has been compromised. "
            "You need to act immediately. "
            "Please read me the verification code you just received."
        ),
        "threat_signals": [],
    }
    result = _run(state)

    assert len(result["voice_signals"]) > 0
    assert any(p.pattern_type == "bank_credential_scam" for p in result["voice_patterns"])


def test_empty_transcript_is_a_no_op():
    state = {"session_id": "s1", "transcript": "", "threat_signals": [_existing_signal()]}
    result = _run(state)

    assert result["voice_signals"] == []
    assert result["voice_patterns"] == []
    assert len(result["threat_signals"]) == 1


def test_missing_session_id_does_not_raise():
    state = {"transcript": "Please read me the verification code.", "threat_signals": []}
    result = _run(state)  # should not raise
    assert isinstance(result["voice_signals"], list)


def test_missing_threat_signals_key_does_not_raise():
    state = {"session_id": "s1", "transcript": "hello there"}
    result = _run(state)
    assert result["threat_signals"] == []
