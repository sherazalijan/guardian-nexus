# Guardian Nexus — Protection Layer (Phase 1)

## Architecture

```
audio → transcript (AssemblyAI) → rule-based scam agent → deterministic risk engine
      → ProtectionService → protection events + timeline events → WebSocket → frontend
```

`ProtectionService` (`app/services/protection/service.py`) is the only new
logic layer. It does **not** detect threats and does **not** calculate
risk — both remain the job of `app.agents.scam_agent` and
`app.services.risk_engine.run_risk_engine`. It only interprets that
existing output for user-facing intervention: dedup, escalation
detection, session state, timeline, and summary.

Session state is in-memory only, one `ProtectionService` per WebSocket
connection. No database.

## Protection event schema (`app/models/protection.py`)

```python
class ProtectionEvent(BaseModel):
    event_id: UUID
    session_id: str
    timestamp: datetime
    event_type: ProtectionEventType  # threat_detected | risk_escalated |
                                      # warning | critical_alert |
                                      # sensitive_information_detected |
                                      # recommended_action | session_summary
    severity: ThreatSeverity         # low | medium | high | critical
    risk_score: float                # 0-100
    title: str
    message: str
    category: SecurityCategory       # otp_theft | bank_impersonation |
                                      # account_compromise | urgent_payment |
                                      # gift_card_scam | cryptocurrency_scam |
                                      # remote_access_scam | phishing |
                                      # credential_theft | social_engineering |
                                      # unknown
    evidence: list[str]
    recommended_action: str
    confidence: float                # 0-1
```

`TimelineEvent` and `SessionSummary` are structured siblings in the same
file — see the module docstring for field lists.

## WebSocket message types (`/ws/audio`)

Original (unchanged): `connected`, `transcript`, `error`.

New, additive:

| type              | when                                                   |
|-------------------|---------------------------------------------------------|
| `risk`            | after every *final* transcript segment, always          |
| `protection`      | 0+ per final segment — one per new threat/escalation     |
| `timeline`        | 0+ per final segment — structured log entries            |
| `session_summary` | once, best-effort, right before the socket closes        |

Example `protection` frame:

```json
{
  "type": "protection",
  "data": {
    "event_type": "critical_alert",
    "severity": "critical",
    "risk_score": 92,
    "title": "Critical alert issued",
    "message": "Risk level increased from high to critical (score 92).",
    "category": "otp_theft",
    "evidence": ["otp_theft"],
    "recommended_action": "End the call immediately and verify through an official channel...",
    "confidence": 0.85
  }
}
```

Analysis runs on the full transcript accumulated so far in the session
(not just the latest fragment), so multi-turn evidence (e.g. "bank
impersonation" in turn 1 + "OTP request" in turn 2) still aggregates into
one risk score. A failure in analysis is reported as
`{"type": "error", "error": {"code": "analysis_failed", ...}}` and does
**not** close the connection.

## Risk escalation behavior

`ProtectionState` is derived directly from `RiskResult.severity` (never
recalculated independently):

| severity | state      |
|----------|------------|
| low      | monitoring |
| medium   | suspicious |
| high     | high_risk  |
| critical | critical   |

A `risk_escalated` / `warning` / `critical_alert` protection event fires
only on a **strict severity increase** vs. the previous analysis call for
that session (low→medium, medium→high, high→critical). Severity decreases
never emit an event, but `highest_severity` / `highest_risk_score` are
still tracked for the session summary.

## Duplicate suppression

Each `threat_detected` event is deduplicated per session on
`(SecurityCategory, normalized indicator)`. Once "OTP theft" has been
surfaced for a session, it will not be surfaced again even if the same
rule matches again in a later transcript fragment — but the recommended
action, risk score, and timeline keep updating.

## Session summary

Built entirely from in-memory state, no LLM:

```python
class SessionSummary(BaseModel):
    session_id: str
    session_started_at: datetime | None
    session_ended_at: datetime | None
    duration_seconds: float | None
    highest_risk_score: float
    final_risk_score: float
    highest_severity: ThreatSeverity
    detected_categories: list[SecurityCategory]
    detected_signals: list[str]
    warning_count: int
    critical_alert_count: int
    recommended_final_action: str
```
