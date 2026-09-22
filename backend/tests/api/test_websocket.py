"""Tests for the Phase 7.4 `/ws/audio` WebSocket gateway.

NOTE ON ASYNC: like `tests/services/assemblyai/test_realtime_provider.py`,
this file intentionally avoids `pytest.mark.asyncio` / `pytest.mark.anyio`,
since neither plugin is installed in this project. All tests here are
plain synchronous pytest functions driven through FastAPI's
`TestClient.websocket_connect()`, which runs the ASGI app in a background
thread via a blocking portal (see `starlette.testclient`) -- no async
pytest plugin is required.

FakeAssemblyAIClient below is a purpose-built test double, distinct from
`MockAssemblyAIClient`: its `receive_event()` blocks on an `asyncio.Queue`
until a scripted chunk (or exception) becomes available, rather than
returning the same chunk immediately on every call. This lets tests
exercise the gateway's dual-task concurrency (audio flowing in while no
transcript has arrived yet, and vice versa) deterministically, without a
busy loop and without needing any cross-thread synchronization: every
queue is fully populated on the main thread *before* the WebSocket is
opened, so the background thread only ever reads from it.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from app.core.errors import ConfigurationError, GuardianError
from app.main import app
from app.services.assemblyai.interface import AssemblyAIClient
from app.services.assemblyai.messages import ConnectionState, TranscriptChunk

_GATEWAY_TASK_PREFIX = "ws_audio_"


class FakeAssemblyAIClient(AssemblyAIClient):
    """Controllable `AssemblyAIClient` test double for the WebSocket gateway.

    `events`, if given, is a sequence of `TranscriptChunk` (returned from
    `receive_event()`) and/or `Exception` instances (raised from
    `receive_event()`), consumed in order. Once exhausted, `receive_event()`
    blocks forever (awaiting an empty queue) rather than raising or
    repeating -- matching how a real streaming provider behaves between
    turns, and giving tests a natural way to leave the transcript side
    "still open" while they exercise the audio side.
    """

    def __init__(
        self,
        *,
        connect_error: Exception | None = None,
        events: list[TranscriptChunk | Exception] | None = None,
    ) -> None:
        self._connect_error = connect_error
        self._state = ConnectionState(connected=False, session_id=None)
        self._queue: asyncio.Queue[TranscriptChunk | Exception] = asyncio.Queue()
        for item in events or []:
            self._queue.put_nowait(item)

        self.connect_calls = 0
        self.disconnect_calls = 0
        self.sent_audio: list[bytes] = []
        self.leaked_task_names: set[str] = set()

    @property
    def connection_state(self) -> ConnectionState:
        return self._state

    async def connect(self) -> None:
        self.connect_calls += 1
        if self._connect_error is not None:
            raise self._connect_error
        self._state = ConnectionState(connected=True, session_id="fake-session")

    async def send_audio(self, audio_chunk: bytes) -> None:
        self.sent_audio.append(audio_chunk)

    async def receive_event(self) -> TranscriptChunk:
        item = await self._queue.get()
        if isinstance(item, Exception):
            raise item
        return item

    async def disconnect(self) -> None:
        self.disconnect_calls += 1
        self._state = ConnectionState(connected=False, session_id=None)
        # Runs on the gateway's own event loop (in the portal thread), after
        # `_cancel_all` has already awaited every gateway task -- the ideal
        # point to confirm none of them are still alive.
        self.leaked_task_names = {
            task.get_name()
            for task in asyncio.all_tasks()
            if task.get_name().startswith(_GATEWAY_TASK_PREFIX)
        }


def _patched_client(monkeypatch: pytest.MonkeyPatch, provider: FakeAssemblyAIClient) -> TestClient:
    """Route `/ws/audio` to `provider` instead of the real factory."""
    monkeypatch.setattr(
        "app.api.routes.create_assemblyai_provider",
        lambda: provider,
    )
    return TestClient(app)


# ---------------------------------------------------------------------
# 1 & 2. Connection accepted, "connected" event returned
# ---------------------------------------------------------------------


def test_ws_audio_accepts_connection_and_sends_connected(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeAssemblyAIClient()
    client = _patched_client(monkeypatch, provider)

    with client:
        with client.websocket_connect("/ws/audio") as ws:
            message = ws.receive_json()

    assert message == {"type": "connected"}
    assert provider.connect_calls == 1


# ---------------------------------------------------------------------
# 3. Binary audio forwarded to the provider
# ---------------------------------------------------------------------


def test_ws_audio_forwards_binary_audio_to_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeAssemblyAIClient()
    client = _patched_client(monkeypatch, provider)

    with client:
        with client.websocket_connect("/ws/audio") as ws:
            ws.receive_json()  # connected
            ws.send_bytes(b"\x00\x01\x02\x03")
            ws.send_bytes(b"\x04\x05")

    assert provider.sent_audio == [b"\x00\x01\x02\x03", b"\x04\x05"]


# ---------------------------------------------------------------------
# 4. Partial TranscriptChunk reaches the client
# ---------------------------------------------------------------------


def test_ws_audio_streams_partial_transcript(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeAssemblyAIClient(
        events=[TranscriptChunk(text="hel", is_final=False, confidence=0.5)]
    )
    client = _patched_client(monkeypatch, provider)

    with client:
        with client.websocket_connect("/ws/audio") as ws:
            ws.receive_json()  # connected
            message = ws.receive_json()

    assert message == {
        "type": "transcript",
        "data": {"text": "hel", "is_final": False, "confidence": 0.5},
    }


# ---------------------------------------------------------------------
# 5. Final TranscriptChunk reaches the client
# ---------------------------------------------------------------------


def test_ws_audio_streams_final_transcript(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeAssemblyAIClient(
        events=[TranscriptChunk(text="hello there.", is_final=True, confidence=0.95)]
    )
    client = _patched_client(monkeypatch, provider)

    with client:
        with client.websocket_connect("/ws/audio") as ws:
            ws.receive_json()  # connected
            message = ws.receive_json()

    assert message == {
        "type": "transcript",
        "data": {"text": "hello there.", "is_final": True, "confidence": 0.95},
    }


def test_ws_audio_streams_partial_then_final_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeAssemblyAIClient(
        events=[
            TranscriptChunk(text="hel", is_final=False, confidence=0.5),
            TranscriptChunk(text="hello there.", is_final=True, confidence=0.95),
        ]
    )
    client = _patched_client(monkeypatch, provider)

    with client:
        with client.websocket_connect("/ws/audio") as ws:
            ws.receive_json()  # connected
            partial = ws.receive_json()
            final = ws.receive_json()

    assert partial["data"]["is_final"] is False
    assert final["data"]["is_final"] is True
    assert final["data"]["text"] == "hello there."


# ---------------------------------------------------------------------
# 6. Text input handled safely (ignored, does not crash the gateway)
# ---------------------------------------------------------------------


def test_ws_audio_ignores_text_frames_without_crashing(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeAssemblyAIClient()
    client = _patched_client(monkeypatch, provider)

    with client:
        with client.websocket_connect("/ws/audio") as ws:
            ws.receive_json()  # connected
            ws.send_text("not audio and not JSON control either")
            ws.send_bytes(b"\x09")

    # The text frame was not forwarded as audio, and the gateway kept
    # running afterwards -- proven by the following binary frame still
    # reaching the provider.
    assert provider.sent_audio == [b"\x09"]


# ---------------------------------------------------------------------
# 7. Client disconnect causes provider cleanup
# ---------------------------------------------------------------------


def test_ws_audio_disconnect_triggers_provider_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeAssemblyAIClient()
    client = _patched_client(monkeypatch, provider)

    with client:
        with client.websocket_connect("/ws/audio") as ws:
            ws.receive_json()  # connected

    assert provider.connect_calls == 1
    assert provider.disconnect_calls == 1


# ---------------------------------------------------------------------
# 8. Provider connection failure is handled cleanly
# ---------------------------------------------------------------------


def test_ws_audio_provider_connect_failure_sends_error_and_closes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeAssemblyAIClient(
        connect_error=ConfigurationError("ASSEMBLYAI_API_KEY is not configured")
    )
    client = _patched_client(monkeypatch, provider)

    with client:
        with client.websocket_connect("/ws/audio") as ws:
            message = ws.receive_json()
            assert message["type"] == "error"
            assert message["error"]["code"] == "connection_failed"
            assert "ASSEMBLYAI_API_KEY" in message["error"]["message"]

            with pytest.raises(WebSocketDisconnect) as excinfo:
                ws.receive_json()
            assert excinfo.value.code == 1011


def test_ws_audio_provider_transcript_error_sends_error_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeAssemblyAIClient(
        events=[GuardianError("AssemblyAI terminated the realtime session.")]
    )
    client = _patched_client(monkeypatch, provider)

    with client:
        with client.websocket_connect("/ws/audio") as ws:
            ws.receive_json()  # connected
            message = ws.receive_json()

    assert message["type"] == "error"
    assert message["error"]["code"] == "provider_error"
    assert "traceback" not in message["error"]
    assert provider.disconnect_calls == 1


# ---------------------------------------------------------------------
# 9. No asyncio tasks are leaked
# ---------------------------------------------------------------------


def test_ws_audio_leaves_no_gateway_tasks_running_after_disconnect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeAssemblyAIClient(
        events=[TranscriptChunk(text="hel", is_final=False, confidence=0.5)]
    )
    client = _patched_client(monkeypatch, provider)

    with client:
        with client.websocket_connect("/ws/audio") as ws:
            ws.receive_json()  # connected
            ws.receive_json()  # partial transcript
            ws.send_bytes(b"\x00\x01")

    assert provider.disconnect_calls == 1
    assert provider.leaked_task_names == set()


# ---------------------------------------------------------------------
# 10. Existing /health endpoint still passes
# ---------------------------------------------------------------------


def test_health_endpoint_still_works() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "guardian-nexus-backend",
    }
