# Guardian Nexus — WebSocket API Contract

The Guardian Nexus backend broadcasts real-time threat intelligence and analysis to connected frontend clients via a WebSocket endpoint at `/ws/audio`.

## Connection Flow
1. Client connects to `/ws/audio`.
2. Client can immediately send binary `audio/webm` frames to the server.
3. Server broadcasts a `connected` JSON event to confirm the stream is open.
4. Server continually broadcasts the following JSON event types as analysis occurs.

---

## Event Payload Reference

All messages from the server are JSON objects containing a required `type` field.

### 1. `connected`
Indicates successful downstream connection to the AssemblyAI transcription service.
```json
{
  "type": "connected"
}
```

### 2. `transcript`
A chunk of transcribed speech.
- `text` (string): The spoken text.
- `is_final` (boolean): `true` if the sentence is complete.
- `confidence` (float): Provider confidence level.
```json
{
  "type": "transcript",
  "text": "Hello, this is your bank.",
  "is_final": true,
  "confidence": 0.95
}
```

### 3. `voice_signal`
A specific behavioral or social-engineering signal detected in the speaker's voice/language.
- `category` (string): e.g., "social_engineering", "urgency".
- `signal_type` (string): Specific tactic, e.g., "authority_impersonation".
- `confidence` (float): AI detection confidence.
- `evidence` (string): Extract of the transcript triggering the signal.
```json
{
  "type": "voice_signal",
  "category": "social_engineering",
  "signal_type": "authority_impersonation",
  "confidence": 0.92,
  "evidence": "This is your bank's fraud department."
}
```

### 4. `voice_pattern`
A broader pattern synthesized from multiple `voice_signal` events.
```json
{
  "type": "voice_pattern",
  "name": "phishing_attempt",
  "severity": "high",
  "signals": ["authority_impersonation", "urgency"],
  "evidence": [...]
}
```

### 5. `risk`
The global risk assessment score for the current session.
- `score` (integer): 0-100 risk score.
- `severity` (string): "low", "medium", "high", "critical".
- `evidence_state` (string): "insufficient", "partial", "sufficient".
- `risk_factors` (array): Contributing factors and their weight.
```json
{
  "type": "risk",
  "score": 85,
  "severity": "high",
  "evidence_state": "sufficient",
  "risk_factors": [
    {
      "name": "OTP Request",
      "description": "Caller asked for verification code",
      "contribution": 0.6
    }
  ],
  "recommended_action": "escalate"
}
```

### 6. `protection`
An event representing a step in the protection pipeline (e.g., risk escalation, threat detection).
```json
{
  "type": "protection",
  "event_type": "risk_escalation",
  "severity": "high",
  "details": "Risk elevated due to OTP request."
}
```

### 7. `evidence`
Extracted entities or specific statements that the Risk Engine considers suspicious.
```json
{
  "type": "evidence",
  "category": "sensitive_data_request",
  "content": "read me the 6 digit code",
  "confidence": 0.98
}
```

### 8. `intervention`
Actionable interventions recommended or enforced by the system.
- `intervention_id` (string): Unique ID for acknowledgement.
- `priority` (string): "low", "medium", "high", "critical".
- `reason` (string): Why it was triggered.
```json
{
  "type": "intervention",
  "intervention_id": "inv_123",
  "priority": "critical",
  "status": "pending",
  "reason": "OTP Theft Attempt Detected",
  "recommended_action": "Do not share your code. Hang up immediately."
}
```

### 9. `guardian_alert`
System-level alerts representing critical states or broad session changes.
```json
{
  "type": "guardian_alert",
  "level": "CRITICAL",
  "status": "ACTIVE",
  "message": "Potential Account Compromise",
  "source": "Intervention Engine"
}
```

### 10. `known_threat_match`
Triggered by the Threat Memory engine when the current session matches a previously encountered threat.
```json
{
  "type": "known_threat_match",
  "threat_id": "th_456",
  "category": "bank_impersonation",
  "severity": "critical",
  "confidence": 0.95,
  "matched_indicators": ["authority_impersonation", "otp_request"],
  "previous_occurrences": 3,
  "message": "This interaction resembles a known threat pattern."
}
```

### 11. `timeline`
Significant events formatted for chronological display.
```json
{
  "type": "timeline",
  "event_type": "risk_escalation",
  "description": "Risk escalated to HIGH",
  "timestamp": "2026-09-28T12:00:00Z"
}
```

### 12. `session_summary`
Broadcast once when the session ends or is disconnected.
```json
{
  "type": "session_summary",
  "final_risk_score": 92,
  "incident_classification": "OTP Theft / Phishing",
  "duration_seconds": 45,
  "summary": "The caller impersonated a bank representative and requested an OTP..."
}
```

### 13. `error`
Broadcast if a pipeline failure occurs.
```json
{
  "type": "error",
  "code": "provider_error",
  "message": "Failed to connect to transcription service."
}
```

---

## Client -> Server Messages
The client can send text messages to interact with active interventions:
```json
{
  "type": "acknowledge_intervention",
  "intervention_id": "inv_123"
}
```
