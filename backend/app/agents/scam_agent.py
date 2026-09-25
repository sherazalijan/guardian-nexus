"""Rule-based (offline, no-API-key) scam detection agent.

This runs deterministic keyword/pattern matching over a transcript to
flag common scam indicators. Unlike `app.agents.scam_detection_agent`
(the advanced pipeline's node, which calls out to an LLM provider), this
agent requires no LLM, no external API key, and no network access -- it
is the entry node of Guardian Nexus's offline pipeline (see
`app.agents.graph.build_rule_based_guardian_graph`).

Each matched rule becomes a `ThreatSignal`, using the exact same model
the advanced pipeline produces, so downstream consumers -- most notably
the existing deterministic risk engine -- don't need to know which
pipeline generated the evidence.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime

from app.agents.rule_based_state import GuardianState
from app.models.enums import ThreatCategory
from app.models.threat import ThreatSignal

logger = logging.getLogger(__name__)

#: `ThreatSignal.source` value used for every signal this agent produces.
RULE_SOURCE = "rule-based-scam-agent"

#: `category` / `scam_score` returned for a transcript with no rule matches.
NO_MATCH_CATEGORY = ThreatCategory.UNKNOWN.value


@dataclass(frozen=True)
class ScamRule:
    """A single keyword/pattern-based scam detection rule."""

    name: str
    category: ThreatCategory
    patterns: tuple[str, ...]
    """Regex patterns, matched case-insensitively; any one match is enough."""
    weight: int
    """Contribution to `scam_score` (0-100 scale) if this rule matches."""
    confidence: float
    """Confidence assigned to the resulting `ThreatSignal`, 0.0-1.0."""
    description: str
    """Human-readable fragment used to build the `explanation` string."""


# Covers the scam indicators Guardian Nexus is required to detect without
# any LLM: OTP/verification-code requests, bank impersonation, urgent
# payment requests, gift cards, cryptocurrency transfers, remote access
# requests, and account suspension threats.
SCAM_RULES: tuple[ScamRule, ...] = (
    ScamRule(
        name="otp_request",
        category=ThreatCategory.PHISHING,
        patterns=(
            r"\botp\b",
            r"one[- ]time (?:pass(?:code|word)|code)",
            r"verification code",
            r"security code",
        ),
        weight=30,
        confidence=0.85,
        description="requested a one-time password / verification code",
    ),
    ScamRule(
        name="bank_impersonation",
        category=ThreatCategory.IMPERSONATION,
        patterns=(
            r"\bthis is .{0,20}bank\b",
            r"calling from .{0,20}bank\b",
            r"bank(?:'s)? security (?:team|department)",
            r"fraud department",
        ),
        weight=25,
        confidence=0.75,
        description="claimed to be calling from a bank or its security/fraud department",
    ),
    ScamRule(
        name="urgent_payment_request",
        category=ThreatCategory.FRAUD,
        patterns=(
            r"pay (?:immediately|right away|now|urgently)",
            r"urgent(?:ly)? .{0,20}payment",
            r"failure to pay",
            r"before it'?s too late",
        ),
        weight=20,
        confidence=0.70,
        description="demanded an urgent or immediate payment",
    ),
    ScamRule(
        name="gift_card_request",
        category=ThreatCategory.FRAUD,
        patterns=(
            r"gift card",
            r"itunes card",
            r"google play card",
            r"steam card",
        ),
        weight=35,
        confidence=0.90,
        description="requested payment via gift cards",
    ),
    ScamRule(
        name="crypto_transfer_request",
        category=ThreatCategory.FRAUD,
        patterns=(
            r"\bbitcoin\b",
            r"\bcrypto(?:currency)?\b",
            r"crypto wallet",
            r"\busdt\b",
            r"\bethereum\b",
        ),
        weight=35,
        confidence=0.90,
        description="requested a cryptocurrency transfer",
    ),
    ScamRule(
        name="remote_access_request",
        category=ThreatCategory.MALWARE,
        patterns=(
            r"remote access",
            r"anydesk",
            r"teamviewer",
            r"take control of your (?:computer|screen|device)",
        ),
        weight=30,
        confidence=0.85,
        description="requested remote access to the caller's device",
    ),
    ScamRule(
        name="account_suspension_threat",
        category=ThreatCategory.SUSPICIOUS_CALL,
        patterns=(
            r"account (?:has been|will be|is) (?:locked|frozen|compromised|suspended)",
            r"suspend(?:ed)? .{0,20}account",
        ),
        weight=20,
        confidence=0.70,
        description="threatened account suspension, locking, or compromise",
    ),
)


def _match_rule(rule: ScamRule, transcript: str) -> str | None:
    """Return the first matched pattern's evidence text, or None."""
    for pattern in rule.patterns:
        match = re.search(pattern, transcript, flags=re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def _build_explanation(matches: list[tuple[ScamRule, str]]) -> str:
    """Build a human-readable explanation from the matched rules."""
    if not matches:
        return "No scam indicators detected."

    fragments = [
        f'{rule.description} (matched: "{evidence}")' for rule, evidence in matches
    ]
    return "Detected " + "; ".join(fragments) + "."


def _dominant_category(matches: list[tuple[ScamRule, str]]) -> str:
    """Return the category of the highest-weighted matched rule."""
    if not matches:
        return NO_MATCH_CATEGORY

    top_rule, _ = max(matches, key=lambda pair: pair[0].weight)
    return top_rule.category.value


def _build_threat_signals(
    matches: list[tuple[ScamRule, str]],
    now: datetime,
) -> list[ThreatSignal]:
    """Convert matched rules into `ThreatSignal` objects for the risk engine."""
    return [
        ThreatSignal(
            category=rule.category,
            indicator=rule.name,
            evidence=evidence,
            confidence=rule.confidence,
            source=RULE_SOURCE,
            metadata={"weight": rule.weight},
            timestamp=now,
        )
        for rule, evidence in matches
    ]


async def scam_agent(state: GuardianState) -> GuardianState:
    """Detect common scam indicators in the transcript using fixed rules.

    Populates `scam_score`, `category`, `explanation`, and the
    `threat_signals` bridge field consumed by the risk-engine node.
    Never raises: an unreadable/empty transcript is a valid, zero-risk
    result rather than an error.
    """
    transcript = (state.get("transcript") or "").strip()

    if not transcript:
        logger.info("scam_agent: empty transcript, nothing to evaluate.")
        return {
            **state,
            "scam_score": 0,
            "category": NO_MATCH_CATEGORY,
            "explanation": "Empty transcript; no scam indicators to evaluate.",
            "threat_signals": [],
        }

    matches: list[tuple[ScamRule, str]] = []
    for rule in SCAM_RULES:
        evidence = _match_rule(rule, transcript)
        if evidence is not None:
            matches.append((rule, evidence))

    scam_score = min(sum(rule.weight for rule, _ in matches), 100)
    category = _dominant_category(matches)
    explanation = _build_explanation(matches)
    threat_signals = _build_threat_signals(matches, datetime.now(UTC))

    logger.info(
        "scam_agent: scored %d (%s), %d indicator(s) matched.",
        scam_score,
        category,
        len(matches),
    )

    return {
        **state,
        "scam_score": scam_score,
        "category": category,
        "explanation": explanation,
        "threat_signals": threat_signals,
    }
