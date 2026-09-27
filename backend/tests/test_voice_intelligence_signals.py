"""Phase 4 — signal detection tests."""

from app.models.voice_intelligence import VoiceSignalType
from app.services.voice_intelligence.detector import detect_voice_signals

SESSION = "test-session"


def _types(transcript: str) -> set[VoiceSignalType]:
    return {s.signal_type for s in detect_voice_signals(transcript, SESSION)}


# --- Authority ---------------------------------------------------------

def test_detects_bank_impersonation():
    assert VoiceSignalType.AUTHORITY_IMPERSONATION in _types(
        "Hi, I'm calling from your bank's security department."
    )


def test_detects_police_impersonation():
    assert VoiceSignalType.AUTHORITY_IMPERSONATION in _types(
        "This is the police, we need to speak with you."
    )


def test_detects_technical_support_impersonation():
    assert VoiceSignalType.TECHNICAL_SUPPORT_IMPERSONATION in _types(
        "I'm calling from technical support, your computer is infected."
    )


# --- Urgency -------------------------------------------------------------

def test_detects_immediate_action_urgency():
    assert VoiceSignalType.URGENCY_PRESSURE in _types(
        "You need to act immediately or lose access."
    )


def test_detects_deadline_pressure():
    assert VoiceSignalType.URGENCY_PRESSURE in _types(
        "You only have five minutes to complete this verification."
    )


def test_detects_account_closure_pressure():
    assert VoiceSignalType.URGENCY_PRESSURE in _types(
        "Your account will be closed if you don't respond now."
    )


# --- Threats ---------------------------------------------------------------

def test_detects_legal_threat():
    assert VoiceSignalType.THREAT_INTIMIDATION in _types(
        "There will be legal action taken against you."
    )


def test_detects_account_suspension_threat():
    assert VoiceSignalType.THREAT_INTIMIDATION in _types(
        "Failure to comply results in financial penalties."
    )


# --- Sensitive information --------------------------------------------------

def test_detects_otp_request():
    assert VoiceSignalType.SENSITIVE_INFORMATION_REQUEST in _types(
        "Please read me the verification code you just received."
    )


def test_detects_pin_request():
    assert VoiceSignalType.SENSITIVE_INFORMATION_REQUEST in _types(
        "I need your PIN number to verify your identity."
    )


def test_detects_password_request():
    assert VoiceSignalType.SENSITIVE_INFORMATION_REQUEST in _types(
        "Can you confirm your password for verification?"
    )


def test_detects_banking_credential_request():
    assert VoiceSignalType.SENSITIVE_INFORMATION_REQUEST in _types(
        "I'll need your bank account credentials to proceed."
    )


# --- Payments ----------------------------------------------------------------

def test_detects_gift_card_payment():
    assert VoiceSignalType.GIFT_CARD_REQUEST in _types(
        "You'll need to pay using an iTunes gift card."
    )


def test_detects_crypto_payment():
    assert VoiceSignalType.CRYPTO_REQUEST in _types(
        "Please send the payment in Bitcoin."
    )


def test_detects_generic_payment_request():
    assert VoiceSignalType.PAYMENT_REQUEST in _types(
        "We'll process this as a wire transfer."
    )


# --- Remote access -------------------------------------------------------------

def test_detects_remote_desktop_request():
    assert VoiceSignalType.REMOTE_ACCESS_REQUEST in _types(
        "Please install AnyDesk so I can access your computer."
    )


def test_detects_screen_share_request():
    assert VoiceSignalType.REMOTE_ACCESS_REQUEST in _types(
        "Can you share your screen with me right now?"
    )


# --- Secrecy -----------------------------------------------------------------

def test_detects_dont_tell_anyone():
    assert VoiceSignalType.SECRECY_ISOLATION in _types(
        "Don't tell anyone about this call."
    )


def test_detects_stay_on_the_line():
    assert VoiceSignalType.SECRECY_ISOLATION in _types(
        "Please stay on the line while I transfer you."
    )


def test_detects_dont_contact_bank():
    assert VoiceSignalType.SECRECY_ISOLATION in _types(
        "Do not talk to your family about this yet."
    )


# --- Verification bypass ------------------------------------------------------

def test_detects_use_this_number_instead():
    assert VoiceSignalType.VERIFICATION_BYPASS in _types(
        "Don't call the official number, use this number instead."
    )


def test_detects_dont_contact_support():
    assert VoiceSignalType.VERIFICATION_BYPASS in _types(
        "Please do not contact customer support about this."
    )


# --- Benign / false-positive resistance ---------------------------------------

def test_benign_greeting_produces_no_signals():
    assert _types("Hi, how are you? Can we reschedule our meeting?") == set()


def test_benign_delivery_notice_produces_no_signals():
    assert _types("Your package will arrive tomorrow morning.") == set()


def test_ordinary_words_without_scam_context_are_not_flagged():
    # "code", "bank", "account", "payment", "security" appear, but not in
    # a scam-indicating construction.
    transcript = (
        "I updated the security settings on my account and set up "
        "autopay for my bank so the payment goes out on time."
    )
    assert _types(transcript) == set()


# --- Malformed input -----------------------------------------------------------

def test_empty_transcript_produces_no_signals():
    assert detect_voice_signals("", SESSION) == []


def test_whitespace_only_transcript_produces_no_signals():
    assert detect_voice_signals("   \n\t  ", SESSION) == []


def test_none_like_transcript_does_not_raise():
    # detect_voice_signals guards against a falsy/None transcript.
    assert detect_voice_signals(None, SESSION) == []  # type: ignore[arg-type]
