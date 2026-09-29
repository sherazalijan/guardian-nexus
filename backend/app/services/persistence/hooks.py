"""Phase 8 — the single integration surface between `app.api.routes` and
persistence/Threat Memory.

Design goal (per the phase brief): additive. `app.api.routes` gains a
handful of `await hooks.on_x(...)` calls at points where it already has
the object in hand (right after `await websocket.send_json(...)` for that
frame type), and nothing else about the existing control flow, error
handling, or WebSocket protocol changes.

One `PersistenceHooks` instance per WebSocket connection, same lifecycle
as `ProtectionService` et al. Owns one `AsyncSession` for the whole
connection and commits once per analysis pass (`flush_pass()`) rather
than once per object, so a single final transcript segment's full
protection/evidence/voice/intervention/alert fan-out is one round trip,
not a dozen.

Never raises into the caller: every public method wraps its body in
try/except and logs, mirroring the existing "a single bad transcript
fragment must not end the session" principle already used throughout
`app.api.routes._run_protection_analysis`. Persistence is additive
infrastructure — a DB hiccup must not take down the live protection
pipeline that already works today.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_sessionmaker
from app.db import session_repo
from app.models.enums import ThreatCategory
from app.models.threat import ThreatSignal
from app.services.threat_memory import repository as threat_memory_repo
from app.services.threat_memory.matcher import SessionSignature, find_matches

logger = logging.getLogger("guardian_nexus.persistence")

# Promotion policy (Phase 8 gap #6): only these severities, with
# sufficient evidence, are ever auto-promoted into persistent Threat
# Memory. Kept as a small module-level constant rather than a config
# knob for now — see PersistenceHooks.maybe_promote_threat.
_PROMOTABLE_SEVERITIES = {"high", "critical"}
_PROMOTABLE_EVIDENCE_STATES = {"sufficient"}


class PersistenceHooks:
    def __init__(self, session_id: str, db: AsyncSession | None = None) -> None:
        """`db` is normally left as None in production — routes.py always
        constructs `PersistenceHooks(session_id)` and this opens its own
        session via `get_sessionmaker()`, exactly as before. Tests pass an
        explicit `db` bound to a sqlite engine instead of requiring a real
        Postgres instance (see backend/tests/persistence/conftest.py)."""
        self._session_id = session_id
        self._db: AsyncSession = db if db is not None else get_sessionmaker()()
        self._signal_types: set[str] = set()
        self._categories: set[str] = set()
        self._threat_categories: set[str] = set()
        self._matched_threat_ids: set[str] = set()
        self._known_threat_matches: list[dict] = []
        self._last_severity: str | None = None
        self._last_evidence_state: str | None = None
        self._last_confidence: float | None = None

    # -- lifecycle -----------------------------------------------------

    async def start(self) -> None:
        try:
            await session_repo.upsert_session(
                self._db, session_id=self._session_id, started_at=datetime.now(timezone.utc)
            )
            await self._db.commit()
        except Exception:
            logger.exception("persistence: failed to open session %s", self._session_id)
            await self._db.rollback()

    async def close(self) -> None:
        try:
            await self._db.close()
        except Exception:
            logger.exception("persistence: failed to close db session for %s", self._session_id)

    # -- per-pass writes -------------------------------------------------
    # Each of these stages a write; call `flush_pass()` once at the end
    # of an analysis pass to commit everything staged since the last call.

    async def on_transcript_segment(self, *, sequence: int, text: str, is_final: bool,
                                     confidence: float | None) -> None:
        await self._safe(session_repo.save_transcript_segment(
            self._db, session_id=self._session_id, sequence=sequence, text=text,
            is_final=is_final, confidence=confidence, timestamp=datetime.now(timezone.utc),
        ))

    async def on_risk_result(self, risk_result, *, timestamp: datetime) -> None:
        # Cached for the end-of-session threat-promotion policy — see
        # maybe_promote_threat(). Cheap, in-memory, never raises.
        self._last_severity = risk_result.severity.value
        self._last_evidence_state = risk_result.evidence_state.value
        self._last_confidence = risk_result.confidence
        await self._safe(session_repo.save_risk_result(
            self._db, session_id=self._session_id, risk_result=risk_result, timestamp=timestamp
        ))

    async def on_threat_signals(self, signals: Sequence) -> None:
        """Accumulate the real `ThreatSignal.category` values seen this
        session (Phase 8 needs these to pick a genuine `ThreatCategory`
        when promoting a threat — see maybe_promote_threat — rather than
        borrowing `SecurityCategory` values from `on_protection_event`,
        which is a different vocabulary; see `app.models.protection`)."""
        for signal in signals:
            self._threat_categories.add(signal.category.value)

    async def on_protection_event(self, event) -> None:
        self._categories.add(event.category.value)
        await self._safe(session_repo.save_protection_event(self._db, event=event))

    async def on_timeline_event(self, event) -> None:
        await self._safe(session_repo.save_timeline_event(self._db, event=event))

    async def on_evidence(self, evidence_item) -> None:
        await self._safe(session_repo.save_evidence(self._db, evidence_item=evidence_item))

    async def on_incident_event(self, event) -> None:
        await self._safe(session_repo.save_incident_event(self._db, event=event))

    async def on_risk_history_entry(self, entry) -> None:
        await self._safe(session_repo.save_risk_history_entry(
            self._db, session_id=self._session_id, entry=entry
        ))

    async def on_voice_signal(self, signal) -> None:
        self._signal_types.add(signal.signal_type.value)
        await self._safe(session_repo.save_voice_signal(self._db, signal=signal))

    async def on_voice_pattern(self, pattern) -> None:
        await self._safe(session_repo.save_voice_pattern(self._db, pattern=pattern))

    async def on_intervention(self, intervention) -> None:
        await self._safe(session_repo.save_intervention(self._db, intervention=intervention))

    async def on_intervention_event(self, event) -> None:
        await self._safe(session_repo.save_intervention_event(
            self._db, session_id=self._session_id, event=event
        ))

    async def on_guardian_alert(self, alert) -> None:
        await self._safe(session_repo.save_guardian_alert(
            self._db, session_id=self._session_id, alert=alert
        ))

    async def on_guardian_alert_event(self, event) -> None:
        await self._safe(session_repo.save_guardian_alert_event(self._db, event=event))

    async def on_session_summary(self, summary, *, extra: dict) -> None:
        await self._safe(session_repo.save_session_summary(
            self._db, session_id=self._session_id, summary=summary, extra=extra
        ))
        await self._safe(session_repo.end_session(
            self._db,
            session_id=self._session_id,
            ended_at=summary.session_ended_at or datetime.now(timezone.utc),
            final_risk_score=summary.final_risk_score,
            highest_risk_score=summary.highest_risk_score,
            highest_severity=summary.highest_severity.value,
        ))

    async def flush_pass(self) -> None:
        try:
            await self._db.commit()
        except Exception:
            logger.exception("persistence: commit failed for session %s", self._session_id)
            await self._db.rollback()

    # -- Threat Memory ---------------------------------------------------

    async def check_threat_memory(self) -> list[dict]:
        """Compare this session's accumulated signature against active
        persisted threats. Returns new matches (threats not already
        matched this session) as plain dicts ready to build a client-
        facing `known_threat_match` frame from (see `app.api.routes`).

        Deterministic and read-mostly: writes only `ThreatMatch` /
        `ThreatOccurrence` rows for genuinely new matches, via
        `app.services.threat_memory.repository`. Never raises.
        """
        if not self._signal_types and not self._categories:
            return []
        try:
            threats = await threat_memory_repo.get_active_threats(self._db)
            signature = SessionSignature(
                signal_types=frozenset(self._signal_types),
                categories=frozenset(self._categories),
            )
            matches = find_matches(signature, threats)

            new_matches = [m for m in matches if str(m.threat.id) not in self._matched_threat_ids]
            results: list[dict] = []
            for match in new_matches:
                self._matched_threat_ids.add(str(match.threat.id))
                await threat_memory_repo.record_match(self._db, self._session_id, match)
                result = {
                    "threat_id": str(match.threat.id),
                    "title": match.threat.title,
                    "category": match.threat.category,
                    "severity": match.threat.severity,
                    "match_score": match.score,
                    "occurrence_count": match.threat.occurrence_count,  # already incremented by record_match
                    "matched_patterns": match.matched_pattern_types,
                    "matched_indicators": [str(i) for i in match.matched_indicator_ids],
                }
                results.append(result)
                self._known_threat_matches.append(result)
            if results:
                await self._db.commit()
            return results
        except Exception:
            logger.exception("persistence: threat memory check failed for %s", self._session_id)
            await self._db.rollback()
            return []

    def build_known_threat_signals(self) -> list[ThreatSignal]:
        """Turn every known-threat match found so far this session into a
        real, additional `ThreatSignal` — Phase 8 gap #4/#5: the match
        must feed the *existing* risk pipeline as one more piece of
        genuine evidence, not a second score.

        Pure / synchronous / no DB access: safe to call every analysis
        pass. `app.api.routes` appends the result to the `threat_signals`
        list it already has before calling `run_risk_engine()` again, so
        the *same* deterministic Risk Engine — not a new one — produces
        an updated `RiskResult` that reflects this session having been
        recognized as similar to a previously observed threat.

        A match whose stored `category` isn't a valid `ThreatCategory`
        member (e.g. a `Threat` row created by seed data with a
        `SecurityCategory` value instead) is skipped rather than guessed
        at — better to under-enrich than to fabricate a category.
        """
        signals: list[ThreatSignal] = []
        for match in self._known_threat_matches:
            try:
                category = ThreatCategory(match["category"])
            except ValueError:
                logger.debug(
                    "persistence: threat %s has a category (%r) that isn't a "
                    "valid ThreatCategory; skipping it for risk-signal feed.",
                    match["threat_id"], match["category"],
                )
                continue
            signals.append(
                ThreatSignal(
                    category=category,
                    indicator="known_threat_match",
                    evidence=(
                        f"This session's signals match a previously observed "
                        f"threat, '{match['title']}' (seen {match['occurrence_count']} "
                        f"time(s) before)."
                    ),
                    confidence=match["match_score"],
                    source="threat_memory",
                    metadata={
                        "threat_id": match["threat_id"],
                        "occurrence_count": match["occurrence_count"],
                        "matched_patterns": match["matched_patterns"],
                    },
                    timestamp=datetime.now(timezone.utc),
                )
            )
        return signals

    async def maybe_promote_threat(self) -> str | None:
        """Deterministic threat-promotion policy (Phase 8 gap #6), run
        once at session finalization — never per transcript chunk.

        Promotes only when:
          * this session's most recent risk severity was HIGH or CRITICAL, and
          * evidence was SUFFICIENT (not PARTIAL/INSUFFICIENT), and
          * the session actually produced at least one structured signal
            or category to recognize it by later.

        Before creating a new `Threat`, checks for an existing *active*
        threat with an identical indicator signature (gap #7) — if found,
        records an occurrence against it instead of creating a duplicate.

        Returns the resulting threat id (new or pre-existing) as a str,
        or None if the session didn't qualify. Never raises.
        """
        if self._last_severity not in _PROMOTABLE_SEVERITIES:
            return None
        if self._last_evidence_state not in _PROMOTABLE_EVIDENCE_STATES:
            return None
        if not self._signal_types and not self._categories:
            return None

        try:
            signature = SessionSignature(
                signal_types=frozenset(self._signal_types),
                categories=frozenset(self._categories),
            )

            existing = await threat_memory_repo.find_equivalent_active_threat(
                self._db, signature
            )
            if existing is not None:
                await threat_memory_repo.record_occurrence(
                    self._db, threat_id=existing.id, session_id=self._session_id
                )
                await self._db.commit()
                return str(existing.id)

            category = sorted(self._threat_categories)[0] if self._threat_categories else "unknown"
            threat = await threat_memory_repo.create_threat_from_session(
                self._db,
                signature=signature,
                category=category,
                severity=self._last_severity,
                confidence=self._last_confidence if self._last_confidence is not None else 0.5,
                title=f"Auto-promoted threat ({category})",
                description=(
                    f"Promoted at session finalization for session "
                    f"{self._session_id}: severity={self._last_severity}, "
                    f"categories={sorted(self._categories)}, "
                    f"signal_types={sorted(self._signal_types)}."
                ),
            )
            await self._db.commit()
            return str(threat.id)
        except Exception:
            logger.exception("persistence: threat promotion failed for %s", self._session_id)
            await self._db.rollback()
            return None

    # -- internals -----------------------------------------------------

    async def _safe(self, coro) -> None:
        try:
            await coro
        except Exception:
            logger.exception("persistence: write failed for session %s", self._session_id)
