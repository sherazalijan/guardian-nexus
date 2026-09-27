from datetime import datetime, timezone

import pytest

from app.models.enums import ThreatSeverity
from app.models.intervention import InterventionPriority, InterventionStatus
from app.models.protection import (
    ProtectionEvent,
    ProtectionEventType,
    ProtectionState,
    SecurityCategory,
)
from app.services.intervention.policy import InterventionPolicyService
from app.services.protection.service import ProtectionAnalysisResult


def make_event(
    *,
    severity=ThreatSeverity.HIGH,
    risk_score=70.0,
    category=SecurityCategory.OTP_THEFT,
    event_type=ProtectionEventType.THREAT_DETECTED,
    title="Possible OTP theft attempt",
    message="The caller is requesting a one-time password.",
    recommended_action="Do not share your OTP.",
    evidence=None,
) -> ProtectionEvent:
    return ProtectionEvent(
        session_id="s1",
        event_type=event_type,
        severity=severity,
        risk_score=risk_score,
        title=title,
        message=message,
        category=category,
        evidence=evidence or ["caller asked for OTP"],
        recommended_action=recommended_action,
        confidence=0.9,
    )


def make_result(events: list[ProtectionEvent]) -> ProtectionAnalysisResult:
    return ProtectionAnalysisResult(
        events=events, timeline_events=[], state=ProtectionState.HIGH_RISK, state_changed=True
    )


@pytest.fixture
def policy() -> InterventionPolicyService:
    return InterventionPolicyService("s1")


# -- no intervention ---------------------------------------------------

def test_no_intervention_for_low_severity(policy):
    event = make_event(severity=ThreatSeverity.LOW, risk_score=10)
    assert policy.decide(make_result([event])) == []


def test_no_events_no_intervention(policy):
    assert policy.decide(make_result([])) == []


# -- priority tiers, reusing ProtectionEvent copy verbatim ---------------

def test_medium_intervention_no_ack_required(policy):
    event = make_event(
        severity=ThreatSeverity.MEDIUM, risk_score=40, category=SecurityCategory.SOCIAL_ENGINEERING
    )
    ivs = policy.decide(make_result([event]))
    assert len(ivs) == 1
    assert ivs[0].priority == InterventionPriority.MEDIUM
    assert ivs[0].requires_acknowledgement is False
    assert ivs[0].title == event.title
    assert ivs[0].message == event.message
    assert ivs[0].recommended_action == event.recommended_action


def test_high_intervention_requires_ack(policy):
    event = make_event(
        severity=ThreatSeverity.HIGH, risk_score=70, category=SecurityCategory.BANK_IMPERSONATION
    )
    ivs = policy.decide(make_result([event]))
    assert ivs[0].priority == InterventionPriority.HIGH
    assert ivs[0].requires_acknowledgement is True


def test_critical_intervention_requires_ack(policy):
    event = make_event(severity=ThreatSeverity.CRITICAL, risk_score=95)
    ivs = policy.decide(make_result([event]))
    assert ivs[0].priority == InterventionPriority.CRITICAL
    assert ivs[0].requires_acknowledgement is True


# -- deduplication / cooldown --------------------------------------------

def test_duplicate_signal_suppressed(policy):
    first = policy.decide(
        make_result([make_event(severity=ThreatSeverity.MEDIUM, category=SecurityCategory.URGENT_PAYMENT)])
    )
    second = policy.decide(
        make_result([make_event(severity=ThreatSeverity.MEDIUM, category=SecurityCategory.URGENT_PAYMENT)])
    )
    assert len(first) == 1
    assert second == []


def test_duplicate_suppressed_after_acknowledgement(policy):
    ivs = policy.decide(
        make_result([make_event(severity=ThreatSeverity.HIGH, category=SecurityCategory.CREDENTIAL_THEFT)])
    )
    policy.acknowledge(ivs[0].intervention_id)
    second = policy.decide(
        make_result([make_event(severity=ThreatSeverity.HIGH, category=SecurityCategory.CREDENTIAL_THEFT)])
    )
    assert second == []  # acknowledging does not mean the threat is gone,
    # but a same-level repeat is still a duplicate, not a new warning


