"""Phase 2 tests: Session Intelligence (evidence, risk history, timeline,
session summary). These exercise `SessionIntelligenceService` together
with the real, existing `ProtectionService` -- nothing here mocks or
duplicates Phase 1.
"""

from datetime import datetime, timezone

from app.models.enums import EvidenceState, RecommendedAction, ThreatCategory, ThreatSeverity
from app.models.protection import ProtectionState, SecurityCategory
from app.models.risk import RiskResult
from app.models.session_intelligence import IncidentEventType, RiskHistoryTrigger
from app.models.threat import ThreatSignal
from app.services.protection.service import ProtectionService
from app.services.session_intelligence import SessionIntelligenceService


def make_signal(indicator, evidence, category=ThreatCategory.SCAM, confidence=0.9):
    return ThreatSignal(
        category=category,
        indicator=indicator,
        evidence=evidence,
        confidence=confidence,
        source="rule_based",
        timestamp=datetime.now(timezone.utc),
    )


def make_risk(score, severity, action=RecommendedAction.MONITOR, confidence=0.8):
    return RiskResult(
        score=score,
        severity=severity,
        confidence=confidence,
        evidence_state=EvidenceState.SUFFICIENT,
        risk_factors=[],
        explanation="test",
        recommended_action=action,
    )


def run_pass(protection, intelligence, signals, risk):
    analysis = protection.process(threat_signals=signals, risk_result=risk)
    update = intelligence.process(
        threat_signals=signals, risk_result=risk, protection_result=analysis
    )
    return analysis, update


# ---------------------------------------------------------------- evidence


def test_otp_evidence_extracted_and_classified():
    protection = ProtectionService("s1")
    intelligence = SessionIntelligenceService("s1")
    signal = make_signal("otp_request", "Tell me the OTP you just received.")
    _, update = run_pass(protection, intelligence, [signal], make_risk(60, ThreatSeverity.HIGH))

    assert len(update.evidence) == 1
    item = update.evidence[0]
    assert item.category == SecurityCategory.OTP_THEFT
    assert item.signal == "otp_request"
    assert item.text == "Tell me the OTP you just received."


def test_bank_impersonation_and_remote_access_and_gift_card_and_crypto_and_account_compromise():
    protection = ProtectionService("s2")
    intelligence = SessionIntelligenceService("s2")
    signals = [
        make_signal("bank_impersonation", "I'm calling from your bank."),
        make_signal("remote_access_request", "Install AnyDesk and give me remote access."),
        make_signal("gift_card_request", "You must buy gift cards immediately."),
        make_signal("crypto_transfer_request", "Transfer bitcoin to this wallet."),
        make_signal("account_suspension_threat", "Your account has been compromised."),
    ]
    _, update = run_pass(protection, intelligence, signals, make_risk(80, ThreatSeverity.CRITICAL))

    categories = {item.category for item in update.evidence}
    assert categories == {
        SecurityCategory.BANK_IMPERSONATION,
        SecurityCategory.REMOTE_ACCESS_SCAM,
        SecurityCategory.GIFT_CARD_SCAM,
        SecurityCategory.CRYPTOCURRENCY_SCAM,
        SecurityCategory.ACCOUNT_COMPROMISE,
    }


def test_benign_transcript_produces_no_evidence():
    protection = ProtectionService("s3")
    intelligence = SessionIntelligenceService("s3")
    _, update = run_pass(protection, intelligence, [], make_risk(0, ThreatSeverity.LOW, RecommendedAction.IGNORE))
    assert update.evidence == []


def test_empty_and_malformed_style_inputs_do_not_crash():
    protection = ProtectionService("s4")
    intelligence = SessionIntelligenceService("s4")
    _, update = run_pass(protection, intelligence, [], make_risk(0, ThreatSeverity.LOW, RecommendedAction.IGNORE))
    assert update.evidence == []
    assert update.timeline_events == []
    snapshot = intelligence.snapshot()
    assert snapshot.evidence == []


def test_evidence_deduplication_same_text_collapses_but_distinct_text_kept():
    protection = ProtectionService("s5")
    intelligence = SessionIntelligenceService("s5")

    otp_signal = make_signal("otp_request", "Tell me the OTP you just received.")
    for _ in range(4):
        run_pass(protection, intelligence, [otp_signal], make_risk(60, ThreatSeverity.HIGH))
    assert len(intelligence.snapshot().evidence) == 1

    pin_signal = make_signal("otp_request", "Tell me your PIN.")
    run_pass(protection, intelligence, [pin_signal], make_risk(60, ThreatSeverity.HIGH))
    assert len(intelligence.snapshot().evidence) == 2
    texts = {item.text for item in intelligence.snapshot().evidence}
    assert texts == {"Tell me the OTP you just received.", "Tell me your PIN."}


# ------------------------------------------------------------ risk history


