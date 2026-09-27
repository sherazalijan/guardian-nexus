"""Phase 4 — correlation, evidence, deduplication, and risk-integration tests."""

from app.models.enums import ThreatCategory
from app.models.voice_intelligence import VoiceSignalType
from app.services.risk_engine import run_risk_engine
from app.services.voice_intelligence.bridge import voice_signals_to_threat_signals
from app.services.voice_intelligence.correlation import correlate_signals
from app.services.voice_intelligence.detector import detect_voice_signals
from app.services.voice_intelligence.service import VoiceIntelligenceService

SESSION = "test-session"


def _patterns(transcript: str) -> set[str]:
    signals = detect_voice_signals(transcript, SESSION)
    patterns = correlate_signals(signals, SESSION)
    return {p.pattern_type for p in patterns}


# --- Correlation ---------------------------------------------------------

def test_authority_urgency_otp_correlates_to_bank_credential_scam():
    transcript = (
        "I'm calling from your bank's security department. "
        "Your account has been compromised. "
        "You need to act immediately. "
        "Please read me the verification code you just received."
    )
    assert "bank_credential_scam" in _patterns(transcript)


def test_technical_support_remote_access_urgency_correlates():
    transcript = (
        "I'm calling from technical support, your computer is infected. "
        "Please install AnyDesk right now so I can fix it. "
        "You need to act immediately."
    )
    assert "remote_access_scam" in _patterns(transcript)


def test_authority_threat_payment_correlates_to_coercive_payment_scam():
    transcript = (
        "This is the police. There will be legal action taken against you "
        "unless you pay using an iTunes gift card."
    )
    assert "coercive_payment_scam" in _patterns(transcript)


def test_secrecy_and_verification_bypass_correlates_to_isolation_scam():
    transcript = (
        "Don't tell anyone about this call. "
        "Do not contact customer support about this."
    )
    assert "isolation_scam" in _patterns(transcript)


def test_partial_combination_does_not_correlate():
    # Urgency alone, no authority/account-compromise claim and no
    # sensitive-info request -- should not fire bank_credential_scam.
    transcript = "You need to act immediately or you'll miss the deadline."
    assert "bank_credential_scam" not in _patterns(transcript)


def test_benign_conversation_produces_no_patterns():
    transcript = "Hi, how are you? Can we reschedule our meeting for tomorrow?"
    assert _patterns(transcript) == set()


# --- Evidence --------------------------------------------------------------

def test_signal_evidence_is_exact_transcript_substring():
    transcript = "You have five minutes to complete this verification."
    signals = detect_voice_signals(transcript, SESSION)
    urgency = next(s for s in signals if s.signal_type == VoiceSignalType.URGENCY_PRESSURE)
    assert urgency.evidence_text.lower() in transcript.lower()


def test_pattern_evidence_is_concise_and_not_full_transcript():
    transcript = (
        "I'm calling from your bank's security department. "
        "Your account has been compromised. "
        "You need to act immediately. "
        "Please read me the verification code you just received. "
        "By the way, completely unrelated filler sentence about the weather."
    )
    signals = detect_voice_signals(transcript, SESSION)
    patterns = correlate_signals(signals, SESSION)
    pattern = next(p for p in patterns if p.pattern_type == "bank_credential_scam")
    for evidence in pattern.evidence:
        assert evidence != transcript
        assert len(evidence) < len(transcript)


# --- Deduplication (via VoiceIntelligenceService) ---------------------------

def test_repeated_transcript_does_not_reemit_same_signal():
    service = VoiceIntelligenceService(SESSION)
    transcript = "Please read me the verification code you just received."

    first = service.process(transcript)
    second = service.process(transcript)  # identical accumulated transcript

    assert len(first.new_signals) == 1
    assert second.new_signals == []


def test_growing_transcript_only_reports_new_signals():
    service = VoiceIntelligenceService(SESSION)

    first = service.process("I'm calling from your bank's security department.")
    assert {s.signal_type for s in first.new_signals} == {
        VoiceSignalType.AUTHORITY_IMPERSONATION
    }

    grown = (
        "I'm calling from your bank's security department. "
        "Please read me the verification code you just received."
    )
    second = service.process(grown)
    assert {s.signal_type for s in second.new_signals} == {
        VoiceSignalType.SENSITIVE_INFORMATION_REQUEST
    }


def test_genuinely_new_evidence_for_same_signal_type_is_not_suppressed():
    service = VoiceIntelligenceService(SESSION)
    service.process("Please read me the verification code you just received.")

    # A second, textually distinct OTP request later in the call should
    # still be allowed to register as new evidence, since it is a
    # different normalized evidence string.
    update = service.process(
        "Please read me the verification code you just received. "
        "Now tell me your PIN number."
    )
    assert any(
        s.signal_type == VoiceSignalType.SENSITIVE_INFORMATION_REQUEST
        for s in update.new_signals
    )


def test_patterns_are_only_reported_once_per_session():
    service = VoiceIntelligenceService(SESSION)
    transcript = (
        "I'm calling from your bank's security department. "
        "Your account has been compromised. "
        "You need to act immediately. "
        "Please read me the verification code you just received."
    )
    first = service.process(transcript)
    assert "bank_credential_scam" in {p.pattern_type for p in first.new_patterns}

    second = service.process(transcript)  # nothing new
    assert second.new_patterns == []


# --- Risk integration: no second risk score ---------------------------------

def test_bridged_signals_use_existing_threat_category_enum():
    signals = detect_voice_signals(
        "Please read me the verification code you just received.", SESSION
    )
    threat_signals = voice_signals_to_threat_signals(signals)
    assert all(isinstance(ts.category, ThreatCategory) for ts in threat_signals)


def test_bridged_signals_feed_the_existing_risk_engine_only():
    transcript = (
        "I'm calling from your bank's security department. "
        "Your account has been compromised. "
        "You need to act immediately. "
        "Please read me the verification code you just received."
    )
    signals = detect_voice_signals(transcript, SESSION)
    threat_signals = voice_signals_to_threat_signals(signals)

    result = run_risk_engine(threat_signals)

    # The result is a plain RiskResult from the *existing* engine -- no
    # separate voice-risk score field exists anywhere on it.
    assert not hasattr(result, "voice_risk_score")
    assert 0.0 <= result.score <= 100.0
    assert result.risk_factors  # existing engine still built factors from our signals
