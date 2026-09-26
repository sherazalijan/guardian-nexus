"""API routes for Guardian Nexus backend.

Phase 7.4 introduced the first WebSocket endpoint: a thin bidirectional
audio-transcription gateway between a client and the configured
AssemblyAI provider (see `app.services.assemblyai.factory`).

Phase 1 (protection layer) extended that gateway, additively, to run the
existing offline rule-based analysis pipeline
(`app.agents.graph.build_rule_based_guardian_graph`) against each
finalized transcript segment and forward its output as three new frame
types -- `risk`, `protection`, and `timeline` -- plus a `session_summary`
frame once the connection ends.

Phase 2 (session intelligence) extends the same gateway again, also
additively: it adds a `SessionIntelligenceService` alongside the existing
`ProtectionService`, which turns the same Risk Engine / Protection
Service output into deduplicated evidence, a deterministic risk history,
and a richer incident timeline. It adds one new frame type -- `evidence`
-- and one new best-effort end-of-session frame -- `session_intelligence`
-- plus a small set of additive keys merged into the existing
`session_summary` payload. Nothing about the original `connected` /
`transcript` / `error` protocol changed, and nothing about the Phase 1
`risk` / `protection` / `timeline` / `session_summary` frames was
removed or altered -- every original field is still sent exactly as
before; Phase 2 only adds new frames and new keys alongside them.

No session management/persistence is added here beyond one in-memory
`ProtectionService` + one in-memory `SessionIntelligenceService` per
connection -- both are discarded when the socket closes.

Concurrency: audio ingestion (client -> provider) and transcript
delivery (provider -> client) run as two independent asyncio tasks so
that neither one blocks on the other -- audio must keep flowing to the
provider even while we're waiting on the next transcript, and transcripts
must keep flowing to the client even while no new audio has arrived.
Whichever task finishes first (due to client disconnect, a provider
error, or the provider ending the session) triggers cancellation of the
other, after which the provider connection is torn down and the client
socket is closed.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents.graph import build_rule_based_guardian_graph
from app.core.errors import GuardianError
from app.services.assemblyai.factory import create_assemblyai_provider
from app.services.assemblyai.interface import AssemblyAIClient
from app.services.protection import ProtectionService
from app.services.session_intelligence import SessionIntelligenceService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/audio")
async def websocket_audio(websocket: WebSocket) -> None:
    """Bidirectional audio-transcription WebSocket gateway.

    Client -> server: binary WebSocket frames containing raw audio,
    forwarded verbatim to the configured AssemblyAI provider via
    `send_audio()`. Text frames are accepted (so a stray text frame from
    a client never tears down the connection) but are not part of any
    defined control protocol in this phase, and are otherwise ignored.

    Server -> client: a minimal JSON protocol --
        {"type": "connected"}
        {"type": "transcript", "data": {"text", "is_final", "confidence"}}
        {"type": "risk", "data": {...RiskResult}}
        {"type": "protection", "data": {...ProtectionEvent}}
        {"type": "timeline", "data": {...TimelineEvent}}
        {"type": "evidence", "data": {...EvidenceItem}}
        {"type": "session_summary", "data": {...SessionSummary + Phase 2 extras}}
        {"type": "session_intelligence", "data": {...SessionIntelligence}}
        {"type": "error", "error": {"code", "message"}}

    `risk` / `protection` / `timeline` / `evidence` frames are emitted,
    in that order, each time a *final* transcript segment arrives and is
    run through the offline rule-based analysis pipeline (see
    `_run_protection_analysis`). Partial transcript segments only ever
    produce a `transcript` frame, as before. `session_summary` and
    `session_intelligence` are each sent once, best-effort, right before
    the connection is torn down.
    """
    await websocket.accept()

    provider = create_assemblyai_provider()
    protection_service: ProtectionService | None = None
    session_intelligence_service: SessionIntelligenceService | None = None

    try:
        if not await _connect_provider(websocket, provider):
            return

        await websocket.send_json({"type": "connected"})

        session_id = provider.connection_state.session_id or str(uuid4())
        protection_service = ProtectionService(session_id)
        session_intelligence_service = SessionIntelligenceService(session_id)
        guardian_graph = build_rule_based_guardian_graph()

        client_task = asyncio.create_task(
            _forward_client_audio(websocket, provider),
            name="ws_audio_client_task",
        )
        transcript_task = asyncio.create_task(
            _forward_transcripts(
                websocket,
                provider,
                protection_service,
                session_intelligence_service,
                guardian_graph,
            ),
            name="ws_audio_transcript_task",
        )
        pending: set[asyncio.Task[None]] = {client_task, transcript_task}

        done, pending = await asyncio.wait(
            pending, return_when=asyncio.FIRST_COMPLETED
        )
        await _cancel_all(pending)
        await _handle_completed(websocket, done)
    finally:
        try:
            if protection_service is not None:
                await _safe_send_session_summary(
                    websocket, protection_service, session_intelligence_service
                )
        finally:
            await _safe_disconnect(provider)
            await _safe_close(websocket)


async def _connect_provider(websocket: WebSocket, provider: AssemblyAIClient) -> bool:
    """Connect the provider, reporting a clean error to the client on failure.

    Returns True if the provider connected successfully, False otherwise.
    On failure, an error frame is sent and the socket is closed before
    returning -- the caller should return immediately without starting
    the audio/transcript tasks.
    """
    try:
        await provider.connect()
        return True
    except GuardianError as exc:
        await _safe_send_error(websocket, "connection_failed", str(exc))
        await _safe_close(websocket, code=1011)
        return False
    except Exception:
        logger.exception("Unexpected error connecting to the AssemblyAI provider.")
        await _safe_send_error(
            websocket,
            "connection_failed",
            "Failed to establish a transcription session.",
        )
        await _safe_close(websocket, code=1011)
        return False


async def _forward_client_audio(websocket: WebSocket, provider: AssemblyAIClient) -> None:
    """Read messages from the client and forward binary audio to the provider.

    Raises `WebSocketDisconnect` once the client disconnects, which is
    the normal way this task ends. Never raises on a text frame -- Phase
    7.4 defines no client control protocol, so a stray text frame is
    logged and skipped rather than treated as an error.
    """
    while True:
        message = await websocket.receive()

        if message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(message.get("code", 1000))

        audio_bytes = message.get("bytes")
        if audio_bytes is not None:
            await provider.send_audio(audio_bytes)
            continue

        text = message.get("text")
        if text is not None:
            logger.debug("Ignoring unexpected text frame on /ws/audio: %r", text)


async def _forward_transcripts(
    websocket: WebSocket,
    provider: AssemblyAIClient,
    protection_service: ProtectionService,
    session_intelligence_service: SessionIntelligenceService,
    guardian_graph,
) -> None:
    """Read transcript events from the provider and forward them to the client.

    Every chunk (partial or final) still produces a `transcript` frame,
    exactly as before Phase 1. Final, non-empty segments additionally run
    through the offline analysis pipeline (`_run_protection_analysis`),
    accumulated across the whole session so later analysis sees the full
    conversation so far, not just the latest fragment.

    Runs until the provider raises (e.g. a `GuardianError` on connection
    loss or session termination) or the task is cancelled by its sibling
    finishing first.
    """
    transcript_segments: list[str] = []

    while True:
        chunk = await provider.receive_event()
        await websocket.send_json(
            {
                "type": "transcript",
                "data": {
                    "text": chunk.text,
                    "is_final": chunk.is_final,
                    "confidence": chunk.confidence,
                },
            }
        )

        if chunk.is_final and chunk.text.strip():
            transcript_segments.append(chunk.text.strip())
            await _run_protection_analysis(
                websocket,
                protection_service,
                session_intelligence_service,
                guardian_graph,
                " ".join(transcript_segments),
            )


async def _run_protection_analysis(
    websocket: WebSocket,
    protection_service: ProtectionService,
    session_intelligence_service: SessionIntelligenceService,
    guardian_graph,
    transcript: str,
) -> None:
    """Run the offline scam-detection/risk-engine pipeline against the
    accumulated final transcript and forward the resulting `risk`,
    `protection`, `timeline`, and `evidence` frames to the client.

    Never raises: an analysis failure (a malformed graph state, an
    unexpected exception from a node, etc.) is reported to the client as
    an `error` frame (code `analysis_failed`) and logged, but does not
    tear down the WebSocket connection -- a single bad transcript
    fragment must not end the session.
    """
    try:
        state = await guardian_graph.ainvoke({"transcript": transcript})
        risk_result = state.get("risk_result")
        threat_signals = state.get("threat_signals", [])

        if risk_result is None:
            return

        await websocket.send_json(
            {"type": "risk", "data": risk_result.model_dump(mode="json")}
        )

        analysis = protection_service.process(
            threat_signals=threat_signals, risk_result=risk_result
        )

        for event in analysis.events:
            await websocket.send_json(
                {"type": "protection", "data": event.model_dump(mode="json")}
            )

        for timeline_event in analysis.timeline_events:
            await websocket.send_json(
                {"type": "timeline", "data": timeline_event.model_dump(mode="json")}
            )

        intelligence_update = session_intelligence_service.process(
            threat_signals=threat_signals,
            risk_result=risk_result,
            protection_result=analysis,
        )

        for evidence_item in intelligence_update.evidence:
            await websocket.send_json(
                {"type": "evidence", "data": evidence_item.model_dump(mode="json")}
            )
    except Exception:
        logger.exception(
            "Protection analysis failed for session %s.",
            protection_service.session_id,
        )
        await _safe_send_error(
            websocket, "analysis_failed", "Failed to analyze the transcript."
        )


async def _cancel_all(tasks: set[asyncio.Task[None]]) -> None:
    """Cancel a set of tasks and wait for them to actually finish.

    This is what prevents the sibling task from leaking once one side of
    the gateway ends: every task handed to this function is guaranteed to
    be done (cancelled) by the time it returns.
    """
    for task in tasks:
        task.cancel()
    for task in tasks:
        with contextlib.suppress(asyncio.CancelledError):
            await task


async def _handle_completed(websocket: WebSocket, done: set[asyncio.Task[None]]) -> None:
    """Report a clean error frame for anything other than a normal disconnect.

    A `WebSocketDisconnect` (the client went away) or a cancellation is
    not an error and is never reported to the client. A `GuardianError`
    raised by the provider is reported using the stable error envelope.
    Anything else is logged server-side and reported as a generic
    internal error, without leaking exception details to the client.
    """
    for task in done:
        exc = task.exception()

        if exc is None or isinstance(exc, (WebSocketDisconnect, asyncio.CancelledError)):
            continue

        if isinstance(exc, GuardianError):
            await _safe_send_error(websocket, "provider_error", str(exc))
        else:
            logger.error("Unexpected error in /ws/audio gateway.", exc_info=exc)
            await _safe_send_error(
                websocket, "internal_error", "An unexpected error occurred."
            )


async def _safe_send_error(websocket: WebSocket, code: str, message: str) -> None:
    """Best-effort error send. Never raises if the socket is already closed."""
    try:
        await websocket.send_json(
            {"type": "error", "error": {"code": code, "message": message}}
        )
    except Exception:
        logger.debug(
            "Could not deliver error frame; the websocket is already closed.",
            exc_info=True,
        )


async def _safe_send_session_summary(
    websocket: WebSocket,
    protection_service: ProtectionService,
    session_intelligence_service: SessionIntelligenceService | None,
) -> None:
    """Best-effort end-of-session summary. Never raises.

    Called from the gateway's `finally` block, so the client socket may
    already be gone (a normal disconnect) -- in that case this is a no-op,
    exactly like `_safe_send_error`.

    The Phase 1 `session_summary` payload is sent unchanged, with a small
    set of additive Phase 2 keys merged in (`evidence_count`,
    `primary_category`, `risk_escalation_count`, `final_state`) so
    existing clients that only read the original fields are unaffected.
    A separate, new `session_intelligence` frame carries the full
    evidence list, risk history, and incident timeline for clients that
    want it.
    """
    try:
        protection_service.end_session()
        summary = protection_service.build_session_summary()
        summary_data = summary.model_dump(mode="json")

        if session_intelligence_service is not None:
            intelligence_summary = session_intelligence_service.build_summary(summary)
            summary_data.update(
                {
                    "evidence_count": intelligence_summary.evidence_count,
                    "primary_category": intelligence_summary.primary_category.value,
                    "risk_escalation_count": intelligence_summary.risk_escalation_count,
                    "final_state": intelligence_summary.final_state.value,
                }
            )

        await websocket.send_json({"type": "session_summary", "data": summary_data})

        if session_intelligence_service is not None:
            snapshot = session_intelligence_service.snapshot()
            await websocket.send_json(
                {
                    "type": "session_intelligence",
                    "data": snapshot.model_dump(mode="json"),
                }
            )
    except Exception:
        logger.debug(
            "Could not deliver session summary; the websocket is already closed.",
            exc_info=True,
        )


async def _safe_disconnect(provider: AssemblyAIClient) -> None:
    """Best-effort provider cleanup. Never raises."""
    try:
        await provider.disconnect()
    except Exception:
        logger.exception("Error while disconnecting the AssemblyAI provider.")


async def _safe_close(websocket: WebSocket, code: int = 1000) -> None:
    """Best-effort socket close. Never raises if already closed."""
    try:
        await websocket.close(code=code)
    except Exception:
        logger.debug("WebSocket already closed.", exc_info=True)
