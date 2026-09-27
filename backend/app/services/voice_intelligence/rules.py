"""Phase 4 — deterministic voice-scam-behavior detection rules.

Mirrors the exact conventions of `app.agents.scam_agent.ScamRule` /
`SCAM_RULES`: a frozen dataclass of regex patterns matched
case-insensitively, plus a confidence and a `ThreatCategory` reused from
the existing enum (`app.models.enums`). This module detects *behavior*
(who the caller claims to be, what pressure they apply, what they ask
for) rather than the specific payment-method / credential keywords
`scam_agent.py` already owns -- the two rule sets are complementary, not
duplicates.

Confidence policy (Phase 4 spec, section 6): deterministic tiers, not a
learned score --
    0.95  exact strong phrase (unambiguous, single-purpose wording)
    0.85  phrase family match (a recognized variant of a strong phrase)
    0.65  weaker / more generic phrasing that needs corroboration
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import ThreatCategory, ThreatSeverity
from app.models.voice_intelligence import VoiceSignalType

VOICE_INTELLIGENCE_SOURCE = "voice-intelligence-agent"


@dataclass(frozen=True)
class VoiceRule:
    """A single behavioral voice-scam detection rule."""

    name: str
    signal_type: VoiceSignalType
    category: ThreatCategory
    severity: ThreatSeverity
    patterns: tuple[str, ...]
    confidence: float
    description: str


VOICE_RULES: tuple[VoiceRule, ...] = (
    # --- Authority / impersonation -------------------------------------
    VoiceRule(
        name="bank_authority_claim",
        signal_type=VoiceSignalType.AUTHORITY_IMPERSONATION,
        category=ThreatCategory.IMPERSONATION,
        severity=ThreatSeverity.MEDIUM,
        patterns=(
            r"calling from .{0,25}(?:bank|credit union)",
            r"this is .{0,25}(?:bank|credit union)",
            r"bank(?:'s)? (?:security|fraud) (?:team|department)",
        ),
        confidence=0.85,
        description="claimed to be calling from a bank",
    ),
    VoiceRule(
        name="law_enforcement_authority_claim",
        signal_type=VoiceSignalType.AUTHORITY_IMPERSONATION,
        category=ThreatCategory.IMPERSONATION,
        severity=ThreatSeverity.MEDIUM,
        patterns=(
            r"this is (?:the )?police",
            r"calling from .{0,20}(?:police department|law enforcement)",
            r"(?:tax authority|internal revenue|government official)",
        ),
        confidence=0.9,
        description="claimed to be a police, government, or tax authority official",
    ),
    VoiceRule(
        name="delivery_authority_claim",
        signal_type=VoiceSignalType.AUTHORITY_IMPERSONATION,
        category=ThreatCategory.IMPERSONATION,
        severity=ThreatSeverity.MEDIUM,
        patterns=(
            r"calling from .{0,20}(?:delivery|courier|shipping) (?:company|service)",
        ),
        confidence=0.7,
        description="claimed to be a delivery or courier company representative",
    ),
    VoiceRule(
        name="technical_support_impersonation",
        signal_type=VoiceSignalType.TECHNICAL_SUPPORT_IMPERSONATION,
        category=ThreatCategory.IMPERSONATION,
        severity=ThreatSeverity.MEDIUM,
        patterns=(
            r"(?:calling from|this is) .{0,20}tech(?:nical)? support",
            r"your computer is infected",
            r"virus (?:detected|found) on your (?:computer|device)",
        ),
        confidence=0.85,
        description="claimed to be technical/account-security support",
    ),
    VoiceRule(
        name="account_compromise_claim",
        signal_type=VoiceSignalType.ACCOUNT_COMPROMISE_CLAIM,
        category=ThreatCategory.SUSPICIOUS_CALL,
        severity=ThreatSeverity.MEDIUM,
        patterns=(
            r"your account (?:has been|is|was) (?:compromised|hacked|breached)",
            r"(?:unauthorized|suspicious) (?:activity|access|login) on your account",
        ),
        confidence=0.85,
        description="claimed the user's account has been compromised",
    ),
    # --- Urgency / pressure ---------------------------------------------
    VoiceRule(
        name="urgency_deadline",
        signal_type=VoiceSignalType.URGENCY_PRESSURE,
        category=ThreatCategory.SUSPICIOUS_CALL,
        severity=ThreatSeverity.MEDIUM,
        patterns=(
            r"act (?:immediately|right now|now)",
            r"you (?:only )?have (?:a )?(?:few|one|two|three|four|five|six|seven|"
        r"eight|nine|ten|fifteen|twenty|thirty|\d+)\s*minutes",
            r"this is your (?:final|last) warning",
            r"do this (?:right )?now",
        ),
        confidence=0.9,
        description="applied an immediate-action time-pressure deadline",
    ),
    VoiceRule(
        name="urgency_account_closure",
        signal_type=VoiceSignalType.URGENCY_PRESSURE,
        category=ThreatCategory.SUSPICIOUS_CALL,
        severity=ThreatSeverity.MEDIUM,
        patterns=(
            r"your account will be closed",
            r"before it'?s too late",
        ),
        confidence=0.8,
        description="threatened imminent account closure to create urgency",
    ),
    # --- Threat / intimidation -------------------------------------------
    VoiceRule(
        name="legal_threat",
        signal_type=VoiceSignalType.THREAT_INTIMIDATION,
        category=ThreatCategory.FRAUD,
        severity=ThreatSeverity.HIGH,
        patterns=(
            r"legal (?:action|consequences|proceedings)",
            r"you (?:will|could) be arrested",
            r"warrant for your arrest",
        ),
        confidence=0.9,
        description="threatened legal action or arrest",
    ),
    VoiceRule(
        name="suspension_threat",
        signal_type=VoiceSignalType.THREAT_INTIMIDATION,
        category=ThreatCategory.FRAUD,
        severity=ThreatSeverity.MEDIUM,
        patterns=(
            r"(?:service|account) (?:will be|is) terminated",
            r"financial penalt(?:y|ies)",
        ),
        confidence=0.75,
        description="threatened service termination or financial penalties",
    ),
    # --- Sensitive information request -----------------------------------
    VoiceRule(
        name="otp_pin_request",
        signal_type=VoiceSignalType.SENSITIVE_INFORMATION_REQUEST,
        category=ThreatCategory.PHISHING,
        severity=ThreatSeverity.HIGH,
        patterns=(
            r"(?:read|tell|give) me the (?:code|otp|pin)",
            r"\botp\b",
            r"verification code",
            r"\bpin\b (?:number|code)?",
            r"security answer",
        ),
        confidence=0.9,
        description="requested an OTP, PIN, or verification code",
    ),
    VoiceRule(
        name="credential_request",
        signal_type=VoiceSignalType.SENSITIVE_INFORMATION_REQUEST,
        category=ThreatCategory.PHISHING,
        severity=ThreatSeverity.HIGH,
        patterns=(
            r"your password",
            r"card (?:number|details)",
            r"bank account (?:number|credentials)",
        ),
        confidence=0.85,
        description="requested passwords or account/card credentials",
    ),
    # --- Payment request ---------------------------------------------------
    VoiceRule(
        name="gift_card_request",
        signal_type=VoiceSignalType.GIFT_CARD_REQUEST,
        category=ThreatCategory.FRAUD,
        severity=ThreatSeverity.HIGH,
        patterns=(
            r"gift card",
            r"itunes card",
            r"google play card",
            r"steam card",
        ),
        confidence=0.9,
        description="asked for payment via gift cards",
    ),
    VoiceRule(
        name="crypto_request",
        signal_type=VoiceSignalType.CRYPTO_REQUEST,
        category=ThreatCategory.FRAUD,
        severity=ThreatSeverity.HIGH,
        patterns=(
            r"\bbitcoin\b",
            r"\bcrypto(?:currency)?\b",
            r"crypto wallet",
        ),
        confidence=0.9,
        description="asked for a cryptocurrency transfer",
    ),
    VoiceRule(
        name="generic_payment_request",
        signal_type=VoiceSignalType.PAYMENT_REQUEST,
        category=ThreatCategory.FRAUD,
        severity=ThreatSeverity.MEDIUM,
        patterns=(
            r"wire transfer",
            r"payment link",
            r"bank transfer",
        ),
        confidence=0.75,
        description="requested an unusual payment method",
    ),
    # --- Remote access ------------------------------------------------------
    VoiceRule(
        name="remote_access_request",
        signal_type=VoiceSignalType.REMOTE_ACCESS_REQUEST,
        category=ThreatCategory.MALWARE,
        severity=ThreatSeverity.HIGH,
        patterns=(
            r"remote access",
            r"anydesk",
            r"teamviewer",
            r"share your screen",
            r"take control of your (?:computer|screen|device)",
            r"install this (?:app|application|software)",
        ),
        confidence=0.9,
        description="requested remote access or screen-sharing control",
    ),
    # --- Secrecy / isolation --------------------------------------------
    VoiceRule(
        name="secrecy_isolation",
        signal_type=VoiceSignalType.SECRECY_ISOLATION,
        category=ThreatCategory.SUSPICIOUS_CALL,
        severity=ThreatSeverity.MEDIUM,
        patterns=(
            r"do(?:n'?t| not) tell anyone",
            r"keep this confidential",
            r"do(?:n'?t| not) (?:hang up|close the call)",
            r"stay on the line",
            r"do(?:n'?t| not) (?:talk|speak) to your family",
        ),
        confidence=0.85,
        description="instructed the user to keep the call secret or stay on the line",
    ),
    # --- Verification bypass -----------------------------------------------
    VoiceRule(
        name="verification_bypass",
        signal_type=VoiceSignalType.VERIFICATION_BYPASS,
        category=ThreatCategory.SUSPICIOUS_CALL,
        severity=ThreatSeverity.MEDIUM,
        patterns=(
            r"do(?:n'?t| not) call the official number",
            r"do(?:n'?t| not) (?:visit|go to) the branch",
            r"do(?:n'?t| not) contact customer support",
            r"use this number instead",
        ),
        confidence=0.85,
        description="discouraged independent verification through official channels",
    ),
    # --- Emotional manipulation ----------------------------------------
    VoiceRule(
        name="emotional_manipulation",
        signal_type=VoiceSignalType.EMOTIONAL_MANIPULATION,
        category=ThreatCategory.SUSPICIOUS_CALL,
        severity=ThreatSeverity.LOW,
        patterns=(
            r"you (?:need|have) to trust me",
            r"i'?m only trying to help you",
            r"don'?t panic, just do (?:this|what i say)",
        ),
        confidence=0.65,
        description="used reassurance-then-request emotional pressure",
    ),
)
