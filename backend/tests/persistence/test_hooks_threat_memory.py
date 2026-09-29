"""Phase 8 — PersistenceHooks tests for the Threat Memory integration
surface: check_threat_memory() dedup within a session, the
maybe_promote_threat() policy gate, and build_known_threat_signals()
producing real ThreatSignal objects usable by the existing
run_risk_engine() — gaps #4, #5, #6, #7 from the phase brief.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.db import session_repo
from app.db.threat_memory_models import Threat
from app.models.enums import EvidenceState, RecommendedAction, ThreatSeverity
from app.models.risk import RiskResult
from app.models.threat import ThreatSignal
from app.services.persistence.hooks import PersistenceHooks
from app.services.threat_memory.matcher import SessionSignature
from app.services.threat_memory import repository as threat_memory_repo

from app.models.enums import ThreatCategory

REAL_CAT = list(ThreatCategory)[0].value

pytestmark = pytest.mark.asyncio


def _risk_result(severity=ThreatSeverity.CRITICAL, evidence_state=EvidenceState.SUFFICIENT, confidence=0.85):
    return RiskResult(
        score=90.0,
        severity=severity,
        confidence=confidence,
        evidence_state=evidence_state,
        risk_factors=[],
        explanation="test",
        recommended_action=RecommendedAction.ESCALATE,
    )


async def _make_session(db, session_id):
    await session_repo.upsert_session(db, session_id=session_id, started_at=datetime.now(timezone.utc))
    await db.commit()


async def test_check_threat_memory_matches_and_deduplicates_within_session(db_session):
    await _make_session(db_session, "sess-A")
    signature = SessionSignature(
        signal_types=frozenset({"sensitive_information_request", "urgency_pressure"}),
        categories=frozenset(),
    )
    await threat_memory_repo.create_threat_from_session(
        db_session, signature=signature, category=REAL_CAT,
        severity="critical", confidence=0.9, title="Known scam", description="test",
    )
    await db_session.commit()

    await _make_session(db_session, "sess-B")
    hooks = PersistenceHooks("sess-B", db=db_session)
    hooks._signal_types = {"sensitive_information_request", "urgency_pressure"}

    first = await hooks.check_threat_memory()
    assert len(first) == 1
    assert first[0]["title"] == "Known scam"

    # same pass or a later pass with the same accumulated signals: no
    # repeated ThreatMatch row for a threat already matched this session
    second = await hooks.check_threat_memory()
    assert second == []


async def test_build_known_threat_signals_produces_valid_threat_signal(db_session):
    hooks = PersistenceHooks("sess-B", db=db_session)
    hooks._known_threat_matches = [
        {
            "threat_id": "abc-123",
            "title": "Known scam",
            "category": REAL_CAT,
            "severity": "critical",
            "match_score": 0.82,
            "occurrence_count": 3,
            "matched_patterns": [],
        }
    ]
    signals = hooks.build_known_threat_signals()
    assert len(signals) == 1
    signal = signals[0]
    assert isinstance(signal, ThreatSignal)
    assert signal.confidence == 0.82
    assert signal.source == "threat_memory"
    assert signal.metadata["occurrence_count"] == 3
    # This is the actual "feed into the existing risk pipeline" step: the
    # object is a real ThreatSignal, usable directly by run_risk_engine().


async def test_build_known_threat_signals_skips_invalid_category(db_session):
    hooks = PersistenceHooks("sess-B", db=db_session)
    hooks._known_threat_matches = [
        {
            "threat_id": "abc-123",
            "title": "Legacy seeded threat",
            "category": "not_a_real_threat_category",
            "severity": "critical",
            "match_score": 0.9,
            "occurrence_count": 1,
            "matched_patterns": [],
        }
    ]
    assert hooks.build_known_threat_signals() == []


@pytest.mark.parametrize(
    "severity,evidence_state,should_promote",
    [
        (ThreatSeverity.CRITICAL, EvidenceState.SUFFICIENT, True),
        (ThreatSeverity.HIGH, EvidenceState.SUFFICIENT, True),
        (ThreatSeverity.MEDIUM, EvidenceState.SUFFICIENT, False),  # severity too low
        (ThreatSeverity.CRITICAL, EvidenceState.PARTIAL, False),  # evidence insufficient
    ],
)
async def test_promotion_policy_gates_on_severity_and_evidence(
    db_session, severity, evidence_state, should_promote
):
    await _make_session(db_session, "sess-A")
    hooks = PersistenceHooks("sess-A", db=db_session)
    await hooks.on_risk_result(
        _risk_result(severity=severity, evidence_state=evidence_state),
        timestamp=datetime.now(timezone.utc),
    )
    hooks._signal_types = {"sensitive_information_request"}

    result = await hooks.maybe_promote_threat()
    if should_promote:
        assert result is not None
        threat = await db_session.get(Threat, uuid.UUID(result))
        assert threat is not None
    else:
        assert result is None


async def test_promotion_does_not_duplicate_equivalent_active_threat(db_session):
    await _make_session(db_session, "sess-A")
    hooks_a = PersistenceHooks("sess-A", db=db_session)
    await hooks_a.on_risk_result(_risk_result(), timestamp=datetime.now(timezone.utc))
    hooks_a._signal_types = {"sensitive_information_request", "urgency_pressure"}
    threat_id_1 = await hooks_a.maybe_promote_threat()
    assert threat_id_1 is not None

    await _make_session(db_session, "sess-B")
    hooks_b = PersistenceHooks("sess-B", db=db_session)
    await hooks_b.on_risk_result(_risk_result(), timestamp=datetime.now(timezone.utc))
    hooks_b._signal_types = {"sensitive_information_request", "urgency_pressure"}  # identical signature
    threat_id_2 = await hooks_b.maybe_promote_threat()

    assert threat_id_2 == threat_id_1  # recognized as the same threat, not duplicated

    result = await db_session.execute(select(Threat))
    assert len(result.scalars().all()) == 1


async def test_promotion_with_no_signals_does_not_promote(db_session):
    await _make_session(db_session, "sess-A")
    hooks = PersistenceHooks("sess-A", db=db_session)
    await hooks.on_risk_result(_risk_result(), timestamp=datetime.now(timezone.utc))
    # no signal_types / categories accumulated at all
    result = await hooks.maybe_promote_threat()
    assert result is None


async def test_match_dict_exposes_indicators_for_known_threat_match_frame(db_session):
    await _make_session(db_session, "sess-A")
    signature = SessionSignature(
        signal_types=frozenset({"urgency_pressure"}), categories=frozenset()
    )
    await threat_memory_repo.create_threat_from_session(
        db_session, signature=signature, category=REAL_CAT,
        severity="critical", confidence=0.9, title="T", description="d",
    )
    await db_session.commit()
    await _make_session(db_session, "sess-B")
    hooks = PersistenceHooks("sess-B", db=db_session)
    hooks._signal_types = {"urgency_pressure"}
    (match,) = await hooks.check_threat_memory()
    assert len(match["matched_indicators"]) == 1
    assert match["match_score"] == 1.0
    assert match["occurrence_count"] == 1


async def test_session_isolation_between_hooks_instances(db_session):
    await _make_session(db_session, "sess-A")
    await _make_session(db_session, "sess-B")
    a = PersistenceHooks("sess-A", db=db_session)
    b = PersistenceHooks("sess-B", db=db_session)
    a._signal_types = {"urgency_pressure"}
    assert b._signal_types == set()
    assert await b.check_threat_memory() == []


async def test_repeated_analysis_same_session_accumulates_without_duplicate_match(db_session):
    await _make_session(db_session, "sess-A")
    sig = SessionSignature(signal_types=frozenset({"urgency_pressure"}), categories=frozenset())
    await threat_memory_repo.create_threat_from_session(
        db_session, signature=sig, category=REAL_CAT,
        severity="critical", confidence=0.9, title="T", description="d",
    )
    await db_session.commit()
    await _make_session(db_session, "sess-B")
    hooks = PersistenceHooks("sess-B", db=db_session)
    hooks._signal_types = {"urgency_pressure"}
    for _ in range(3):
        await hooks.check_threat_memory()
    from app.db.threat_memory_models import ThreatMatch
    rows = (await db_session.execute(select(ThreatMatch))).scalars().all()
    assert len(rows) == 1
    assert len(hooks.build_known_threat_signals()) == 1
