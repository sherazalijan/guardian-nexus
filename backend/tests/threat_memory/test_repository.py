"""Phase 8 — repository tests, against sqlite (see conftest.db_session).

Covers gaps #6/#7 from the phase brief plus the cross-session promotion
-> match -> occurrence flow it explicitly asks to be tested:

    Session A -> promote serious threat -> Threat exists, indicators exist
    Session B -> similar signals -> existing threat found -> ThreatMatch
                 created -> occurrence updated
    identical threat -> no duplicate Threat row
    different session -> session isolation preserved
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.db import session_repo
from app.db.threat_memory_models import Threat, ThreatMatch, ThreatOccurrence
from app.services.threat_memory import repository as threat_memory_repo
from app.services.threat_memory.matcher import SessionSignature, find_matches

pytestmark = pytest.mark.asyncio


async def _make_session(db, session_id):
    await session_repo.upsert_session(
        db, session_id=session_id, started_at=datetime.now(timezone.utc)
    )
    await db.commit()


async def test_create_threat_from_session_writes_indicators(db_session):
    await _make_session(db_session, "sess-A")
    signature = SessionSignature(
        signal_types=frozenset({"sensitive_information_request", "urgency_pressure"}),
        categories=frozenset({"bank_impersonation"}),
    )
    threat = await threat_memory_repo.create_threat_from_session(
        db_session,
        signature=signature,
        category="bank_impersonation",
        severity="critical",
        confidence=0.9,
        title="Bank OTP scam",
        description="test",
    )
    await db_session.commit()

    fetched = await db_session.get(Threat, threat.id)
    assert fetched is not None
    assert fetched.occurrence_count == 0

    active = await threat_memory_repo.get_active_threats(db_session)
    assert len(active) == 1
    assert {i.signal_type for i in active[0].indicators if i.signal_type} == {
        "sensitive_information_request",
        "urgency_pressure",
    }
    assert {i.category for i in active[0].indicators if i.category} == {"bank_impersonation"}


async def test_full_promotion_then_cross_session_match_flow(db_session):
    # --- Session A: promote a serious threat -----------------------------
    await _make_session(db_session, "sess-A")
    signature_a = SessionSignature(
        signal_types=frozenset(
            {"sensitive_information_request", "account_compromise_claim", "urgency_pressure"}
        ),
        categories=frozenset(),
    )
    threat = await threat_memory_repo.create_threat_from_session(
        db_session,
        signature=signature_a,
        category="bank_impersonation",
        severity="critical",
        confidence=0.9,
        title="Bank OTP scam",
        description="test",
    )
    await db_session.commit()
    assert threat.occurrence_count == 0

    # --- Session B: similar (not identical) signals -> match -------------
    await _make_session(db_session, "sess-B")
    signature_b = SessionSignature(
        signal_types=frozenset({"sensitive_information_request", "account_compromise_claim"}),
        categories=frozenset(),
    )
    active = await threat_memory_repo.get_active_threats(db_session)
    matches = find_matches(signature_b, active)
    assert len(matches) == 1  # 2/3 = 0.667 >= 0.6 threshold

    match_row = await threat_memory_repo.record_match(db_session, "sess-B", matches[0])
    await db_session.commit()

    assert match_row.session_id == "sess-B"
    assert match_row.threat_id == threat.id

    refreshed = await db_session.get(Threat, threat.id)
    assert refreshed.occurrence_count == 1  # updated by record_occurrence

    occ_result = await db_session.execute(
        select(ThreatOccurrence).where(ThreatOccurrence.threat_id == threat.id)
    )
    occurrences = occ_result.scalars().all()
    assert {o.session_id for o in occurrences} == {"sess-B"}  # session isolation: only sess-B logged

    # re-matching the SAME session again must not double-count
    match_row_2 = await threat_memory_repo.record_match(db_session, "sess-B", matches[0])
    await db_session.commit()
    refreshed_again = await db_session.get(Threat, threat.id)
    assert refreshed_again.occurrence_count == 1  # idempotent per (threat, session)


async def test_dedup_prevents_duplicate_threat_rows(db_session):
    await _make_session(db_session, "sess-A")
    await _make_session(db_session, "sess-C")

    signature = SessionSignature(
        signal_types=frozenset({"sensitive_information_request", "urgency_pressure"}),
        categories=frozenset({"bank_impersonation"}),
    )

    threat_1 = await threat_memory_repo.create_threat_from_session(
        db_session, signature=signature, category="bank_impersonation",
        severity="critical", confidence=0.9, title="First", description="test",
    )
    await db_session.commit()

    # Session C produces the EXACT same signature -> must be recognized as
    # equivalent, not create a second Threat row.
    existing = await threat_memory_repo.find_equivalent_active_threat(db_session, signature)
    assert existing is not None
    assert existing.id == threat_1.id

    await threat_memory_repo.record_occurrence(
        db_session, threat_id=existing.id, session_id="sess-C"
    )
    await db_session.commit()

    result = await db_session.execute(select(Threat))
    all_threats = result.scalars().all()
    assert len(all_threats) == 1  # no duplicate row


async def test_dedup_does_not_match_a_different_signature(db_session):
    await _make_session(db_session, "sess-A")
    signature_a = SessionSignature(
        signal_types=frozenset({"sensitive_information_request"}), categories=frozenset()
    )
    await threat_memory_repo.create_threat_from_session(
        db_session, signature=signature_a, category="bank_impersonation",
        severity="critical", confidence=0.9, title="A", description="test",
    )
    await db_session.commit()

    signature_different = SessionSignature(
        signal_types=frozenset({"crypto_request"}), categories=frozenset()
    )
    existing = await threat_memory_repo.find_equivalent_active_threat(
        db_session, signature_different
    )
    assert existing is None
