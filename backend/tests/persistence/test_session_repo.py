"""Phase 8 — persistence tests for app.db.session_repo.

Covers: model registration/relationships/constraints (via successful
create_all + round-trip in conftest.db_session), and one test per
persisted Pydantic model type per the phase brief's "Persistence" test
list.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.db import models as db_models
from app.db import session_repo
from app.models.enums import EvidenceState, RecommendedAction, ThreatCategory, ThreatSeverity
from app.models.protection import (
    ProtectionEvent,
    ProtectionEventType,
    ProtectionState,
    SecurityCategory,
    SessionSummary,
)
from app.models.risk import RiskFactor, RiskResult
from app.models.session_intelligence import EvidenceItem
from app.models.voice_intelligence import VoiceSignal, VoiceSignalType

pytestmark = pytest.mark.asyncio


async def _make_session(db, session_id="sess-1"):
    await session_repo.upsert_session(
        db, session_id=session_id, started_at=datetime.now(timezone.utc)
    )
    await db.commit()


async def test_upsert_session_is_idempotent(db_session):
    await _make_session(db_session, "sess-1")
    await _make_session(db_session, "sess-1")  # second call must not duplicate/raise

    result = await db_session.execute(
        select(db_models.Session).where(db_models.Session.id == "sess-1")
    )
    rows = result.scalars().all()
    assert len(rows) == 1


async def test_end_session_sets_final_fields(db_session):
    await _make_session(db_session, "sess-1")
    await session_repo.end_session(
        db_session,
        session_id="sess-1",
        ended_at=datetime.now(timezone.utc),
        final_risk_score=42.0,
        highest_risk_score=90.0,
        highest_severity="high",
    )
    await db_session.commit()

    row = await db_session.get(db_models.Session, "sess-1")
    assert row.status == "ended"
    assert row.final_risk_score == 42.0
    assert row.highest_severity == "high"


async def test_save_transcript_segment(db_session):
    await _make_session(db_session)
    await session_repo.save_transcript_segment(
        db_session,
        session_id="sess-1",
        sequence=0,
        text="hello",
        is_final=True,
        confidence=0.9,
        timestamp=datetime.now(timezone.utc),
    )
    await db_session.commit()

    result = await db_session.execute(
        select(db_models.TranscriptSegment).where(
            db_models.TranscriptSegment.session_id == "sess-1"
        )
    )
    row = result.scalar_one()
    assert row.text == "hello"
    assert row.sequence == 0


async def test_save_risk_result(db_session):
    await _make_session(db_session)
    risk_result = RiskResult(
        score=75.0,
        severity=ThreatSeverity.HIGH,
        confidence=0.8,
        evidence_state=EvidenceState.SUFFICIENT,
        risk_factors=[RiskFactor(name="x", description="y", contribution=0.5)],
        explanation="test",
        recommended_action=RecommendedAction.WARN,
    )
    await session_repo.save_risk_result(
        db_session, session_id="sess-1", risk_result=risk_result,
        timestamp=datetime.now(timezone.utc),
    )
    await db_session.commit()

    result = await db_session.execute(
        select(db_models.RiskEvent).where(db_models.RiskEvent.session_id == "sess-1")
    )
    row = result.scalar_one()
    assert row.score == 75.0
    assert row.severity == "high"
    assert row.risk_factors[0]["name"] == "x"


async def test_save_evidence(db_session):
    await _make_session(db_session)
    item = EvidenceItem(
        session_id="sess-1",
        text="asked for OTP",
        signal="otp_request",
        category=SecurityCategory.OTP_THEFT,
        severity=ThreatSeverity.HIGH,
        risk_score=80.0,
        confidence=0.9,
    )
    await session_repo.save_evidence(db_session, evidence_item=item)
    await db_session.commit()

    row = await db_session.get(db_models.Evidence, item.evidence_id)
    assert row.signal == "otp_request"
    assert row.category == "otp_theft"


async def test_save_protection_event(db_session):
    await _make_session(db_session)
    event = ProtectionEvent(
        session_id="sess-1",
        event_type=ProtectionEventType.WARNING,
        severity=ThreatSeverity.MEDIUM,
        risk_score=50.0,
        title="Warning",
        message="Be careful",
        category=SecurityCategory.PHISHING,
        recommended_action="hang up",
        confidence=0.7,
    )
    await session_repo.save_protection_event(db_session, event=event)
    await db_session.commit()

    row = await db_session.get(db_models.ProtectionEventRow, event.event_id)
    assert row.title == "Warning"
    assert row.category == "phishing"


async def test_save_voice_signal(db_session):
    await _make_session(db_session)
    signal = VoiceSignal(
        session_id="sess-1",
        signal_type=VoiceSignalType.URGENCY_PRESSURE,
        category=ThreatCategory.UNKNOWN,
        confidence=0.6,
        severity=ThreatSeverity.MEDIUM,
        evidence_text="hurry up",
        source="voice-intelligence-agent",
    )
    await session_repo.save_voice_signal(db_session, signal=signal)
    await db_session.commit()

    row = await db_session.get(db_models.VoiceSignalRow, signal.signal_id)
    assert row.signal_type == "urgency_pressure"


async def test_save_session_summary_is_write_once(db_session):
    await _make_session(db_session)
    summary = SessionSummary(
        session_id="sess-1",
        highest_risk_score=90.0,
        final_risk_score=80.0,
        highest_severity=ThreatSeverity.CRITICAL,
        warning_count=2,
        critical_alert_count=1,
        recommended_final_action="end call",
    )
    await session_repo.save_session_summary(
        db_session, session_id="sess-1", summary=summary, extra={"evidence_count": 3}
    )
    await db_session.commit()

    # second call for the same session must be a no-op, not raise / duplicate
    await session_repo.save_session_summary(
        db_session, session_id="sess-1", summary=summary, extra={"evidence_count": 999}
    )
    await db_session.commit()

    row = await db_session.get(db_models.SessionSummaryRow, "sess-1")
    assert row.extra["evidence_count"] == 3
