"""
Deterministic mock AssemblyAI client for testing and local development.
 
MockAssemblyAIClient performs no network access, requires no credentials,
and produces fully deterministic output on every call. It exists so the
rest of Guardian Nexus (and its test suite) can depend on AssemblyAIClient
without any real AssemblyAI connectivity.
"""
 
from __future__ import annotations
 
import uuid
 
from app.services.assemblyai.interface import AssemblyAIClient
from app.services.assemblyai.messages import ConnectionState, TranscriptChunk
 
_MOCK_TRANSCRIPT_TEXT = "This is a mock transcript."
_MOCK_SESSION_ID_PREFIX = "mock-session-"
 
 
class MockAssemblyAIClient(AssemblyAIClient):
    """A deterministic, in-memory stand-in for a real AssemblyAI client.
 
    Every call to receive_event() returns the same finalized TranscriptChunk,
    regardless of how many audio chunks were sent or how many times
    receive_event() has been called. This is intentional: Phase 7.2 only
    needs a predictable double for exercising the provider boundary, not a
    simulation of realistic conversational streaming (that belongs to more
    elaborate test fixtures introduced alongside the real client in 7.3, if
    needed).
    """
 
    def __init__(self) -> None:
        self._state = ConnectionState(connected=False, session_id=None)
 
    @property
    def connection_state(self) -> ConnectionState:
        return self._state
 
    async def connect(self) -> None:
        # Deterministic session id: stable per-instance, not time- or
        # randomness-derived in a way that would vary output content.
        session_id = f"{_MOCK_SESSION_ID_PREFIX}{uuid.uuid4()}"
        self._state = ConnectionState(connected=True, session_id=session_id)
 
    async def send_audio(self, audio_chunk: bytes) -> None:
        # No real processing. Accept any bytes without inspecting content.
        # Intentionally a no-op beyond the type/contract check implied by
        # the `bytes` parameter.
        return None
 
    async def receive_event(self) -> TranscriptChunk:
        return TranscriptChunk(
            text=_MOCK_TRANSCRIPT_TEXT,
            is_final=True,
            confidence=1.0,
        )
 
    async def disconnect(self) -> None:
        self._state = ConnectionState(connected=False, session_id=None)
