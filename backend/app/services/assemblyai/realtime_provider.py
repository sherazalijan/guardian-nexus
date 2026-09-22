"""Real (non-mock) AssemblyAI realtime streaming provider.

This implements ``AssemblyAIClient`` against AssemblyAI's current v3
Universal-Streaming WebSocket API. It is the network-facing sibling of
``MockAssemblyAIClient`` and contains ONLY protocol/transport concerns:
opening the socket, authenticating, converting AssemblyAI's wire
messages into the project's internal ``TranscriptChunk`` /
``ConnectionState`` models, and tearing the session down cleanly.

No Risk Engine, LangGraph, scam-detection, Tavily, Nemotron, route, or
frontend logic belongs in this file (see Phase 7.3 spec).

Protocol reference (AssemblyAI Universal-Streaming v3, verified against
current AssemblyAI docs as of this implementation):

    Endpoint:
        wss://streaming.assemblyai.com/v3/ws
        (NOT the deprecated wss://api.assemblyai.com/v2/realtime/ws)

    Query parameters used here:
        sample_rate=16000
        speech_model=universal-3-5-pro

    Auth:
        The raw API key is sent in the `Authorization` header with NO
        "Bearer" prefix. This is specific to the raw streaming
        WebSocket endpoint (the official Python SDK's StreamingClient
        does this under the hood; we do it explicitly since we are
        talking to the WebSocket directly).

    Audio:
        Client -> server audio frames are raw binary WebSocket frames
        containing PCM16 mono samples at 16 kHz. They are NOT
        JSON-encoded and NOT base64-encoded. This provider does not
        perform any audio conversion; it forwards whatever bytes
        `send_audio()` is given.

    Server -> client JSON text messages, discriminated by "type":
        - "Begin":
              {"type": "Begin", "id": "<session-id>", "expires_at": ...}
          Sent once, immediately after the connection is accepted.
        - "Turn":
              {
                "type": "Turn",
                "turn_order": 0,
                "turn_is_formatted": bool,
                "end_of_turn": bool,
                "transcript": "hello world",
                "end_of_turn_confidence": 0.99,
                "words": [
                    {"text": "hello", "start": 0, "end": 500, "confidence": 0.99},
                    ...
                ]
              }
          Sent repeatedly as the model transcribes; `end_of_turn` marks
          whether this is a partial or final turn.
        - "Termination":
              {"type": "Termination", "audio_duration_seconds": ..., "session_duration_seconds": ...}
          Sent by AssemblyAI when the session ends (in response to a
          client Terminate message, or on an idle/expiry timeout).

    Client -> server control message for clean shutdown:
        {"type": "Terminate"}
        sent as a JSON text frame before closing the socket.

Confidence mapping (see `_confidence_from_turn` below for the full
rationale): AssemblyAI's v3 Turn message has no single field that
represents "confidence in this transcript's correctness" as a scalar.
It exposes `end_of_turn_confidence`, which is the model's confidence
that the *speaker has stopped talking* (a turn-boundary signal, not a
transcription-quality signal), and a `words` array where each word
carries its own transcription `confidence`. Since the internal
`TranscriptChunk.confidence` field is documented here as "confidence in
the transcribed text", this provider derives it as the arithmetic mean
of the per-word confidences returned for that turn. When a turn has no
words (e.g. an empty/whitespace-only partial), there is no
transcription confidence to report, and 0.0 is used rather than a
fabricated placeholder such as 1.0.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Final

import websockets
from websockets.exceptions import WebSocketException

from app.core.errors import ConfigurationError, GuardianError
from app.services.assemblyai.interface import AssemblyAIClient
from app.services.assemblyai.messages import ConnectionState, TranscriptChunk

logger = logging.getLogger(__name__)

_STREAMING_URL: Final[str] = "wss://streaming.assemblyai.com/v3/ws"
_SPEECH_MODEL: Final[str] = "universal-3-5-pro"
_SAMPLE_RATE: Final[int] = 16000

# Transport-level failures we treat as "provider/network failure" and
# surface via the existing GuardianError hierarchy rather than letting
# leak out as raw library exceptions.
_TRANSPORT_ERRORS: Final[tuple[type[Exception], ...]] = (WebSocketException, OSError)


class RealtimeAssemblyAIProvider(AssemblyAIClient):
    """AssemblyAIClient implementation backed by AssemblyAI's real v3
    realtime streaming WebSocket.

    The provider is constructed with the API key it should use (the
    factory is responsible for reading `ASSEMBLYAI_API_KEY` from the
    existing Settings system and passing it in here) so that this class
    has no direct dependency on how configuration is wired elsewhere.
    """

    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key
        self._ws: Any | None = None
        self._state = ConnectionState(connected=False, session_id=None)

    # ------------------------------------------------------------------
    # AssemblyAIClient interface
    # ------------------------------------------------------------------

    @property
    def connection_state(self) -> ConnectionState:
        return self._state

    async def connect(self) -> None:
        if not self._api_key:
            raise ConfigurationError(
                "ASSEMBLYAI_API_KEY is not configured; cannot start a "
                "realtime AssemblyAI session."
            )

        url = f"{_STREAMING_URL}?sample_rate={_SAMPLE_RATE}&speech_model={_SPEECH_MODEL}"

        try:
            self._ws = await self._open_socket(url)
        except _TRANSPORT_ERRORS as exc:
            self._ws = None
            raise GuardianError(
                f"Failed to connect to the AssemblyAI realtime endpoint: {exc}"
            ) from exc

        try:
            raw = await self._ws.recv()
        except _TRANSPORT_ERRORS as exc:
            await self._close_socket()
            raise GuardianError(
                f"AssemblyAI connection closed before sending a Begin message: {exc}"
            ) from exc

        message = self._parse_message(raw)
        if message.get("type") != "Begin":
            await self._close_socket()
            raise GuardianError(
                "Expected a Begin message from AssemblyAI but received "
                f"{message.get('type', 'an unrecognized message')!r} instead."
            )

        self._state = ConnectionState(
            connected=True,
            session_id=message.get("id"),
        )

    async def send_audio(self, audio_chunk: bytes) -> None:
        if self._ws is None or not self._state.connected:
            raise GuardianError(
                "Cannot send audio: the AssemblyAI realtime session is not connected."
            )

        try:
            # Passing `bytes` sends a binary WebSocket frame. Raw PCM16
            # audio only -- never JSON- or base64-encoded here.
            await self._ws.send(audio_chunk)
        except _TRANSPORT_ERRORS as exc:
            raise GuardianError(
                f"Failed to send audio to AssemblyAI: {exc}"
            ) from exc

    async def receive_event(self) -> TranscriptChunk:
        if self._ws is None or not self._state.connected:
            raise GuardianError(
                "Cannot receive events: the AssemblyAI realtime session is not connected."
            )

        while True:
            try:
                raw = await self._ws.recv()
            except _TRANSPORT_ERRORS as exc:
                self._state = ConnectionState(connected=False, session_id=None)
                raise GuardianError(
                    f"AssemblyAI realtime connection was lost: {exc}"
                ) from exc

            message = self._parse_message(raw)
            msg_type = message.get("type")

            if msg_type == "Turn":
                return self._turn_to_chunk(message)

            if msg_type == "Termination":
                # The session ended (client Terminate, idle timeout, or
                # server-side expiry). There is no transcript to return,
                # so we surface this deterministically as an error
                # rather than fabricating an empty TranscriptChunk, and
                # we reflect the state change so callers relying on
                # `connection_state` see it immediately.
                self._state = ConnectionState(connected=False, session_id=None)
                raise GuardianError("AssemblyAI terminated the realtime session.")

            if msg_type == "Begin":
                # A stray Begin after the initial handshake shouldn't
                # happen, but if it does it is not a transcript event --
                # skip it and keep waiting for the next relevant message.
                logger.debug("Ignoring unexpected duplicate Begin message from AssemblyAI.")
                continue

            # Any other/unrecognized message type (e.g. SpeakerRevision,
            # LLMGatewayResponse) is not a transcript event for this
            # provider's purposes. Skip and keep waiting rather than
            # raising, so the provider stays forward-compatible with
            # message types AssemblyAI may add.
            logger.debug("Ignoring non-transcript AssemblyAI message type: %r", msg_type)

    async def disconnect(self) -> None:
        ws = self._ws
        self._ws = None

        if ws is not None:
            try:
                await ws.send(json.dumps({"type": "Terminate"}))
            except _TRANSPORT_ERRORS:
                # Best-effort: if the socket is already broken there is
                # no clean termination message to send; we still close
                # it below.
                pass
            finally:
                try:
                    await ws.close()
                except _TRANSPORT_ERRORS:
                    pass

        self._state = ConnectionState(connected=False, session_id=None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _open_socket(self, url: str) -> Any:
        headers = {"Authorization": self._api_key}
        try:
            # websockets >= 14 uses the asyncio client by default, whose
            # `connect()` takes `additional_headers`.
            return await websockets.connect(url, additional_headers=headers)
        except TypeError:
            # websockets < 14 (or an environment still resolving the
            # legacy client) exposes the same kwarg as `extra_headers`.
            return await websockets.connect(url, extra_headers=headers)

    async def _close_socket(self) -> None:
        ws, self._ws = self._ws, None
        if ws is None:
            return
        try:
            await ws.close()
        except _TRANSPORT_ERRORS:
            pass

    @staticmethod
    def _parse_message(raw: str | bytes) -> dict[str, Any]:
        if isinstance(raw, (bytes, bytearray)):
            # AssemblyAI's v3 control channel only ever sends JSON text
            # frames; a binary frame here is a protocol violation.
            raise GuardianError(
                "Received an unexpected binary frame from AssemblyAI while "
                "expecting a JSON message."
            )
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise GuardianError(
                f"Received malformed JSON from AssemblyAI: {exc}"
            ) from exc
        if not isinstance(parsed, dict):
            raise GuardianError(
                "Received a JSON message from AssemblyAI that was not a JSON object."
            )
        return parsed

    @staticmethod
    def _confidence_from_turn(message: dict[str, Any]) -> float:
        """Derive a single transcription-confidence float for a Turn.

        AssemblyAI's v3 Turn message does not provide one scalar
        "confidence in this transcript" value. `end_of_turn_confidence`
        exists but measures something different (how confident the
        model is that the speaker has finished talking), so using it
        here would silently mislabel a turn-detection signal as a
        transcription-quality signal. Instead we average the per-word
        `confidence` values AssemblyAI does provide. If there are no
        words (e.g. an empty partial turn), there is no transcription
        confidence to report, so 0.0 is returned rather than inventing
        a value such as 1.0.
        """
        words = message.get("words") or []
        confidences = [
            word["confidence"]
            for word in words
            if isinstance(word, dict) and isinstance(word.get("confidence"), (int, float))
        ]
        if not confidences:
            return 0.0
        return sum(confidences) / len(confidences)

    @classmethod
    def _turn_to_chunk(cls, message: dict[str, Any]) -> TranscriptChunk:
        return TranscriptChunk(
            text=message.get("transcript", ""),
            is_final=bool(message.get("end_of_turn", False)),
            confidence=cls._confidence_from_turn(message),
        )
