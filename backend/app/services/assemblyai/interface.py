"""
Abstract interface for AssemblyAI streaming clients.
 
This module defines the provider boundary that the rest of Guardian Nexus
should depend on. No implementation in this module performs real networking,
authentication, or AssemblyAI SDK/API calls — see mock_provider.py for the
Phase 7.2 deterministic test double, and (in Phase 7.3) the real
AssemblyAI WebSocket client.
 
Mirrors the interface pattern used by:
    app/services/llm_analysis/interface.py
    app/services/threat_intelligence/interface.py
 
NOTE: Verify this against those two files directly — this module was written
without access to the live repository and should be reconciled with the
project's actual ABC/typing conventions (e.g. ABC vs typing.Protocol,
naming of the base exception type, etc.) before merging.
"""
 
from __future__ import annotations
 
from abc import ABC, abstractmethod
 
from app.services.assemblyai.messages import ConnectionState, TranscriptChunk
 
 
class AssemblyAIClient(ABC):
    """Provider-agnostic interface for an AssemblyAI-style streaming STT client.
 
    Implementations are responsible only for connection lifecycle, audio
    transmission, and transcript-event retrieval. Implementations must NOT
    contain Risk Engine, LangGraph, or UI logic.
    """
 
    @abstractmethod
    async def connect(self) -> None:
        """Establish a streaming connection/session.
 
        Must update the client's connection state such that
        `connection_state.connected` is True and `connection_state.session_id`
        is populated on success.
        """
        raise NotImplementedError
 
    @abstractmethod
    async def send_audio(self, audio_chunk: bytes) -> None:
        """Send a chunk of raw audio to the streaming session.
 
        Implementations are not required to validate audio encoding in this
        phase; real audio-format validation belongs to the Phase 7.3 client.
        """
        raise NotImplementedError
 
    @abstractmethod
    async def receive_event(self) -> TranscriptChunk:
        """Receive the next available transcript event.
 
        Returns a TranscriptChunk. Implementations that need to represent
        provider errors should do so via their own documented mechanism
        (e.g. raising a specific exception type) rather than returning a
        malformed or empty TranscriptChunk.
        """
        raise NotImplementedError
 
    @abstractmethod
    async def disconnect(self) -> None:
        """Terminate the streaming session and release any held resources.
 
        Must update the client's connection state such that
        `connection_state.connected` is False. Implementations should treat
        repeated calls to disconnect() as safe/idempotent.
        """
        raise NotImplementedError
 
    @property
    @abstractmethod
    def connection_state(self) -> ConnectionState:
        """The client's current ConnectionState."""
        raise NotImplementedError
