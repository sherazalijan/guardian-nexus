"""
Tests for MockAssemblyAIClient.
 
Uses asyncio.run() rather than pytest.mark.asyncio, consistent with the
project's existing convention (pytest-asyncio is not installed).
 
NOTE: Reconcile file location/naming/fixture conventions with
tests/services/llm_analysis/ and tests/services/threat_intelligence/
before merging — written without access to those files.
"""
 
import asyncio
 
from app.services.assemblyai.messages import TranscriptChunk
from app.services.assemblyai.mock_provider import MockAssemblyAIClient
 
 
def test_connect_updates_connection_state():
    async def scenario():
        client = MockAssemblyAIClient()
        assert client.connection_state.connected is False
        assert client.connection_state.session_id is None
 
        await client.connect()
 
        assert client.connection_state.connected is True
        assert client.connection_state.session_id is not None
 
    asyncio.run(scenario())
 
 
def test_disconnect_updates_connection_state():
    async def scenario():
        client = MockAssemblyAIClient()
        await client.connect()
        assert client.connection_state.connected is True
 
        await client.disconnect()
 
        assert client.connection_state.connected is False
        assert client.connection_state.session_id is None
 
    asyncio.run(scenario())
 
 
def test_disconnect_is_idempotent():
    async def scenario():
        client = MockAssemblyAIClient()
        await client.connect()
        await client.disconnect()
        # Calling disconnect a second time should not raise.
        await client.disconnect()
        assert client.connection_state.connected is False
 
    asyncio.run(scenario())
 
 
def test_receive_event_returns_expected_transcript_chunk():
    async def scenario():
        client = MockAssemblyAIClient()
        await client.connect()
 
        event = await client.receive_event()
 
        assert isinstance(event, TranscriptChunk)
        assert event.text == "This is a mock transcript."
        assert event.is_final is True
 
    asyncio.run(scenario())
 
 
def test_receive_event_confidence_is_one():
    async def scenario():
        client = MockAssemblyAIClient()
        await client.connect()
 
        event = await client.receive_event()
 
        assert event.confidence == 1.0
 
    asyncio.run(scenario())
 
 
def test_receive_event_is_deterministic_across_repeated_calls():
    async def scenario():
        client = MockAssemblyAIClient()
        await client.connect()
 
        first = await client.receive_event()
        second = await client.receive_event()
        third = await client.receive_event()
 
        assert first == second == third
 
    asyncio.run(scenario())
 
 
def test_send_audio_accepts_bytes_without_raising():
    async def scenario():
        client = MockAssemblyAIClient()
        await client.connect()
 
        # Should not raise for arbitrary bytes content, including empty bytes.
        await client.send_audio(b"test audio")
        await client.send_audio(b"")
 
    asyncio.run(scenario())
 
 
def test_each_client_instance_gets_its_own_session_id():
    async def scenario():
        client_a = MockAssemblyAIClient()
        client_b = MockAssemblyAIClient()
 
        await client_a.connect()
        await client_b.connect()
 
        assert client_a.connection_state.session_id != client_b.connection_state.session_id
 
    asyncio.run(scenario())
