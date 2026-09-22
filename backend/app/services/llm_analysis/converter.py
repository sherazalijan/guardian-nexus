
"""Convert untrusted LLM analysis into trusted Guardian Nexus signals."""

from datetime import datetime, timezone

from app.models.enums import ThreatCategory
from app.models.llm_analysis import LLMAnalysis, LLMSignal
from app.models.threat import ThreatSignal


SOURCE_RELIABILITY = 0.90


def calculate_evidence_strength(
    signal: LLMSignal,
    transcript: str,
) -> float:
    """Calculate deterministic evidence strength from quoted transcript evidence."""

    quote = signal.evidence_quote.strip()

    if not quote:
        return 0.0

    if quote.lower() not in transcript.lower():
        return 0.0

    return 1.0


def calculate_signal_confidence(
    signal: LLMSignal,
    evidence_strength: float,
) -> float:
    """Calculate trusted confidence from model and deterministic evidence."""

    confidence = (
        signal.model_confidence
        * evidence_strength
        * SOURCE_RELIABILITY
    )

    return max(0.0, min(confidence, 1.0))


def convert_signal(
    signal: LLMSignal,
    transcript: str,
    *,
    source: str = "nebius-nemotron",
) -> ThreatSignal | None:
    """Validate and convert one untrusted LLM signal."""

    try:
        category = ThreatCategory(
            signal.category.strip().lower()
        )
    except ValueError:
        return None

    evidence_strength = calculate_evidence_strength(
        signal,
        transcript,
    )

    if evidence_strength <= 0.0:
        return None

    confidence = calculate_signal_confidence(
        signal,
        evidence_strength,
    )

    return ThreatSignal(
        category=category,
        indicator=signal.category.strip().lower(),
        evidence=signal.evidence_quote.strip(),
        confidence=confidence,
        source=source,
        metadata={
            "reasoning": signal.reasoning,
            "model_confidence": signal.model_confidence,
            "evidence_strength": evidence_strength,
            "source_reliability": SOURCE_RELIABILITY,
        },
        timestamp=datetime.now(timezone.utc),
    )


def convert_analysis(
    analysis: LLMAnalysis,
    transcript: str,
    *,
    source: str = "nebius-nemotron",
) -> list[ThreatSignal]:
    """Convert all valid LLM signals into trusted ThreatSignals."""

    converted: list[ThreatSignal] = []

    for signal in analysis.signals:
        converted_signal = convert_signal(
            signal,
            transcript,
            source=source,
        )

        if converted_signal is not None:
            converted.append(converted_signal)

    return converted
