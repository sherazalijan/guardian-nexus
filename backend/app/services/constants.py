"""Deterministic Risk Engine policy constants."""

from app.models.enums import ThreatCategory


# Illustrative starting weights.
# These values are Phase 3 policy parameters and must be calibrated
# against representative scenarios before production use.
CATEGORY_WEIGHTS: dict[ThreatCategory, float] = {
    ThreatCategory.SCAM: 50.0,
    ThreatCategory.PHISHING: 55.0,
    ThreatCategory.IMPERSONATION: 45.0,
    ThreatCategory.MALWARE: 70.0,
    ThreatCategory.FRAUD: 60.0,
    ThreatCategory.SUSPICIOUS_CALL: 25.0,
    ThreatCategory.MALICIOUS_LINK: 55.0,
    ThreatCategory.UNKNOWN: 0.0,
}


# Corroboration policy.
CORROBORATION_FACTOR = 0.30
CORROBORATION_DECAY = 0.50
CORROBORATION_CAP = 30.0


# Score limits.
MIN_SCORE = 0.0
MAX_SCORE = 100.0


# Severity boundaries.
LOW_MAX = 29.0
MEDIUM_MAX = 59.0
HIGH_MAX = 79.0