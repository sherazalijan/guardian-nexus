"""Phase 4 — Voice Scam Intelligence models.

These models describe *behavioral* signals extracted from a live call
transcript (who is claiming to be whom, what pressure is being applied,
what is being requested) and deterministic multi-signal patterns built
from them.

Deliberately reuses the *existing* vocabulary rather than inventing a
parallel one:

- `VoiceSignal.category` is `app.models.enums.ThreatCategory` -- the same
  enum `ThreatSignal.category` already uses. No new category enum.
- `VoiceSignal.severity` is `app.models.enums.ThreatSeverity` -- a
  descriptive tag only. It is NOT fed into risk scoring; the existing
  Risk Engine (`app.services.risk_engine.run_risk_engine`) remains the
  sole source of the 0-100 score. See `app.services.voice_intelligence.bridge`
  for how a `VoiceSignal` becomes a `ThreatSignal` for that engine.
- `VoicePattern` never carries a 0-100 score, only a 0.0-1.0 confidence,
  to avoid even the appearance of a second risk scale.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.models.enums import ThreatCategory, ThreatSeverity


class VoiceSignalType(StrEnum):
    """Behavioral scam signal types (Phase 4 spec, section 2)."""

    AUTHORITY_IMPERSONATION = "authority_impersonation"
    TECHNICAL_SUPPORT_IMPERSONATION = "technical_support_impersonation"
    ACCOUNT_COMPROMISE_CLAIM = "account_compromise_claim"
    URGENCY_PRESSURE = "urgency_pressure"
    THREAT_INTIMIDATION = "threat_intimidation"
    SENSITIVE_INFORMATION_REQUEST = "sensitive_information_request"
    PAYMENT_REQUEST = "payment_request"
    GIFT_CARD_REQUEST = "gift_card_request"
    CRYPTO_REQUEST = "crypto_request"
    REMOTE_ACCESS_REQUEST = "remote_access_request"
    SECRECY_ISOLATION = "secrecy_isolation"
    VERIFICATION_BYPASS = "verification_bypass"
    EMOTIONAL_MANIPULATION = "emotional_manipulation"


class VoiceSignal(BaseModel):
    """A single structured behavioral signal extracted from a transcript."""

    signal_id: UUID = Field(default_factory=uuid4)
    session_id: str = Field(min_length=1)
    signal_type: VoiceSignalType
    category: ThreatCategory
    confidence: float = Field(ge=0.0, le=1.0)
    severity: ThreatSeverity
    evidence_text: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = Field(min_length=1)
    metadata: dict[str, object] = Field(default_factory=dict)


class VoicePattern(BaseModel):
    """A deterministic multi-signal correlation finding.

    Represents *how* a caller is combining behaviors (e.g. authority +
    urgency + an OTP request), not a second risk score.
    """

    pattern_id: UUID = Field(default_factory=uuid4)
    session_id: str = Field(min_length=1)
    pattern_type: str = Field(min_length=1)
    signals: list[VoiceSignalType] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VoiceIntelligenceSnapshot(BaseModel):
    """Everything the voice-intelligence layer has produced for a session
    so far -- used for the `voice_intelligence` WebSocket frame."""

    session_id: str = Field(min_length=1)
    signals: list[VoiceSignal] = Field(default_factory=list)
    patterns: list[VoicePattern] = Field(default_factory=list)
