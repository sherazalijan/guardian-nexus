"""Phase 5 — deterministic intervention rules.

No LLMs, no external APIs, no randomness. Each rule is a plain predicate
over a small `RuleContext` snapshot (risk score, the set of voice-signal
types seen, and how many urgency signals have fired). Rules are checked
in order, most severe first, and the first match wins -- this is what
makes "multiple scam indicators" or "repeated pressure tactics" escalate
to CRITICAL ahead of a narrower WARNING rule that would otherwise also
match.

Messages are short, plain-language, and non-technical per the Phase 5
spec's "suitable for seniors" requirement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.models.intervention_engine import InterventionLevel
from app.models.voice_intelligence import VoiceSignalType

_T = VoiceSignalType


@dataclass(frozen=True)
class RuleContext:
    risk_score: float
    signal_types: frozenset[VoiceSignalType]
    urgency_count: int
    pattern_types: frozenset[str]


@dataclass(frozen=True)
class InterventionRule:
    name: str
    level: InterventionLevel
    title: str
    message: str
    predicate: Callable[[RuleContext], bool]


# --- CRITICAL -----------------------------------------------------------

def _multiple_indicators_critical(ctx: RuleContext) -> bool:
    return len(ctx.signal_types) >= 3 and ctx.risk_score >= 85


def _repeated_pressure_critical(ctx: RuleContext) -> bool:
    return ctx.urgency_count >= 2 and _T.URGENCY_PRESSURE in ctx.signal_types


def _remote_access_critical(ctx: RuleContext) -> bool:
    return _T.REMOTE_ACCESS_REQUEST in ctx.signal_types and ctx.risk_score >= 85


# --- HIGH_RISK ------------------------------------------------------------

def _bank_impersonation_high(ctx: RuleContext) -> bool:
    return _T.AUTHORITY_IMPERSONATION in ctx.signal_types and ctx.risk_score >= 70


def _crypto_scam_high(ctx: RuleContext) -> bool:
    return _T.CRYPTO_REQUEST in ctx.signal_types and ctx.risk_score >= 70


def _gift_card_scam_high(ctx: RuleContext) -> bool:
    return _T.GIFT_CARD_REQUEST in ctx.signal_types and ctx.risk_score >= 70


def _remote_access_high(ctx: RuleContext) -> bool:
    return _T.REMOTE_ACCESS_REQUEST in ctx.signal_types and ctx.risk_score >= 70


def _generic_high_risk(ctx: RuleContext) -> bool:
    return ctx.risk_score >= 70


# --- WARNING ----------------------------------------------------------------

def _otp_warning(ctx: RuleContext) -> bool:
    return _T.SENSITIVE_INFORMATION_REQUEST in ctx.signal_types and ctx.risk_score >= 50


def _generic_warning(ctx: RuleContext) -> bool:
    return ctx.risk_score >= 50


INTERVENTION_RULES: tuple[InterventionRule, ...] = (
    # Critical -- checked first so a severe combination always wins.
    InterventionRule(
        name="multiple_indicators_critical",
        level=InterventionLevel.CRITICAL,
        title="Critical Fraud Risk",
        message="Critical fraud indicators detected. Avoid sending money or sensitive information.",
        predicate=_multiple_indicators_critical,
    ),
    InterventionRule(
        name="repeated_pressure_critical",
        level=InterventionLevel.CRITICAL,
        title="High-Pressure Tactics Detected",
        message="This caller is using repeated pressure tactics. End the call and verify independently.",
        predicate=_repeated_pressure_critical,
    ),
    InterventionRule(
        name="remote_access_critical",
        level=InterventionLevel.CRITICAL,
        title="Remote Access Scam",
        message="Do not allow remote access to your device. Hang up immediately.",
        predicate=_remote_access_critical,
    ),
    # High risk
    InterventionRule(
        name="bank_impersonation_high",
        level=InterventionLevel.HIGH_RISK,
        title="Potential Bank Impersonation",
        message="This caller may be impersonating a bank. Hang up and call your bank directly using the number on your card.",
        predicate=_bank_impersonation_high,
    ),
    InterventionRule(
        name="crypto_scam_high",
        level=InterventionLevel.HIGH_RISK,
        title="Cryptocurrency Scam Risk",
        message="High scam risk detected. Do not send cryptocurrency to this caller.",
        predicate=_crypto_scam_high,
    ),
    InterventionRule(
        name="gift_card_scam_high",
        level=InterventionLevel.HIGH_RISK,
        title="Gift Card Scam Risk",
        message="Legitimate organizations never ask for payment in gift cards. Do not buy or share gift card codes.",
        predicate=_gift_card_scam_high,
    ),
    InterventionRule(
        name="remote_access_high",
        level=InterventionLevel.HIGH_RISK,
        title="Remote Access Request",
        message="Be cautious about giving remote access to your device.",
        predicate=_remote_access_high,
    ),
    InterventionRule(
        name="generic_high_risk",
        level=InterventionLevel.HIGH_RISK,
        title="High Scam Risk",
        message="High scam risk detected. End the call and verify independently.",
        predicate=_generic_high_risk,
    ),
    # Warning
    InterventionRule(
        name="otp_warning",
        level=InterventionLevel.WARNING,
        title="Potential OTP Scam",
        message="Do not share verification codes, PINs, or passwords with callers.",
        predicate=_otp_warning,
    ),
    InterventionRule(
        name="generic_warning",
        level=InterventionLevel.WARNING,
        title="Suspicious Call",
        message="This call shows signs of a scam. Proceed with caution.",
        predicate=_generic_warning,
    ),
)
