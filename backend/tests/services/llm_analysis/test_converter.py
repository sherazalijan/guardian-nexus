from app.models.enums import ThreatCategory
from app.models.llm_analysis import LLMAnalysis, LLMSignal
from app.services.llm_analysis.converter import (
    SOURCE_RELIABILITY,
    convert_analysis,
    convert_signal,
)


def make_signal(
    category: str = "scam",
    evidence_quote: str = "Please send me the verification code.",
    model_confidence: float = 1.0,
) -> LLMSignal:
    return LLMSignal(
        category=category,
        evidence_quote=evidence_quote,
        model_confidence=model_confidence,
        reasoning="Test reasoning.",
    )


def test_valid_signal_is_converted():
    transcript = "Please send me the verification code."

    result = convert_signal(
        make_signal(),
        transcript,
        source="nebius-nemotron",
    )

    assert result is not None
    assert result.category == ThreatCategory.SCAM
    assert result.evidence == transcript
    assert result.confidence == SOURCE_RELIABILITY
    assert result.source == "nebius-nemotron"


def test_unknown_category_is_rejected():
    result = convert_signal(
        make_signal(category="made_up_category"),
        "Please send me the verification code.",
        source="nebius-nemotron",
    )

    assert result is None


def test_fabricated_evidence_quote_is_rejected():
    result = convert_signal(
        make_signal(
            evidence_quote="Give me your bank password.",
        ),
        "Hello, how are you today?",
        source="nebius-nemotron",
    )

    assert result is None


def test_model_confidence_is_scaled_by_source_reliability():
    result = convert_signal(
        make_signal(model_confidence=0.50),
        "Please send me the verification code.",
        source="nebius-nemotron",
    )

    assert result is not None
    assert result.confidence == 0.50 * SOURCE_RELIABILITY


def test_convert_analysis_filters_invalid_signals():
    analysis = LLMAnalysis(
        model_version="nemotron-test",
        signals=[
            make_signal(),
            make_signal(category="unknown-made-up"),
            make_signal(
                evidence_quote="This evidence does not exist in transcript."
            ),
        ],
    )

    result = convert_analysis(
        analysis,
        "Please send me the verification code.",
    )

    assert len(result) == 1
    assert result[0].category == ThreatCategory.SCAM