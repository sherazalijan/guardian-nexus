"""Phase 5 — Intervention Engine rule tests."""

from app.models.voice_intelligence import VoiceSignal, VoiceSignalType
from app.models.enums import ThreatCategory, ThreatSeverity
from app.services.intervention_engine.engine import build_event, decide

SESSION = "test-session"


def _signal(signal_type: VoiceSignalType, confidence: float = 0.9) -> VoiceSignal:
    return VoiceSignal(
        session_id=SESSION,
        signal_type=signal_type,
        category=ThreatCategory.FRAUD,
        confidence=confidence,
        severity=ThreatSeverity.HIGH,
        evidence_text="evidence",
        source="test",
    )


def test_low_risk_is_ignored():
    decision = decide(risk_score=20, confidence=0.6, voice_signals=[], voice_patterns=[])
    assert decision.should_intervene is False
    assert build_event(decision, risk_score=20, voice_signals=[]) is None


def test_otp_detected_with_moderate_risk_triggers_warning():
    signals = [_signal(VoiceSignalType.SENSITIVE_INFORMATION_REQUEST)]
    decision = decide(risk_score=55, confidence=0.85, voice_signals=signals, voice_patterns=[])
    assert decision.should_intervene is True
    assert decision.level.value == "warning"

    event = build_event(decision, risk_score=55, voice_signals=signals)
    assert event is not None
    assert "verification codes" in event.message.lower() or "otp" in event.title.lower() or "OTP" in event.title


def test_bank_impersonation_with_high_risk_triggers_high_risk():
    signals = [_signal(VoiceSignalType.AUTHORITY_IMPERSONATION)]
    decision = decide(risk_score=75, confidence=0.9, voice_signals=signals, voice_patterns=[])
    assert decision.level.value == "high_risk"

    event = build_event(decision, risk_score=75, voice_signals=signals)
    assert "bank" in event.title.lower()


def test_crypto_scam_triggers_high_risk():
    signals = [_signal(VoiceSignalType.CRYPTO_REQUEST)]
    decision = decide(risk_score=72, confidence=0.9, voice_signals=signals, voice_patterns=[])
    assert decision.level.value == "high_risk"
    event = build_event(decision, risk_score=72, voice_signals=signals)
    assert "crypto" in event.title.lower() or "crypto" in event.message.lower()


def test_gift_card_scam_triggers_high_risk():
    signals = [_signal(VoiceSignalType.GIFT_CARD_REQUEST)]
    decision = decide(risk_score=71, confidence=0.9, voice_signals=signals, voice_patterns=[])
    assert decision.level.value == "high_risk"
    event = build_event(decision, risk_score=71, voice_signals=signals)
    assert "gift card" in event.message.lower()


def test_remote_access_scam_triggers_high_risk_below_critical_threshold():
    signals = [_signal(VoiceSignalType.REMOTE_ACCESS_REQUEST)]
    decision = decide(risk_score=72, confidence=0.9, voice_signals=signals, voice_patterns=[])
    assert decision.level.value == "high_risk"


def test_remote_access_scam_escalates_to_critical_at_high_risk_score():
    signals = [_signal(VoiceSignalType.REMOTE_ACCESS_REQUEST)]
    decision = decide(risk_score=90, confidence=0.95, voice_signals=signals, voice_patterns=[])
    assert decision.level.value == "critical"
    event = build_event(decision, risk_score=90, voice_signals=signals)
    assert "remote access" in event.message.lower()


def test_multiple_scam_indicators_with_very_high_risk_triggers_critical():
    signals = [
        _signal(VoiceSignalType.AUTHORITY_IMPERSONATION),
        _signal(VoiceSignalType.URGENCY_PRESSURE),
        _signal(VoiceSignalType.SENSITIVE_INFORMATION_REQUEST),
    ]
    decision = decide(risk_score=88, confidence=0.95, voice_signals=signals, voice_patterns=[])
    assert decision.level.value == "critical"


def test_repeated_pressure_tactics_with_urgency_triggers_critical():
    signals = [
        _signal(VoiceSignalType.URGENCY_PRESSURE),
        _signal(VoiceSignalType.URGENCY_PRESSURE),
    ]
    decision = decide(risk_score=60, confidence=0.9, voice_signals=signals, voice_patterns=[])
    assert decision.level.value == "critical"


def test_critical_rules_take_priority_over_lower_severity_matches():
    # This combination satisfies both "multiple_indicators_critical" and
    # "bank_impersonation_high" -- critical must win.
    signals = [
        _signal(VoiceSignalType.AUTHORITY_IMPERSONATION),
        _signal(VoiceSignalType.URGENCY_PRESSURE),
        _signal(VoiceSignalType.SENSITIVE_INFORMATION_REQUEST),
    ]
    decision = decide(risk_score=90, confidence=0.95, voice_signals=signals, voice_patterns=[])
    assert decision.level.value == "critical"
    assert decision.reason == "multiple_indicators_critical"


def test_event_carries_risk_score_and_confidence_through():
    signals = [_signal(VoiceSignalType.SENSITIVE_INFORMATION_REQUEST)]
    decision = decide(risk_score=55.5, confidence=0.77, voice_signals=signals, voice_patterns=[])
    event = build_event(decision, risk_score=55.5, voice_signals=signals)
    assert event.risk_score == 55.5
    assert event.confidence == 0.77


def test_no_intervene_decision_produces_no_event():
    decision = decide(risk_score=10, confidence=0.5, voice_signals=[], voice_patterns=[])
    assert build_event(decision, risk_score=10, voice_signals=[]) is None
