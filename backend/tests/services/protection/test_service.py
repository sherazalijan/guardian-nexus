from datetime import datetime, timezone

from app.models.enums import ThreatCategory, ThreatSeverity
from app.models.protection import ProtectionEventType, ProtectionState, SecurityCategory
from app.models.risk import RiskResult
from app.models.threat import ThreatSignal
from app.services.protection.service import ProtectionService

NOW = datetime.now(timezone.utc)


def _signal(
    indicator: str,
    category: ThreatCategory,
    confidence: float = 0.8,
    evidence: str = "matched evidence",
) -> ThreatSignal:
    return ThreatSignal(
        category=category,
        indicator=indicator,
        evidence=evidence,
        confidence=confidence,
        source="rule-based-scam-agent",
        timestamp=NOW,
    )


def _risk(
    score: float,
    severity: ThreatSeverity,
    signals: list[ThreatSignal] | None = None,
) -> RiskResult:
    from app.models.enums import EvidenceState, RecommendedAction
    from app.services.risk_engine import run_risk_engine

    if signals is not None:
        return run_risk_engine(signals)

    # Manual construction for tests that just want to drive severity/score.
    return RiskResult(
        score=score,
        severity=severity,
        confidence=0.5,
        evidence_state=EvidenceState.PARTIAL,
        risk_factors=[],
        explanation="test",
        recommended_action=RecommendedAction.MONITOR,
    )


# --- Protection event creation -------------------------------------------------


def test_process_creates_threat_detected_event_for_new_signal():
    service = ProtectionService("session-1", now=lambda: NOW)
    signal = _signal("otp_request", ThreatCategory.PHISHING)
    risk = _risk(30.0, ThreatSeverity.MEDIUM, signals=[signal])

    result = service.process(threat_signals=[signal], risk_result=risk)

    threat_events = [
        e for e in result.events if e.event_type == ProtectionEventType.THREAT_DETECTED
    ]
    assert len(threat_events) == 1
    assert threat_events[0].category == SecurityCategory.OTP_THEFT
    assert threat_events[0].session_id == "session-1"
    assert threat_events[0].evidence == [signal.evidence]


def test_process_with_no_signals_and_no_threat_produces_no_threat_events():
    service = ProtectionService("session-2", now=lambda: NOW)
    risk = _risk(0.0, ThreatSeverity.LOW, signals=[])

    result = service.process(threat_signals=[], risk_result=risk)

    assert result.events == []
    assert result.state == ProtectionState.MONITORING


def test_process_multiple_different_threats_creates_multiple_events():
    service = ProtectionService("session-3", now=lambda: NOW)
    signals = [
        _signal("otp_request", ThreatCategory.PHISHING),
        _signal("bank_impersonation", ThreatCategory.IMPERSONATION),
    ]
    risk = _risk(0, ThreatSeverity.LOW, signals=signals)

    result = service.process(threat_signals=signals, risk_result=risk)

    threat_events = [
        e for e in result.events if e.event_type == ProtectionEventType.THREAT_DETECTED
    ]
    categories = {e.category for e in threat_events}
    assert categories == {SecurityCategory.OTP_THEFT, SecurityCategory.BANK_IMPERSONATION}


# --- Duplicate warning suppression ---------------------------------------------


def test_repeated_identical_threat_is_not_re_emitted():
    service = ProtectionService("session-4", now=lambda: NOW)
    signal = _signal("otp_request", ThreatCategory.PHISHING)
    risk = _risk(30.0, ThreatSeverity.MEDIUM, signals=[signal])

    first = service.process(threat_signals=[signal], risk_result=risk)
    second = service.process(threat_signals=[signal], risk_result=risk)

    first_threats = [
        e for e in first.events if e.event_type == ProtectionEventType.THREAT_DETECTED
    ]
    second_threats = [
        e for e in second.events if e.event_type == ProtectionEventType.THREAT_DETECTED
    ]
    assert len(first_threats) == 1
    assert len(second_threats) == 0


