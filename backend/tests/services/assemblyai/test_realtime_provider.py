"""Tests for RealtimeAssemblyAIProvider.

These tests never touch the network or a real API key. They patch
`websockets.connect` with a deterministic fake WebSocket transport that
plays back a scripted sequence of messages, so behavior is fully
controlled and timing-independent.

NOTE ON ASYNC: this file intentionally does NOT use `pytest.mark.asyncio`
or `pytest.mark.anyio`, since neither `pytest-asyncio` nor a configured
`anyio` pytest plugin was confirmed to be active in this project's test
suite. Every test is a plain (synchronous) pytest test function that
drives its async body via `asyncio.run(...)`, so no async pytest plugin
or config is required at all. If this project already standardizes on
`pytest-asyncio` or `anyio` elsewhere, these can be converted later --
but as written they work unconditionally.
"""

from __future__ import annotations

import asyncio
import json
from collections import deque
from collections.abc import Iterable
from typing import Any

import pytest

from app.core.errors import ConfigurationError, GuardianError
from app.services.assemblyai.realtime_provider import RealtimeAssemblyAIProvider


class FakeWebSocket:
    """Deterministic stand-in for a websockets client connection.

    `to_recv` is the scripted queue of inbound messages (each either a
    JSON-serializable dict, which is sent as a text frame, or raw
    bytes/str, which is sent as-is). `raise_on_recv` lets tests simulate
    a transport failure once the scripted queue is exhausted.
    """

    def __init__(self, to_recv: Iterable[Any] = (), *, raise_on_recv: Exception | None = None):
        self._queue: deque[Any] = deque(to_recv)
        self._raise_on_recv = raise_on_recv
        self.sent: list[Any] = []
        self.closed = False
        self.close_calls = 0

    async def recv(self) -> Any:
        if self._queue:
            item = self._queue.popleft()
            if isinstance(item, (bytes, bytearray, str)):
                return item
            return json.dumps(item)
        if self._raise_on_recv is not None:
            raise self._raise_on_recv
        raise AssertionError("FakeWebSocket.recv() called with an empty script")

    async def send(self, data: Any) -> None:
        self.sent.append(data)

    async def close(self) -> None:
        self.closed = True
        self.close_calls += 1


BEGIN_MESSAGE = {"type": "Begin", "id": "session-123", "expires_at": 1234567890}

PARTIAL_TURN = {
    "type": "Turn",
    "turn_order": 0,
    "end_of_turn": False,
    "transcript": "hello",
    "end_of_turn_confidence": 0.1,
    "words": [{"text": "hello", "start": 0, "end": 300, "confidence": 0.9}],
}

FINAL_TURN = {
    "type": "Turn",
    "turn_order": 1,
    "end_of_turn": True,
    "transcript": "hello there.",
    "end_of_turn_confidence": 0.99,
    "words": [
        {"text": "hello", "start": 0, "end": 300, "confidence": 0.9},
        {"text": "there.", "start": 300, "end": 600, "confidence": 0.8},
    ],
}

TERMINATION_MESSAGE = {
    "type": "Termination",
    "audio_duration_seconds": 5,
    "session_duration_seconds": 6,
}


def _patch_connect(monkeypatch: pytest.MonkeyPatch, ws: FakeWebSocket | Exception) -> None:
    async def fake_connect(*args: Any, **kwargs: Any) -> FakeWebSocket:
        if isinstance(ws, Exception):
            raise ws
        return ws

    monkeypatch.setattr(
        "app.services.assemblyai.realtime_provider.websockets.connect",
        fake_connect,
    )


async def _connected_provider(
    monkeypatch: pytest.MonkeyPatch, *extra_messages: Any
) -> tuple[RealtimeAssemblyAIProvider, FakeWebSocket]:
    ws = FakeWebSocket(to_recv=[BEGIN_MESSAGE, *extra_messages])
    _patch_connect(monkeypatch, ws)
    provider = RealtimeAssemblyAIProvider(api_key="test-key")
    await provider.connect()
    return provider, ws


# ---------------------------------------------------------------------
# 1. Initial state
# ---------------------------------------------------------------------


def test_initial_state_is_disconnected() -> None:
    provider = RealtimeAssemblyAIProvider(api_key="test-key")

    state = provider.connection_state

    assert state.connected is False
    assert state.session_id is None


# ---------------------------------------------------------------------
# 2. Successful connect
# ---------------------------------------------------------------------


