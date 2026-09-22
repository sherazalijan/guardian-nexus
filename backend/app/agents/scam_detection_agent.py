from app.agents.state import GuardianGraphState
from app.models.graph import GraphError, NodeStatus
from app.services.llm_analysis.converter import convert_analysis
from app.services.llm_analysis.factory import create_llm_provider


async def scam_detection_agent(state: GuardianGraphState) -> GuardianGraphState:
    transcript = state.get("transcript", "").strip()

    status = dict(state.get("node_status", {}))
    errors = list(state.get("errors", []))

    if not transcript:
        status["scam_detection"] = NodeStatus.SKIPPED
        return {
            **state,
            "llm_analysis": None,
            "threat_signals": [],
            "candidate_targets": [],
            "node_status": status,
            "errors": errors,
        }

    try:
        provider = create_llm_provider()
        analysis = await provider.analyze(transcript)

        threat_signals = convert_analysis(
            analysis,
            transcript,
            source="nebius-nemotron",
        )

        candidate_targets = []

        for signal in threat_signals:
            candidate_targets.append(
                {
                    "target_type": signal.category.value,
                    "value": signal.indicator,
                    "source": signal.source,
                }
            )

        status["scam_detection"] = NodeStatus.SUCCESS

        return {
            **state,
            "llm_analysis": analysis,
            "threat_signals": threat_signals,
            "candidate_targets": candidate_targets,
            "node_status": status,
            "errors": errors,
        }

    except Exception as exc:
        status["scam_detection"] = NodeStatus.FAILED
        errors.append(
            GraphError(
                node="scam_detection",
                code="SCAM_DETECTION_FAILED",
                message=str(exc),
            )
        )

        return {
            **state,
            "llm_analysis": None,
            "threat_signals": [],
            "candidate_targets": [],
            "node_status": status,
            "errors": errors,
        }
