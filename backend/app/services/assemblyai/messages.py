"""
Pydantic message models for the AssemblyAI service layer.
 
These models represent the normalized, internal shape of AssemblyAI-related
data used by AssemblyAIClient implementations. They intentionally do NOT
mirror AssemblyAI's raw wire format — that mapping belongs to the real
client implementation added in Phase 7.3.
"""
 
from __future__ import annotations
 
from pydantic import BaseModel, Field
 
 
class TranscriptChunk(BaseModel):
    """A single transcript chunk received from an AssemblyAI client.
 
    Represents either a partial (in-progress) or final (end_of_turn)
    transcript segment.
    """
 
    text: str = Field(..., description="The transcribed text for this chunk.")
    is_final: bool = Field(
        ...,
        description="True if this chunk represents a finalized turn "
        "(AssemblyAI end_of_turn=true); False for partial/in-progress text.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Provider-reported confidence for this transcript chunk, 0.0-1.0.",
    )
 
 
class ConnectionState(BaseModel):
    """Represents the current connection state of an AssemblyAIClient."""
 
    connected: bool = Field(
        ..., description="True if the client currently holds an active connection."
    )
    session_id: str | None = Field(
        default=None,
        description="Provider/session identifier once connected; None if not connected.",
    )