def test_connect_success_sets_connected_and_session_id(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        provider, _ws = await _connected_provider(monkeypatch)

        state = provider.connection_state
        assert state.connected is True
        assert state.session_id == "session-123"

    asyncio.run(_run())


# ---------------------------------------------------------------------
# 3. Missing API key
# ---------------------------------------------------------------------


def test_connect_without_api_key_raises_configuration_error() -> None:
    async def _run() -> None:
        provider = RealtimeAssemblyAIProvider(api_key=None)

        with pytest.raises(ConfigurationError):
            await provider.connect()

        assert provider.connection_state.connected is False

    asyncio.run(_run())


# ---------------------------------------------------------------------
# 4. Send audio
# ---------------------------------------------------------------------


def test_send_audio_sends_raw_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        provider, ws = await _connected_provider(monkeypatch)

        audio = b"\x00\x01\x02\x03"
        await provider.send_audio(audio)

        assert ws.sent == [audio]
        assert isinstance(ws.sent[0], (bytes, bytearray))

    asyncio.run(_run())


def test_send_audio_before_connect_raises() -> None:
    async def _run() -> None:
        provider = RealtimeAssemblyAIProvider(api_key="test-key")

        with pytest.raises(GuardianError):
            await provider.send_audio(b"\x00\x00")

    asyncio.run(_run())


# ---------------------------------------------------------------------
# 5. Partial transcript
# ---------------------------------------------------------------------


def test_receive_event_partial_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        provider, _ws = await _connected_provider(monkeypatch, PARTIAL_TURN)

        chunk = await provider.receive_event()

        assert chunk.text == "hello"
        assert chunk.is_final is False
        assert chunk.confidence == pytest.approx(0.9)

    asyncio.run(_run())


# ---------------------------------------------------------------------
# 6. Final transcript
# ---------------------------------------------------------------------


def test_receive_event_final_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        provider, _ws = await _connected_provider(monkeypatch, FINAL_TURN)

        chunk = await provider.receive_event()

        assert chunk.text == "hello there."
        assert chunk.is_final is True
        assert chunk.confidence == pytest.approx(0.85)

    asyncio.run(_run())


def test_receive_event_turn_with_no_words_has_zero_confidence(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        empty_turn = {"type": "Turn", "end_of_turn": False, "transcript": "", "words": []}
        provider, _ws = await _connected_provider(monkeypatch, empty_turn)

        chunk = await provider.receive_event()

        assert chunk.text == ""
        assert chunk.confidence == 0.0

    asyncio.run(_run())


# ---------------------------------------------------------------------
# 7. Non-transcript events
# ---------------------------------------------------------------------


def test_receive_event_skips_stray_begin_then_returns_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        stray_begin = {"type": "Begin", "id": "session-123", "expires_at": 1}
        provider, _ws = await _connected_provider(monkeypatch, stray_begin, PARTIAL_TURN)

        chunk = await provider.receive_event()

        assert chunk.text == "hello"
        assert chunk.is_final is False

    asyncio.run(_run())


def test_receive_event_skips_unknown_message_type_then_returns_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        unknown = {"type": "SpeakerRevision", "revisions": []}
        provider, _ws = await _connected_provider(monkeypatch, unknown, FINAL_TURN)

        chunk = await provider.receive_event()

        assert chunk.text == "hello there."
        assert chunk.is_final is True

    asyncio.run(_run())


def test_receive_event_termination_raises_and_marks_disconnected(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        provider, _ws = await _connected_provider(monkeypatch, TERMINATION_MESSAGE)

        with pytest.raises(GuardianError):
            await provider.receive_event()

        assert provider.connection_state.connected is False
        assert provider.connection_state.session_id is None

    asyncio.run(_run())


# ---------------------------------------------------------------------
# 8. Disconnect
# ---------------------------------------------------------------------


def test_disconnect_sends_terminate_and_closes_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        provider, ws = await _connected_provider(monkeypatch)

        await provider.disconnect()

        assert ws.sent == [json.dumps({"type": "Terminate"})]
        assert ws.closed is True
        assert provider.connection_state.connected is False
        assert provider.connection_state.session_id is None

    asyncio.run(_run())


# ---------------------------------------------------------------------
# 9. Idempotent disconnect
# ---------------------------------------------------------------------


def test_disconnect_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        provider, ws = await _connected_provider(monkeypatch)

        await provider.disconnect()
        await provider.disconnect()  # must not raise

        assert ws.close_calls == 1
        assert provider.connection_state.connected is False

    asyncio.run(_run())


def test_disconnect_without_ever_connecting_is_safe() -> None:
    async def _run() -> None:
        provider = RealtimeAssemblyAIProvider(api_key="test-key")

        await provider.disconnect()  # must not raise

        assert provider.connection_state.connected is False

    asyncio.run(_run())


# ---------------------------------------------------------------------
# 10. Connection failure
# ---------------------------------------------------------------------


def test_connect_failure_surfaces_guardian_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        _patch_connect(monkeypatch, OSError("connection refused"))
        provider = RealtimeAssemblyAIProvider(api_key="test-key")

        with pytest.raises(GuardianError):
            await provider.connect()

        assert provider.connection_state.connected is False

    asyncio.run(_run())


def test_connect_without_begin_message_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        ws = FakeWebSocket(to_recv=[{"type": "Turn", "transcript": "oops", "end_of_turn": False}])
        _patch_connect(monkeypatch, ws)
        provider = RealtimeAssemblyAIProvider(api_key="test-key")

        with pytest.raises(GuardianError):
            await provider.connect()

        assert provider.connection_state.connected is False
        assert ws.closed is True

    asyncio.run(_run())


# ---------------------------------------------------------------------
# 11. Receive failure (malformed / unexpected response)
# ---------------------------------------------------------------------


def test_receive_event_malformed_json_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        ws = FakeWebSocket(to_recv=[BEGIN_MESSAGE, "{not valid json"])
        _patch_connect(monkeypatch, ws)
        provider = RealtimeAssemblyAIProvider(api_key="test-key")
        await provider.connect()

        with pytest.raises(GuardianError):
            await provider.receive_event()

    asyncio.run(_run())


def test_receive_event_unexpected_binary_frame_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        ws = FakeWebSocket(to_recv=[BEGIN_MESSAGE, b"\x01\x02\x03"])
        _patch_connect(monkeypatch, ws)
        provider = RealtimeAssemblyAIProvider(api_key="test-key")
        await provider.connect()

        with pytest.raises(GuardianError):
            await provider.receive_event()

    asyncio.run(_run())


def test_receive_event_transport_error_raises_and_disconnects(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        ws = FakeWebSocket(to_recv=[BEGIN_MESSAGE], raise_on_recv=OSError("connection reset"))
        _patch_connect(monkeypatch, ws)
        provider = RealtimeAssemblyAIProvider(api_key="test-key")
        await provider.connect()

        with pytest.raises(GuardianError):
            await provider.receive_event()

        assert provider.connection_state.connected is False

    asyncio.run(_run())
