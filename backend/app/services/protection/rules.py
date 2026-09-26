"""Deterministic protection rules: signal -> category -> user-facing copy.

This module maps output from the *existing* scam detector
(`app.models.threat.ThreatSignal`, produced by `app.agents.scam_agent` or
`app.agents.scam_detection_agent`) into the user-facing vocabulary defined
in `app.models.protection`. It does not detect anything itself and it is
not a second scam detector -- the existing detection system remains the
single source of truth for *whether* something is suspicious; this module
only decides how to *describe* what was already detected.

Everything here is a plain lookup table so it stays deterministic and
trivially testable.
"""

from __future__ import annotations

from app.models.enums import RecommendedAction, ThreatCategory
from app.models.protection import SecurityCategory
from app.models.threat import ThreatSignal
from app.services.normalization import normalize_indicator

# Maps the rule-based scam agent's `ThreatSignal.indicator` values
# (`app.agents.scam_agent.SCAM_RULES`) directly onto a `SecurityCategory`.
# This is the primary, most precise classification path.
_INDICATOR_CATEGORY_MAP: dict[str, SecurityCategory] = {
    "otp_request": SecurityCategory.OTP_THEFT,
    "bank_impersonation": SecurityCategory.BANK_IMPERSONATION,
    "urgent_payment_request": SecurityCategory.URGENT_PAYMENT,
    "gift_card_request": SecurityCategory.GIFT_CARD_SCAM,
    "crypto_transfer_request": SecurityCategory.CRYPTOCURRENCY_SCAM,
    "remote_access_request": SecurityCategory.REMOTE_ACCESS_SCAM,
    "account_suspension_threat": SecurityCategory.ACCOUNT_COMPROMISE,
    "credential_theft": SecurityCategory.CREDENTIAL_THEFT,
    "social_engineering": SecurityCategory.SOCIAL_ENGINEERING,
}

# Fallback classification for signals whose `indicator` isn't recognized
# above (e.g. produced by the advanced/LLM-backed pipeline), keyed by the
# detector's `ThreatCategory` instead.
_THREAT_CATEGORY_FALLBACK_MAP: dict[ThreatCategory, SecurityCategory] = {
    ThreatCategory.SCAM: SecurityCategory.SOCIAL_ENGINEERING,
    ThreatCategory.PHISHING: SecurityCategory.PHISHING,
    ThreatCategory.IMPERSONATION: SecurityCategory.BANK_IMPERSONATION,
    ThreatCategory.MALWARE: SecurityCategory.REMOTE_ACCESS_SCAM,
    ThreatCategory.FRAUD: SecurityCategory.URGENT_PAYMENT,
    ThreatCategory.SUSPICIOUS_CALL: SecurityCategory.ACCOUNT_COMPROMISE,
    ThreatCategory.MALICIOUS_LINK: SecurityCategory.PHISHING,
    ThreatCategory.UNKNOWN: SecurityCategory.UNKNOWN,
}

TITLES: dict[SecurityCategory, str] = {
    SecurityCategory.OTP_THEFT: "Possible OTP theft attempt",
    SecurityCategory.BANK_IMPERSONATION: "Possible bank impersonation",
    SecurityCategory.ACCOUNT_COMPROMISE: "Account compromise threat detected",
    SecurityCategory.URGENT_PAYMENT: "Urgent payment pressure detected",
    SecurityCategory.GIFT_CARD_SCAM: "Gift card payment request detected",
    SecurityCategory.CRYPTOCURRENCY_SCAM: "Cryptocurrency transfer request detected",
    SecurityCategory.REMOTE_ACCESS_SCAM: "Remote access request detected",
    SecurityCategory.PHISHING: "Phishing attempt detected",
    SecurityCategory.CREDENTIAL_THEFT: "Credential theft attempt detected",
    SecurityCategory.SOCIAL_ENGINEERING: "Social engineering tactics detected",
    SecurityCategory.UNKNOWN: "Suspicious activity detected",
}

MESSAGES: dict[SecurityCategory, str] = {
    SecurityCategory.OTP_THEFT: (
        "The caller is requesting a one-time password or verification code."
    ),
    SecurityCategory.BANK_IMPERSONATION: (
        "The caller is claiming to represent your bank or its "
        "security/fraud department."
    ),
    SecurityCategory.ACCOUNT_COMPROMISE: (
        "The caller is claiming your account has been compromised, "
        "locked, or suspended."
    ),
    SecurityCategory.URGENT_PAYMENT: (
        "The caller is pressuring you to make an urgent or immediate payment."
    ),
    SecurityCategory.GIFT_CARD_SCAM: (
        "The caller is asking you to pay using gift cards, which is a "
        "common scam payment method."
    ),
    SecurityCategory.CRYPTOCURRENCY_SCAM: (
        "The caller is asking you to transfer cryptocurrency."
    ),
    SecurityCategory.REMOTE_ACCESS_SCAM: (
        "The caller is asking for remote access to your device."
    ),
    SecurityCategory.PHISHING: (
        "The caller is using phishing tactics to obtain personal information."
    ),
    SecurityCategory.CREDENTIAL_THEFT: (
        "The caller is attempting to obtain your login credentials or passwords."
    ),
    SecurityCategory.SOCIAL_ENGINEERING: (
        "The caller is using social-engineering pressure tactics."
    ),
    SecurityCategory.UNKNOWN: (
        "Suspicious language was detected in this conversation."
    ),
}

