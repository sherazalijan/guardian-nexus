"""API routes for Guardian Nexus backend.

Phase 7.4 introduces the first WebSocket endpoint: a thin bidirectional
audio-transcription gateway between a client and the configured
AssemblyAI provider (see `app.services.assemblyai.factory`).

Scope for this phase is intentionally narrow:
    - No session management. The provider's own `ConnectionState.session_id`
      stays internal to the provider and is not surfaced here.
    - No LangGraph / risk engine / GuardianEvent integration. This
      endpoint only forwards raw transcript chunks using a minimal,
      purpose-specific JSON protocol (see the docstring on
      `websocket_audio` below). Wiring this gateway into the analysis
      pipeline and switching to `app.models.events.GuardianEvent` is a
      later phase.

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

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.errors import GuardianError
from app.services.assemblyai.factory import create_assemblyai_provider
from app.services.assemblyai.interface import AssemblyAIClient

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
        {"type": "error", "error": {"code", "message"}}
    """
    await websocket.accept()

    provider = create_assemblyai_provider()

    try:
        if not await _connect_provider(websocket, provider):
            return

        await websocket.send_json({"type": "connected"})

        client_task = asyncio.create_task(
            _forward_client_audio(websocket, provider),
            name="ws_audio_client_task",
        )
        transcript_task = asyncio.create_task(
            _forward_transcripts(websocket, provider),
            name="ws_audio_transcript_task",
        )
        pending: set[asyncio.Task[None]] = {client_task, transcript_task}

        done, pending = await asyncio.wait(
            pending, return_when=asyncio.FIRST_COMPLETED
        )
        await _cancel_all(pending)
        await _handle_completed(websocket, done)
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


async def _forward_transcripts(websocket: WebSocket, provider: AssemblyAIClient) -> None:
    """Read transcript events from the provider and forward them to the client.

    Runs until the provider raises (e.g. a `GuardianError` on connection
    loss or session termination) or the task is cancelled by its sibling
    finishing first.
    """
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