def test_risk_history_initial_increase_decrease_duplicate_and_transitions():
    protection = ProtectionService("s6")
    intelligence = SessionIntelligenceService("s6")

    run_pass(protection, intelligence, [], make_risk(0, ThreatSeverity.LOW, RecommendedAction.IGNORE))
    history = intelligence.snapshot().risk_history
    assert len(history) == 1
    assert history[0].trigger == RiskHistoryTrigger.INITIAL

    run_pass(protection, intelligence, [], make_risk(0, ThreatSeverity.LOW, RecommendedAction.IGNORE))
    assert len(intelligence.snapshot().risk_history) == 1

    run_pass(protection, intelligence, [], make_risk(20, ThreatSeverity.LOW, RecommendedAction.MONITOR))
    history = intelligence.snapshot().risk_history
    assert len(history) == 2
    assert history[-1].trigger == RiskHistoryTrigger.RISK_INCREASE

    run_pass(protection, intelligence, [], make_risk(55, ThreatSeverity.MEDIUM, RecommendedAction.WARN))
    history = intelligence.snapshot().risk_history
    assert history[-1].trigger == RiskHistoryTrigger.SEVERITY_CHANGE

    run_pass(protection, intelligence, [], make_risk(92, ThreatSeverity.CRITICAL, RecommendedAction.ESCALATE))
    history = intelligence.snapshot().risk_history
    assert history[-1].trigger == RiskHistoryTrigger.CRITICAL_ESCALATION

    run_pass(protection, intelligence, [], make_risk(70, ThreatSeverity.CRITICAL, RecommendedAction.ESCALATE))
    history = intelligence.snapshot().risk_history
    assert history[-1].trigger == RiskHistoryTrigger.RISK_DECREASE


def test_risk_history_sample_progression_matches_spec_example():
    protection = ProtectionService("s7")
    intelligence = SessionIntelligenceService("s7")
    scores = [
        (0, ThreatSeverity.LOW, RecommendedAction.IGNORE),
        (20, ThreatSeverity.LOW, RecommendedAction.MONITOR),
        (25, ThreatSeverity.LOW, RecommendedAction.MONITOR),
        (52, ThreatSeverity.MEDIUM, RecommendedAction.WARN),
        (78, ThreatSeverity.HIGH, RecommendedAction.BLOCK),
        (92, ThreatSeverity.CRITICAL, RecommendedAction.ESCALATE),
    ]
    for score, severity, action in scores:
        run_pass(protection, intelligence, [], make_risk(score, severity, action))

    history = intelligence.snapshot().risk_history
    assert [e.new_score for e in history] == [0, 20, 25, 52, 78, 92]


# ---------------------------------------------------------------- timeline


def test_timeline_ordering_and_no_double_counted_escalations():
    protection = ProtectionService("s8")
    intelligence = SessionIntelligenceService("s8")

    otp_signal = make_signal("otp_request", "Tell me the OTP you just received.")
    run_pass(protection, intelligence, [otp_signal], make_risk(20, ThreatSeverity.LOW, RecommendedAction.MONITOR))
    run_pass(protection, intelligence, [otp_signal], make_risk(78, ThreatSeverity.HIGH, RecommendedAction.BLOCK))

    timeline = intelligence.snapshot().timeline
    event_types = [e.event_type for e in timeline]

    assert event_types[0] == IncidentEventType.SESSION_STARTED
    timestamps = [e.timestamp for e in timeline]
    assert timestamps == sorted(timestamps)

    warning_count = sum(1 for t in event_types if t == IncidentEventType.WARNING)
    risk_escalated_count = sum(1 for t in event_types if t == IncidentEventType.RISK_ESCALATED)
    assert warning_count == 1
    assert risk_escalated_count == 0


def test_timeline_includes_evidence_threat_and_critical_alert_events():
    protection = ProtectionService("s9")
    intelligence = SessionIntelligenceService("s9")
    signal = make_signal("bank_impersonation", "I'm calling from your bank.")

    run_pass(protection, intelligence, [signal], make_risk(20, ThreatSeverity.LOW, RecommendedAction.MONITOR))
    run_pass(protection, intelligence, [signal], make_risk(92, ThreatSeverity.CRITICAL, RecommendedAction.ESCALATE))

    event_types = {e.event_type for e in intelligence.snapshot().timeline}
    assert IncidentEventType.EVIDENCE_DETECTED in event_types
    assert IncidentEventType.THREAT_DETECTED in event_types
    assert IncidentEventType.CRITICAL_ALERT in event_types


# --------------------------------------------------------- session summary


def test_session_summary_benign():
    protection = ProtectionService("s10")
    intelligence = SessionIntelligenceService("s10")
    run_pass(protection, intelligence, [], make_risk(0, ThreatSeverity.LOW, RecommendedAction.IGNORE))
    protection.end_session()
    summary = intelligence.build_summary(protection.build_session_summary())

    assert summary.evidence_count == 0
    assert summary.warning_count == 0
    assert summary.critical_alert_count == 0
    assert summary.primary_category == SecurityCategory.UNKNOWN
    assert summary.final_state == ProtectionState.MONITORING


def test_session_summary_multiple_threats_and_critical():
    protection = ProtectionService("s11")
    intelligence = SessionIntelligenceService("s11")
    otp = make_signal("otp_request", "Tell me the OTP you just received.")
    urgent = make_signal("urgent_payment_request", "You must transfer the money immediately.")

    run_pass(protection, intelligence, [otp], make_risk(30, ThreatSeverity.LOW, RecommendedAction.MONITOR))
    run_pass(protection, intelligence, [otp, urgent], make_risk(92, ThreatSeverity.CRITICAL, RecommendedAction.ESCALATE))
    protection.end_session()

    summary = intelligence.build_summary(protection.build_session_summary())
    assert summary.evidence_count == 2
    assert summary.critical_alert_count == 1
    assert summary.highest_severity == ThreatSeverity.CRITICAL
    assert summary.risk_escalation_count >= 1
    assert SecurityCategory.OTP_THEFT in summary.categories
    assert SecurityCategory.URGENT_PAYMENT in summary.categories


def test_session_summary_empty_session_and_disconnected_session():
    protection = ProtectionService("s12")
    intelligence = SessionIntelligenceService("s12")
    protection.end_session()
    summary = intelligence.build_summary(protection.build_session_summary())
    assert summary.evidence_count == 0
    assert summary.final_risk_score == 0.0
    assert summary.session_duration_seconds is not None