def test_duplicate_suppression_is_per_category_not_per_evidence_text():
    """Same rule, slightly different matched text -> still deduplicated."""
    service = ProtectionService("session-5", now=lambda: NOW)
    signal_a = _signal("otp_request", ThreatCategory.PHISHING, evidence="OTP")
    signal_b = _signal("otp_request", ThreatCategory.PHISHING, evidence="otp code")

    risk_a = _risk(30.0, ThreatSeverity.MEDIUM, signals=[signal_a])
    service.process(threat_signals=[signal_a], risk_result=risk_a)

    risk_b = _risk(30.0, ThreatSeverity.MEDIUM, signals=[signal_b])
    second = service.process(threat_signals=[signal_b], risk_result=risk_b)

    threat_events = [
        e for e in second.events if e.event_type == ProtectionEventType.THREAT_DETECTED
    ]
    assert threat_events == []


# --- Risk escalation / severity transitions ------------------------------------


def test_low_to_medium_emits_risk_escalated():
    service = ProtectionService("session-6", now=lambda: NOW)
    service.process(threat_signals=[], risk_result=_risk(20.0, ThreatSeverity.LOW))

    result = service.process(threat_signals=[], risk_result=_risk(52.0, ThreatSeverity.MEDIUM))

    types = {e.event_type for e in result.events}
    assert ProtectionEventType.RISK_ESCALATED in types
    assert result.state == ProtectionState.SUSPICIOUS


def test_medium_to_high_emits_warning():
    service = ProtectionService("session-7", now=lambda: NOW)
    service.process(threat_signals=[], risk_result=_risk(52.0, ThreatSeverity.MEDIUM))

    result = service.process(threat_signals=[], risk_result=_risk(78.0, ThreatSeverity.HIGH))

    types = {e.event_type for e in result.events}
    assert ProtectionEventType.WARNING in types
    assert result.state == ProtectionState.HIGH_RISK


def test_high_to_critical_emits_critical_alert():
    service = ProtectionService("session-8", now=lambda: NOW)
    service.process(threat_signals=[], risk_result=_risk(78.0, ThreatSeverity.HIGH))

    result = service.process(threat_signals=[], risk_result=_risk(92.0, ThreatSeverity.CRITICAL))

    types = {e.event_type for e in result.events}
    assert ProtectionEventType.CRITICAL_ALERT in types
    assert result.state == ProtectionState.CRITICAL


def test_no_escalation_event_within_the_same_severity_band():
    service = ProtectionService("session-9", now=lambda: NOW)
    service.process(threat_signals=[], risk_result=_risk(20.0, ThreatSeverity.LOW))

    result = service.process(threat_signals=[], risk_result=_risk(25.0, ThreatSeverity.LOW))

    escalation_types = {
        ProtectionEventType.RISK_ESCALATED,
        ProtectionEventType.WARNING,
        ProtectionEventType.CRITICAL_ALERT,
    }
    assert not (escalation_types & {e.event_type for e in result.events})


def test_severity_decrease_does_not_emit_escalation_event():
    service = ProtectionService("session-10", now=lambda: NOW)
    service.process(threat_signals=[], risk_result=_risk(92.0, ThreatSeverity.CRITICAL))

    result = service.process(threat_signals=[], risk_result=_risk(20.0, ThreatSeverity.LOW))

    escalation_types = {
        ProtectionEventType.RISK_ESCALATED,
        ProtectionEventType.WARNING,
        ProtectionEventType.CRITICAL_ALERT,
    }
    assert not (escalation_types & {e.event_type for e in result.events})
    # Highest severity/score reached this session must still be remembered.
    summary = service.build_session_summary()
    assert summary.highest_severity == ThreatSeverity.CRITICAL
    assert summary.highest_risk_score == 92.0


