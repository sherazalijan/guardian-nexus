from datetime import datetime, timezone

from app.models.enums import RecommendedAction, ThreatCategory
from app.models.protection import SecurityCategory
from app.models.threat import ThreatSignal
from app.services.protection.rules import (
    classify_signal,
    message_for,
    recommended_action_for,
    risk_action_text,
    title_for,
)

NOW = datetime.now(timezone.utc)


def _signal(indicator: str, category: ThreatCategory) -> ThreatSignal:
    return ThreatSignal(
        category=category,
        indicator=indicator,
        evidence="evidence text",
        confidence=0.8,
        source="rule-based-scam-agent",
        timestamp=NOW,
    )


def test_classify_signal_otp_request():
    signal = _signal("otp_request", ThreatCategory.PHISHING)
    assert classify_signal(signal) == SecurityCategory.OTP_THEFT


def test_classify_signal_bank_impersonation():
    signal = _signal("bank_impersonation", ThreatCategory.IMPERSONATION)
    assert classify_signal(signal) == SecurityCategory.BANK_IMPERSONATION


def test_classify_signal_remote_access():
    signal = _signal("remote_access_request", ThreatCategory.MALWARE)
    assert classify_signal(signal) == SecurityCategory.REMOTE_ACCESS_SCAM


def test_classify_signal_gift_card():
    signal = _signal("gift_card_request", ThreatCategory.FRAUD)
    assert classify_signal(signal) == SecurityCategory.GIFT_CARD_SCAM


def test_classify_signal_crypto():
    signal = _signal("crypto_transfer_request", ThreatCategory.FRAUD)
    assert classify_signal(signal) == SecurityCategory.CRYPTOCURRENCY_SCAM


def test_classify_signal_account_compromise():
    signal = _signal("account_suspension_threat", ThreatCategory.SUSPICIOUS_CALL)
    assert classify_signal(signal) == SecurityCategory.ACCOUNT_COMPROMISE


def test_classify_signal_urgent_payment():
    signal = _signal("urgent_payment_request", ThreatCategory.FRAUD)
    assert classify_signal(signal) == SecurityCategory.URGENT_PAYMENT


def test_classify_signal_unrecognized_indicator_falls_back_to_threat_category():
    signal = _signal("some_new_llm_indicator", ThreatCategory.PHISHING)
    assert classify_signal(signal) == SecurityCategory.PHISHING


def test_classify_signal_unknown_category_falls_back_to_unknown():
    signal = _signal("totally_unmapped", ThreatCategory.UNKNOWN)
    assert classify_signal(signal) == SecurityCategory.UNKNOWN


def test_classify_signal_indicator_match_is_case_and_space_insensitive():
    signal = _signal("OTP Request", ThreatCategory.PHISHING)
    assert classify_signal(signal) == SecurityCategory.OTP_THEFT


def test_every_security_category_has_deterministic_copy():
    for category in SecurityCategory:
        assert title_for(category)
        assert message_for(category)
        assert recommended_action_for(category)


def test_recommended_actions_match_spec_examples():
    assert "Do not share your OTP" in recommended_action_for(SecurityCategory.OTP_THEFT)
    assert "official channel" in recommended_action_for(SecurityCategory.BANK_IMPERSONATION)
    assert "remote-access software" in recommended_action_for(
        SecurityCategory.REMOTE_ACCESS_SCAM
    )
    assert "gift cards" in recommended_action_for(SecurityCategory.GIFT_CARD_SCAM)
    assert "cryptocurrency" in recommended_action_for(SecurityCategory.CRYPTOCURRENCY_SCAM)
    assert "Verify independently" in recommended_action_for(
        SecurityCategory.ACCOUNT_COMPROMISE
    )


def test_recommended_actions_are_deterministic_across_calls():
    for category in SecurityCategory:
        assert recommended_action_for(category) == recommended_action_for(category)


def test_risk_action_text_covers_every_recommended_action():
    for action in RecommendedAction:
        assert risk_action_text(action)
