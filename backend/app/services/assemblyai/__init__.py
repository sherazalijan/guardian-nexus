"""
AssemblyAI service package.
 
Exposes the provider boundary (AssemblyAIClient), its message models, and
the factory function used to obtain a client instance. Real networking is
NOT part of this package in Phase 7.2 — see mock_provider.py.
 
NOTE: Confirm this export list matches the convention actually used by
app/services/llm_analysis/__init__.py and
app/services/threat_intelligence/__init__.py before merging.
"""
 
from app.services.assemblyai.factory import get_assemblyai_client
from app.services.assemblyai.interface import AssemblyAIClient
from app.services.assemblyai.messages import ConnectionState, TranscriptChunk
from app.services.assemblyai.mock_provider import MockAssemblyAIClient
 
__all__ = [
    "AssemblyAIClient",
    "MockAssemblyAIClient",
    "TranscriptChunk",
    "ConnectionState",
    "get_assemblyai_client",
]
