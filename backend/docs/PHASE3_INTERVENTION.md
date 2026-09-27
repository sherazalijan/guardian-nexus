# Phase 3 — Real-Time Intervention

## Purpose
Turns each pass's new `ProtectionEvent`s (from the existing
`ProtectionService`) into a deterministic, actionable on-screen
intervention. Performs no scam classification and no risk scoring --
`title`, `message`, `category`, and `recommended_action` are copied
verbatim from the triggering `ProtectionEvent`.

## Lifecycle
```
ProtectionAnalysisResult.events (from ProtectionService.process())
    -> InterventionPolicyService.decide(analysis)
    -> priority = SEVERITY_TO_PRIORITY[event.severity]   (LOW -> NONE)
    -> NONE -> no intervention
    -> else -> dedup/cooldown check -> suppressed | new Intervention(ACTIVE)
Intervention.status: ACTIVE -> ACKNOWLEDGED -> [ESCALATED] -> RESOLVED | EXPIRED
```
Acknowledging an intervention does not mean the threat is gone: a later,
materially higher-priority event in the same `SecurityCategory` marks the
current intervention `ESCALATED` and a new one is created
(`escalated_from` points back to it).

## Deduplication / cooldown
Keyed by `SecurityCategory` within the session.
- Same or lower priority while a live (`ACTIVE`/`ACKNOWLEDGED`)
  intervention exists for that category -> always suppressed.
- Materially higher priority -> escalates immediately, bypassing cooldown.
- No live intervention, but one was just emitted for that category -> the
  per-priority cooldown window (`COOLDOWN_SECONDS` in `policy.py`) applies
  before an equal-or-lower-priority repeat is allowed through.

## Acknowledgement
`InterventionPolicyService.acknowledge(intervention_id)` returns a
structured `InterventionAckResult` (`success`, `reason`, `status`) --
never raises for unknown/resolved/expired/already-acknowledged
interventions.

## WebSocket events (all additive)
- `intervention` — sent whenever `decide()` produces a new intervention.
- `intervention_ack_result` — sent in response to a client
  `acknowledge_intervention` message.
- `intervention_history` — sent once, best-effort, at session end,
  alongside the existing `session_summary` / `session_intelligence`
  frames.
- `session_summary` gains two additive keys: `intervention_count`,
  `critical_intervention_occurred`.

Client -> server:
```json
{"type": "acknowledge_intervention", "intervention_id": "int_..."}
```

## Session cleanup
`InterventionPolicyService.resolve()` is called from
`_safe_send_session_summary` in `app/api/routes.py`, alongside the
existing `protection_service.end_session()` -- it marks any
`ACTIVE`/`ACKNOWLEDGED` interventions `RESOLVED` for that session only.

## Wiring in routes.py
`app/api/routes.py` was overwritten by `phase3_apply_v2.sh` (backup at
`app/api/routes.py.bak`). Changes vs. Phase 2, all additive:
1. Import and instantiate `InterventionPolicyService(session_id)`
   alongside `ProtectionService`/`SessionIntelligenceService`.
2. `_forward_client_audio` now routes text frames through
   `_handle_client_text_frame` (the `acknowledge_intervention` handler);
   previously it just logged and dropped them.
3. `_run_protection_analysis` calls `intervention_service.decide(analysis)`
   right after emitting `protection`/`timeline` frames, before `evidence`.
4. `_safe_send_session_summary` calls `intervention_service.resolve()` and
   sends the additive summary keys + the new `intervention_history` frame.
