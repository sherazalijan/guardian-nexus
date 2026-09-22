"""
Tests for the AssemblyAIClient interface contract.
 
NOTE: Reconcile with the existing interface-contract tests for
LLMAnalysisProvider / ThreatIntelligenceProvider before merging, so the
style/depth of these tests matches project convention.
"""
 
import inspect
 
import pytest
 
from app.services.assemblyai.interface import AssemblyAIClient
from app.services.assemblyai.mock_provider import MockAssemblyAIClient
 
 
def test_abstract_interface_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        AssemblyAIClient()  # type: ignore[abstract]
 
 
def test_mock_provider_is_an_assemblyai_client():
    client = MockAssemblyAIClient()
    assert isinstance(client, AssemblyAIClient)
 
 
@pytest.mark.parametrize(
    "method_name",
    ["connect", "send_audio", "receive_event", "disconnect"],
)
def test_required_async_methods_exist_on_interface(method_name):
    method = getattr(AssemblyAIClient, method_name)
    assert inspect.iscoroutinefunction(method)
 
 
@pytest.mark.parametrize(
    "method_name",
    ["connect", "send_audio", "receive_event", "disconnect"],
)
def test_mock_provider_implements_required_async_methods(method_name):
    method = getattr(MockAssemblyAIClient, method_name)
    assert inspect.iscoroutinefunction(method)
 
 
def test_connection_state_property_exists():
    client = MockAssemblyAIClient()
    # Should be accessible without error and return a ConnectionState-shaped object.
    state = client.connection_state
    assert hasattr(state, "connected")
    assert hasattr(state, "session_id")
