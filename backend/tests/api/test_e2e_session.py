import asyncio
import pytest
from uuid import uuid4
from sqlalchemy import select

from app.api import routes
from app.services.assemblyai.messages import TranscriptChunk, ConnectionState
from app.services.protection.service import ProtectionService
from app.services.session_intelligence.service import SessionIntelligenceService
from app.services.interventions.policy import InterventionPolicyService
from app.services.voice_intelligence.service import VoiceIntelligenceService
from app.services.protection_history.service import ProtectionHistoryService
from app.services.guardian_alerts.manager import GuardianAlertManager
from app.agents.guardian.graph import build_rule_based_guardian_graph
from app.services.persistence.hooks import PersistenceHooks
from tests.api.test_websocket import FakeAssemblyAIClient

pytestmark = pytest.mark.asyncio

class MockWebSocket:
    def __init__(self):
        self.sent_messages = []

    async def send_json(self, data: dict):
        self.sent_messages.append(data)


async def test_e2e_bank_scam_session(db_session):
    """
    E2E test verifying a full session through the backend logic and into the Database.
    We inject a FakeAssemblyAIClient that simulates a bank impersonation scam.
    """
    fake_provider = FakeAssemblyAIClient(
        events=[
            TranscriptChunk(text="Hello, this is your bank's fraud department.", is_final=True, confidence=0.95),
            TranscriptChunk(text="We've detected unauthorized transactions.", is_final=True, confidence=0.95),
            TranscriptChunk(text="We need to verify your identity. Please read me the OTP just sent to your phone.", is_final=True, confidence=0.95),
            RuntimeError("End of stream"),
        ]
    )
    fake_provider._state = ConnectionState(connected=True, session_id=str(uuid4()))

    mock_ws = MockWebSocket()
    
    session_id = fake_provider.connection_state.session_id
    protection_service = ProtectionService(session_id)
    session_intelligence_service = SessionIntelligenceService(session_id)
    intervention_service = InterventionPolicyService(session_id)
    voice_intelligence_service = VoiceIntelligenceService(session_id)
    protection_history_service = ProtectionHistoryService(session_id)
    guardian_alert_manager = GuardianAlertManager(session_id)
    guardian_graph = build_rule_based_guardian_graph()
    
    # Initialize hooks with our explicit db_session
    persistence_hooks = PersistenceHooks(session_id, db=db_session)
    await persistence_hooks.start()

    try:
        # Run the transcript forwarding loop directly
        await routes._forward_transcripts(
            mock_ws,  # type: ignore
            fake_provider,
            protection_service,
            session_intelligence_service,
            intervention_service,
            voice_intelligence_service,
            protection_history_service,
            guardian_alert_manager,
            guardian_graph,
            persistence_hooks,
        )
    except RuntimeError as e:
        if str(e) != "End of stream":
            raise
    
    # Send the final session summary
    await routes._safe_send_session_summary(
        mock_ws,  # type: ignore
        protection_service,
        session_intelligence_service,
        intervention_service,
        persistence_hooks,
    )
    await persistence_hooks.close()

    # Verification: Ensure we received the expected WebSocket events
    types_received = {e.get("type") for e in mock_ws.sent_messages}
    assert "transcript" in types_received
    assert "risk" in types_received
    assert "protection" in types_received
    assert "session_summary" in types_received

    # Verify Database Persistence
    from app.db.models import Session, TranscriptSegment, RiskEvent, ProtectionEvent

    # Check Sessions
    result = await db_session.execute(select(Session))
    sessions = result.scalars().all()
    assert len(sessions) == 1

    # Check Transcripts
    result = await db_session.execute(select(TranscriptSegment))
    transcripts = result.scalars().all()
    assert len(transcripts) == 3

    # Check Risk Events
    result = await db_session.execute(select(RiskEvent))
    risks = result.scalars().all()
    assert len(risks) > 0
    assert risks[-1].score > 50  # Risk should have escalated

    # Check Protection Events
    result = await db_session.execute(select(ProtectionEvent))
    protections = result.scalars().all()
    assert len(protections) > 0
