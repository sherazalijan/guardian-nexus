import asyncio

from app.agents.scam_agent import scam_agent


def _run(transcript: str) -> dict:
    return asyncio.run(scam_agent({"transcript": transcript}))


def test_scam_agent_detects_otp_request():
    result = _run(
        "Please give me the OTP that was just sent to your phone so I can verify your identity."
    )

    assert result["category"] == "phishing"
    assert result["scam_score"] > 0
    assert len(result["threat_signals"]) == 1
    assert result["threat_signals"][0].category.value == "phishing"
    assert "otp" in result["explanation"].lower()


def test_scam_agent_detects_bank_impersonation():
    result = _run(
        "This is your bank's fraud department calling about suspicious activity on your account."
    )

    assert result["category"] == "impersonation"
    assert result["scam_score"] > 0
    assert len(result["threat_signals"]) == 1
    assert result["threat_signals"][0].category.value == "impersonation"


def test_scam_agent_detects_crypto_scam():
    result = _run(
        "You need to transfer the funds using your crypto wallet to avoid losing your account."
    )

    assert result["category"] == "fraud"
    assert result["scam_score"] > 0
    assert any(
        signal.indicator == "crypto_transfer_request"
        for signal in result["threat_signals"]
    )


def test_scam_agent_detects_gift_card_scam():
    result = _run(
        "I need you to go buy a Google Play gift card and read me the codes right now."
    )

    assert result["category"] == "fraud"
    assert result["scam_score"] > 0
    assert any(
        signal.indicator == "gift_card_request" for signal in result["threat_signals"]
    )


def test_scam_agent_detects_remote_access_request():
    result = _run(
        "I'm going to need you to install AnyDesk so I can take control of your computer."
    )

    assert result["category"] == "malware"
    assert result["scam_score"] > 0
    assert any(
        signal.indicator == "remote_access_request"
        for signal in result["threat_signals"]
    )


def test_scam_agent_detects_account_suspension_threat():
    result = _run("Your account has been suspended due to unusual activity.")

    assert result["category"] == "suspicious_call"
    assert result["scam_score"] > 0
    assert any(
        signal.indicator == "account_suspension_threat"
        for signal in result["threat_signals"]
    )


def test_scam_agent_multiple_indicators_increase_score_and_signal_count():
    result = _run(
        "This is your bank's security department. Your account has been compromised "
        "— tell me your OTP immediately."
    )

    # otp_request + bank_impersonation + account_suspension_threat all match.
    assert len(result["threat_signals"]) == 3
    assert result["scam_score"] > 50
    assert "otp" in result["explanation"].lower()
    assert "bank" in result["explanation"].lower()


def test_scam_agent_benign_conversation_is_clean():
    result = _run(
        "Hey, are we still on for coffee tomorrow morning? I was thinking around 10am."
    )

    assert result["scam_score"] == 0
    assert result["category"] == "unknown"
    assert result["threat_signals"] == []
    assert result["explanation"] == "No scam indicators detected."


def test_scam_agent_empty_transcript_is_handled_safely():
    result = _run("")

    assert result["scam_score"] == 0
    assert result["category"] == "unknown"
    assert result["threat_signals"] == []
    assert result["explanation"] == "Empty transcript; no scam indicators to evaluate."


def test_scam_agent_whitespace_only_transcript_is_treated_as_empty():
    result = _run("    \n\t  ")

    assert result["scam_score"] == 0
    assert result["threat_signals"] == []


def test_scam_agent_missing_transcript_key_is_handled_safely():
    result = asyncio.run(scam_agent({}))

    assert result["scam_score"] == 0
    assert result["category"] == "unknown"
    assert result["threat_signals"] == []