# Deterministic, testable recommended-action copy per user-facing category.
RECOMMENDED_ACTIONS: dict[SecurityCategory, str] = {
    SecurityCategory.OTP_THEFT: (
        "Do not share your OTP. Contact your bank using the official number."
    ),
    SecurityCategory.BANK_IMPERSONATION: (
        "End the call and contact your bank through an official channel."
    ),
    SecurityCategory.ACCOUNT_COMPROMISE: (
        "Do not provide credentials or verification codes. Verify independently."
    ),
    SecurityCategory.URGENT_PAYMENT: (
        "Do not make any payment under pressure. Verify the request "
        "independently before acting."
    ),
    SecurityCategory.GIFT_CARD_SCAM: (
        "Do not purchase or send gift cards as payment."
    ),
    SecurityCategory.CRYPTOCURRENCY_SCAM: (
        "Do not transfer cryptocurrency based on an unsolicited call."
    ),
    SecurityCategory.REMOTE_ACCESS_SCAM: (
        "Do not install remote-access software or give the caller "
        "control of your device."
    ),
    SecurityCategory.PHISHING: (
        "Do not click links or share personal information. "
        "Verify the sender independently."
    ),
    SecurityCategory.CREDENTIAL_THEFT: (
        "Do not share passwords or login credentials with the caller."
    ),
    SecurityCategory.SOCIAL_ENGINEERING: (
        "Be cautious of pressure tactics. Take time to verify the "
        "caller's identity independently."
    ),
    SecurityCategory.UNKNOWN: (
        "Stay cautious and verify the caller's identity through an "
        "official channel before sharing any information."
    ),
}

# Generic, severity-driven copy used for session-level events (risk
# escalation / warnings / critical alerts / session summaries) that are not
# tied to a single detected category. Reuses the existing
# `RecommendedAction` enum produced by the Risk Engine rather than
# duplicating its policy.
RISK_ACTION_TEXT: dict[RecommendedAction, str] = {
    RecommendedAction.IGNORE: "No action needed at this time.",
    RecommendedAction.MONITOR: "Continue monitoring the call for suspicious activity.",
    RecommendedAction.WARN: (
        "Proceed with caution and verify the caller's identity independently."
    ),
    RecommendedAction.BLOCK: (
        "Consider ending the call and verifying independently before "
        "taking any action."
    ),
    RecommendedAction.ESCALATE: (
        "End the call immediately and verify through an official channel. "
        "Do not share any personal or financial information."
    ),
}


def classify_signal(signal: ThreatSignal) -> SecurityCategory:
    """Map a threat signal onto a user-facing `SecurityCategory`.

    Tries the precise indicator-name mapping first (matches the
    rule-based scam agent's exact rule names), then falls back to the
    signal's `ThreatCategory`, and finally to `SecurityCategory.UNKNOWN`.
    """
    indicator_key = normalize_indicator(signal.indicator).replace(" ", "_")

    if indicator_key in _INDICATOR_CATEGORY_MAP:
        return _INDICATOR_CATEGORY_MAP[indicator_key]

    return _THREAT_CATEGORY_FALLBACK_MAP.get(signal.category, SecurityCategory.UNKNOWN)


def title_for(category: SecurityCategory) -> str:
    """Deterministic event title for a user-facing category."""
    return TITLES.get(category, TITLES[SecurityCategory.UNKNOWN])


def message_for(category: SecurityCategory) -> str:
    """Deterministic event message for a user-facing category."""
    return MESSAGES.get(category, MESSAGES[SecurityCategory.UNKNOWN])


def recommended_action_for(category: SecurityCategory) -> str:
    """Deterministic recommended action text for a user-facing category."""
    return RECOMMENDED_ACTIONS.get(category, RECOMMENDED_ACTIONS[SecurityCategory.UNKNOWN])


def risk_action_text(action: RecommendedAction) -> str:
    """Deterministic recommended-action text for a Risk Engine action."""
    return RISK_ACTION_TEXT.get(action, RISK_ACTION_TEXT[RecommendedAction.MONITOR])
