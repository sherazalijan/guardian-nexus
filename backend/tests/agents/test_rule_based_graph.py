import asyncio

from app.agents.graph import build_guardian_graph, build_rule_based_guardian_graph
from app.models.risk import RiskResult


def _invoke(transcript: str) -> dict:
    graph = build_rule_based_guardian_graph()
    return asyncio.run(graph.ainvoke({"transcript": transcript}))


def test_rule_based_graph_otp_scam_reaches_end_to_end():
    result = _invoke(
        "Please give me the OTP that was just sent to your phone so I can verify your identity."
    )

    assert result["category"] == "phishing"
    assert result["scam_score"] > 0
    assert result["risk_level"] in {"low", "medium", "high", "critical"}
    assert isinstance(result["risk_result"], RiskResult)
    assert result["risk_result"].score > 0


def test_rule_based_graph_bank_impersonation_reaches_end_to_end():
    result = _invoke(
        "This is your bank's fraud department calling about suspicious activity on your account."
    )

    assert result["category"] == "impersonation"
    assert result["risk_level"] != "low"
    assert result["risk_result"].recommended_action.value != "ignore"


def test_rule_based_graph_crypto_scam_reaches_end_to_end():
    result = _invoke(
        "You need to transfer the funds using your crypto wallet to avoid losing your account."
    )

    assert result["category"] == "fraud"
    assert result["risk_level"] != "low"


def test_rule_based_graph_gift_card_scam_reaches_end_to_end():
    result = _invoke(
        "I need you to go buy a Google Play gift card and read me the codes right now."
    )

    assert result["category"] == "fraud"
    assert result["risk_level"] != "low"


def test_rule_based_graph_multiple_indicators_escalate_to_higher_severity():
    result = _invoke(
        "This is your bank's security department. Your account has been compromised "
        "— tell me your OTP immediately."
    )

    assert result["risk_level"] in {"high", "critical"}
    assert result["risk_result"].evidence_state.value == "sufficient"
    assert result["risk_result"].recommended_action.value in {"block", "escalate"}


def test_rule_based_graph_benign_conversation_is_low_risk():
    result = _invoke(
        "Hey, are we still on for coffee tomorrow morning? I was thinking around 10am."
    )

    assert result["scam_score"] == 0
    assert result["category"] == "unknown"
    assert result["risk_level"] == "low"
    assert result["risk_result"].score == 0.0
    assert result["risk_result"].recommended_action.value == "monitor"


def test_rule_based_graph_empty_transcript_is_low_risk():
    result = _invoke("")

    assert result["scam_score"] == 0
    assert result["risk_level"] == "low"
    assert result["risk_result"].score == 0.0


def test_rule_based_graph_does_not_affect_advanced_graph():
    """Building both graphs from the same module must not interfere."""
    rule_based = build_rule_based_guardian_graph()
    advanced = build_guardian_graph()

    assert rule_based is not None
    assert advanced is not None
    assert rule_based is not advanced