def test_escalation_bypasses_suppression(policy):
    first = policy.decide(
        make_result([make_event(severity=ThreatSeverity.MEDIUM, category=SecurityCategory.OTP_THEFT, risk_score=45)])
    )
    second = policy.decide(
        make_result([make_event(severity=ThreatSeverity.CRITICAL, category=SecurityCategory.OTP_THEFT, risk_score=92)])
    )
    assert len(first) == 1
    assert len(second) == 1
    assert second[0].priority == InterventionPriority.CRITICAL
    assert second[0].escalated_from == first[0].intervention_id

    original = next(
        i for i in policy.history().interventions if i.intervention_id == first[0].intervention_id
    )
    assert original.status == InterventionStatus.ESCALATED


def test_same_category_materially_higher_risk_creates_new_intervention(policy):
    policy.decide(
        make_result([make_event(severity=ThreatSeverity.MEDIUM, category=SecurityCategory.REMOTE_ACCESS_SCAM)])
    )
    second = policy.decide(
        make_result([make_event(severity=ThreatSeverity.HIGH, category=SecurityCategory.REMOTE_ACCESS_SCAM)])
    )
    assert len(second) == 1
    assert second[0].priority == InterventionPriority.HIGH


# -- acknowledgement ------------------------------------------------------

def test_acknowledge_active_intervention(policy):
    ivs = policy.decide(make_result([make_event(severity=ThreatSeverity.CRITICAL)]))
    result = policy.acknowledge(ivs[0].intervention_id)
    assert result.success is True
    assert result.status == InterventionStatus.ACKNOWLEDGED


def test_repeated_acknowledgement_is_safe(policy):
    ivs = policy.decide(make_result([make_event(severity=ThreatSeverity.CRITICAL)]))
    policy.acknowledge(ivs[0].intervention_id)
    second = policy.acknowledge(ivs[0].intervention_id)
    assert second.success is True
    assert second.reason == "already_acknowledged"


def test_acknowledge_unknown_intervention(policy):
    result = policy.acknowledge("int_does_not_exist")
    assert result.success is False
    assert result.reason == "not_found"


def test_acknowledge_after_resolution_fails(policy):
    ivs = policy.decide(make_result([make_event(severity=ThreatSeverity.CRITICAL)]))
    policy.resolve()
    result = policy.acknowledge(ivs[0].intervention_id)
    assert result.success is False
    assert result.reason == "already_resolved"


# -- resolution / session isolation --------------------------------------

def test_session_end_resolves_active_interventions(policy):
    policy.decide(make_result([make_event(severity=ThreatSeverity.CRITICAL)]))
    policy.resolve()
    history = policy.history()
    assert history.interventions[0].status == InterventionStatus.RESOLVED
    assert history.interventions[0].resolved_at is not None


def test_session_isolation():
    policy_a = InterventionPolicyService("sA")
    policy_b = InterventionPolicyService("sB")
    policy_a.decide(
        make_result([make_event(severity=ThreatSeverity.CRITICAL, category=SecurityCategory.OTP_THEFT)])
    )
    ivs_b = policy_b.decide(
        make_result([make_event(severity=ThreatSeverity.CRITICAL, category=SecurityCategory.OTP_THEFT)])
    )
    assert len(ivs_b) == 1
    assert policy_a.history().count == 1
    assert policy_b.history().count == 1


# -- history / summary -----------------------------------------------------

def test_history_summary_fields(policy):
    policy.decide(
        make_result([make_event(severity=ThreatSeverity.MEDIUM, category=SecurityCategory.URGENT_PAYMENT)])
    )
    policy.decide(
        make_result([make_event(severity=ThreatSeverity.CRITICAL, category=SecurityCategory.URGENT_PAYMENT)])
    )
    summary = policy.summary()
    assert summary["total_interventions"] == 2
    assert summary["escalated_count"] == 1
    assert summary["highest_priority"] == "critical"
    assert summary["has_critical"] is True
    assert "urgent_payment" in summary["categories"]


# -- websocket event shape / malformed input -----------------------------

def test_to_ws_event_shape(policy):
    ivs = policy.decide(make_result([make_event(severity=ThreatSeverity.CRITICAL)]))
    event = ivs[0].to_ws_event()
    assert event["type"] == "intervention"
    data = event["data"]
    for key in (
        "intervention_id", "session_id", "priority", "risk_score", "title",
        "message", "category", "recommended_action",
        "requires_acknowledgement", "status",
    ):
        assert key in data


def test_malformed_input_no_events_no_crash(policy):
    assert policy.decide(make_result([])) == []
