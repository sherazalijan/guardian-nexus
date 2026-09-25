"""State definition for Guardian Nexus's offline, rule-based pipeline.

This is a deliberately separate, minimal state from
`app.agents.state.GuardianGraphState` (the advanced, Nebius/Tavily-backed
pipeline's state). It exists so the offline pipeline -- built entirely
from deterministic rules and the existing risk engine -- can run with
zero external API keys, using a flat, easy-to-consume output shape,
without touching or depending on the advanced pipeline's typed domain
models or graph.

See `app.agents.graph.build_rule_based_guardian_graph` for the graph
that uses this state.
"""

from __future__ import annotations

from typing import TypedDict

from app.models.risk import RiskResult
from app.models.threat import ThreatSignal


class GuardianState(TypedDict, total=False):
    """State for the rule-based (offline, no-API-key) Guardian pipeline."""

    # Input
    transcript: str

    # RuleBasedScamAgent output
    scam_score: int
    category: str
    explanation: str

    # Internal bridge data: the ThreatSignal objects the scam agent
    # derives from its rule matches, consumed by the risk-engine node to
    # produce a real `RiskResult` via the existing, unmodified risk
    # engine (`app.services.risk_engine.run_risk_engine`).
    threat_signals: list[ThreatSignal]

    # Risk Engine output
    risk_level: str
    risk_result: RiskResult | None
