"""Phase 8 — pure unit tests for app.services.threat_memory.matcher.

No database access: `score_match`/`find_matches` take plain ORM objects
in memory, so these are fast, deterministic, and need no fixtures.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.db.threat_memory_models import Threat, ThreatIndicator, ThreatPattern
from app.services.threat_memory.matcher import SessionSignature, find_matches, score_match


def _threat(indicators: list[ThreatIndicator], patterns: list[ThreatPattern] | None = None) -> Threat:
    t = Threat(
        id=uuid.uuid4(),
        category="bank_impersonation",
        type="bank_impersonation",
        title="Bank impersonation + OTP",
        description="test",
        severity="critical",
        confidence=0.8,
        status="active",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        occurrence_count=0,
    )
    t.indicators = indicators
    t.patterns = patterns or []
    return t


def _indicator(threat_id, *, signal_type=None, category=None, weight=1.0):
    return ThreatIndicator(
        id=uuid.uuid4(),
        threat_id=threat_id,
        signal_type=signal_type,
        category=category,
        normalized_value=signal_type or category,
        weight=weight,
    )


def test_full_overlap_scores_1_0():
    t = _threat([])
    t.indicators = [
        _indicator(t.id, signal_type="sensitive_information_request", weight=1.0),
        _indicator(t.id, signal_type="urgency_pressure", weight=1.0),
    ]
    sig = SessionSignature(
        signal_types=frozenset({"sensitive_information_request", "urgency_pressure"}),
        categories=frozenset(),
    )
    result = score_match(sig, t)
    assert result.score == 1.0


def test_partial_overlap_below_threshold_is_excluded_by_find_matches():
    t = _threat([])
    t.indicators = [
        _indicator(t.id, signal_type="a", weight=1.0),
        _indicator(t.id, signal_type="b", weight=1.0),
        _indicator(t.id, signal_type="c", weight=1.0),
        _indicator(t.id, signal_type="d", weight=1.0),
    ]
    # 1 of 4 signal_type indicators present -> score 0.25, below MATCH_THRESHOLD (0.6)
    sig = SessionSignature(signal_types=frozenset({"a"}), categories=frozenset())
    assert find_matches(sig, [t]) == []


def test_worked_example_three_of_four_signals_scores_0_75():
    t = _threat([])
    t.indicators = [
        _indicator(t.id, signal_type="sensitive_information_request", weight=1.0),
        _indicator(t.id, signal_type="account_compromise_claim", weight=1.0),
        _indicator(t.id, signal_type="urgency_pressure", weight=1.0),
        _indicator(t.id, signal_type="authority_impersonation", weight=1.0),
    ]
    sig = SessionSignature(
        signal_types=frozenset(
            {"sensitive_information_request", "account_compromise_claim", "urgency_pressure"}
        ),
        categories=frozenset(),
    )
    result = score_match(sig, t)
    assert result.score == 0.75
    matches = find_matches(sig, [t])
    assert len(matches) == 1
    assert matches[0].threat is t


def test_threat_with_no_indicators_scores_zero_not_error():
    t = _threat([])
    sig = SessionSignature(signal_types=frozenset({"anything"}), categories=frozenset())
    result = score_match(sig, t)
    assert result.score == 0.0


def test_category_indicator_matches_on_category_set():
    t = _threat([])
    t.indicators = [_indicator(t.id, category="otp_theft", weight=0.5)]
    sig = SessionSignature(signal_types=frozenset(), categories=frozenset({"otp_theft"}))
    result = score_match(sig, t)
    assert result.score == 1.0


def test_find_matches_sorts_descending_by_score():
    t_low = _threat([])
    t_low.indicators = [
        _indicator(t_low.id, signal_type="a", weight=1.0),
        _indicator(t_low.id, signal_type="b", weight=1.0),
    ]
    t_high = _threat([])
    t_high.indicators = [_indicator(t_high.id, signal_type="a", weight=1.0)]

    sig = SessionSignature(signal_types=frozenset({"a"}), categories=frozenset())
    # t_low: 1/2 = 0.5 (below threshold, excluded); t_high: 1/1 = 1.0 (included)
    matches = find_matches(sig, [t_low, t_high])
    assert len(matches) == 1
    assert matches[0].threat is t_high