def test_warning_and_critical_counts_are_tracked():
    service = ProtectionService("session-11", now=lambda: NOW)
    service.process(threat_signals=[], risk_result=_risk(20.0, ThreatSeverity.LOW))
    service.process(threat_signals=[], risk_result=_risk(70.0, ThreatSeverity.HIGH))
    service.process(threat_signals=[], risk_result=_risk(20.0, ThreatSeverity.LOW))
    service.process(threat_signals=[], risk_result=_risk(70.0, ThreatSeverity.HIGH))
    service.process(threat_signals=[], risk_result=_risk(92.0, ThreatSeverity.CRITICAL))

    summary = service.build_session_summary()
    assert summary.warning_count == 2
    assert summary.critical_alert_count == 1


# --- Protection state -----------------------------------------------------------


def test_protection_state_mirrors_current_severity_not_highest():
    service = ProtectionService("session-12", now=lambda: NOW)
    service.process(threat_signals=[], risk_result=_risk(92.0, ThreatSeverity.CRITICAL))
    result = service.process(threat_signals=[], risk_result=_risk(20.0, ThreatSeverity.LOW))

    assert result.state == ProtectionState.MONITORING
    assert service.state == ProtectionState.MONITORING


# --- Timeline events -------------------------------------------------------------


def test_session_starts_with_a_session_started_timeline_entry():
    service = ProtectionService("session-13", now=lambda: NOW)
    assert service.build_session_summary().session_started_at == NOW


def test_timeline_events_are_structured_not_formatted_strings():
    service = ProtectionService("session-14", now=lambda: NOW)
    signal = _signal("otp_request", ThreatCategory.PHISHING)
    risk = _risk(30.0, ThreatSeverity.MEDIUM, signals=[signal])

    result = service.process(threat_signals=[signal], risk_result=risk)

    assert len(result.timeline_events) >= 1
    for event in result.timeline_events:
        assert event.session_id == "session-14"
        assert event.label
        assert event.timestamp == NOW


# --- Session summary --------------------------------------------------------------


def test_session_summary_before_end_has_no_end_time():
    service = ProtectionService("session-15", now=lambda: NOW)
    summary = service.build_session_summary()

    assert summary.session_ended_at is None
    assert summary.duration_seconds is None


def test_end_session_sets_duration():
    times = iter([NOW, NOW.replace(microsecond=0)])
    start = NOW
    end = NOW.fromtimestamp(NOW.timestamp() + 30, tz=timezone.utc)
    calls = iter([start, end])

    service = ProtectionService("session-16", now=lambda: next(calls))
    service.end_session()

    summary = service.build_session_summary()
    assert summary.session_ended_at == end
    assert summary.duration_seconds == 30.0


def test_session_summary_reflects_detected_categories_and_signals():
    service = ProtectionService("session-17", now=lambda: NOW)
    signals = [
        _signal("otp_request", ThreatCategory.PHISHING),
        _signal("gift_card_request", ThreatCategory.FRAUD),
    ]
    risk = _risk(0, ThreatSeverity.LOW, signals=signals)
    service.process(threat_signals=signals, risk_result=risk)

    summary = service.build_session_summary()
    assert SecurityCategory.OTP_THEFT in summary.detected_categories
    assert SecurityCategory.GIFT_CARD_SCAM in summary.detected_categories
    assert "otp_request" in summary.detected_signals
    assert "gift_card_request" in summary.detected_signals


# --- Robustness: empty / malformed input ------------------------------------------


def test_process_handles_empty_signal_list_safely():
    service = ProtectionService("session-18", now=lambda: NOW)
    risk = _risk(0.0, ThreatSeverity.LOW, signals=[])

    result = service.process(threat_signals=[], risk_result=risk)

    assert result.events == []
    assert result.timeline_events  # still logs the risk-score timeline entry
    assert result.state == ProtectionState.MONITORING


def test_process_is_idempotent_safe_for_partial_transcripts_with_no_signals():
    service = ProtectionService("session-19", now=lambda: NOW)
    risk = _risk(0.0, ThreatSeverity.LOW, signals=[])

    for _ in range(3):
        result = service.process(threat_signals=[], risk_result=risk)
        assert result.events == []
