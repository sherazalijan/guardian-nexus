from enum import StrEnum


class ThreatSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatCategory(StrEnum):
    SCAM = "scam"
    PHISHING = "phishing"
    IMPERSONATION = "impersonation"
    MALWARE = "malware"
    FRAUD = "fraud"
    SUSPICIOUS_CALL = "suspicious_call"
    MALICIOUS_LINK = "malicious_link"
    UNKNOWN = "unknown"


class RecommendedAction(StrEnum):
    IGNORE = "ignore"
    MONITOR = "monitor"
    WARN = "warn"
    BLOCK = "block"
    ESCALATE = "escalate"


class EventType(StrEnum):
    TRANSCRIPT = "transcript"
    RISK = "risk"
    THREAT = "threat"
    ALERT = "alert"
