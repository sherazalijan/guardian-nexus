
"""Tests for LLM analysis to ThreatSignal conversion."""

from app.models.enums import ThreatCategory
from app.models.llm_analysis import LLMAnalysis, LLMSignal
from app.services.llm_analysis.converter import (
    SOURCE_RELIABILITY,
    calculate_evidence_strength,
    calculate_signal_confidence,
    convert_analysis,
    convert_signal,
)


def make_signal(
    *,
    category: str = "scam",
    evidence_quote: str = "Please send me the verification code.",
    model_confidence: float = 1.0,
) -> LLMSignal:
    """Create a valid test LLM signal."""

    return LLMSignal(
        category=category,
        evidence_quote=evidence_quote,
        model_confidence=model_confidence,
        reasoning="The transcript contains a suspicious verification request.",
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
    assert result.source == "nebius-nemotron"
    assert result.confidence == SOURCE_RELIABILITY


def test_category_is_normalized():
    result = convert_signal(
        make_signal(category="  SCAM  "),
        "Please send me the verification code.",
    )

    assert result is not None
    assert result.category == ThreatCategory.SCAM
    assert result.indicator == "scam"


def test_unknown_category_is_rejected():
    result = convert_signal(
        make_signal(category="super_scam"),
        "Please send me the verification code.",
    )

    assert result is None


def test_fabricated_evidence_is_rejected():
    result = convert_signal(
        make_signal(
            evidence_quote="The victim transferred ten million dollars."
        ),
        "Please send me the verification code.",
    )

    assert result is None


def test_evidence_strength_is_one_for_direct_quote():
    signal = make_signal()

    strength = calculate_evidence_strength(
        signal,
        "Please send me the verification code.",
    )

    assert strength == 1.0


def test_evidence_strength_is_zero_for_missing_quote():
    signal = make_signal(
        evidence_quote="This sentence does not exist."
    )

    strength = calculate_evidence_strength(
        signal,
        "Please send me the verification code.",
    )

    assert strength == 0.0


def test_model_confidence_is_scaled_by_source_reliability():
    signal = make_signal(model_confidence=0.50)

    confidence = calculate_signal_confidence(
        signal,
        evidence_strength=1.0,
    )

    assert confidence == 0.50 * SOURCE_RELIABILITY


def test_zero_evidence_produces_zero_confidence():
    signal = make_signal(model_confidence=1.0)

    confidence = calculate_signal_confidence(
        signal,
        evidence_strength=0.0,
    )

    assert confidence == 0.0


def test_confidence_is_clamped_to_one():
    signal = make_signal(model_confidence=1.0)

    confidence = calculate_signal_confidence(
        signal,
        evidence_strength=2.0,
    )

    assert confidence == 1.0


def test_converted_confidence_is_between_zero_and_one():
    result = convert_signal(
        make_signal(model_confidence=0.75),
        "Please send me the verification code.",
    )

    assert result is not None
    assert 0.0 <= result.confidence <= 1.0


def test_source_is_preserved():
    result = convert_signal(
        make_signal(),
        "Please send me the verification code.",
        source="test-provider",
    )

    assert result is not None
    assert result.source == "test-provider"


def test_metadata_contains_reasoning():
    result = convert_signal(
        make_signal(),
        "Please send me the verification code.",
    )

    assert result is not None
    assert result.metadata["reasoning"] == (
        "The transcript contains a suspicious verification request."
    )


def test_metadata_contains_confidence_components():
    result = convert_signal(
        make_signal(model_confidence=0.75),
        "Please send me the verification code.",
    )

    assert result is not None

    assert result.metadata["model_confidence"] == 0.75
    assert result.metadata["evidence_strength"] == 1.0
    assert result.metadata["source_reliability"] == SOURCE_RELIABILITY


def test_convert_analysis_filters_invalid_signals():
    transcript = "Please send me the verification code."

    analysis = LLMAnalysis(
        model_version="test-model",
        signals=[
            make_signal(category="scam"),
            make_signal(category="unknown_attack"),
            make_signal(
                category="phishing",
                evidence_quote="This evidence is not in the transcript.",
            ),
        ],
    )

    results = convert_analysis(
        analysis,
        transcript,
    )

    assert len(results) == 1
    assert results[0].category == ThreatCategory.SCAM


def test_convert_analysis_converts_multiple_valid_signals():
    transcript = (
        "Please send me the verification code. "
        "Click this link to verify your account."
    )

    analysis = LLMAnalysis(
        model_version="test-model",
        signals=[
            make_signal(
                category="scam",
                evidence_quote="Please send me the verification code.",
            ),
            make_signal(
                category="phishing",
                evidence_quote="Click this link to verify your account.",
            ),
        ],
    )

    results = convert_analysis(
        analysis,
        transcript,
    )

    assert len(results) == 2
    assert results[0].category == ThreatCategory.SCAM
    assert results[1].category == ThreatCategory.PHISHING
