"""Threat signal normalization and deterministic deduplication."""

from collections.abc import Iterable

from app.models.threat import ThreatSignal


def normalize_indicator(indicator: str) -> str:
    """Normalize an indicator for deterministic comparison."""
    return " ".join(indicator.strip().lower().split())


def normalize_source(source: str) -> str:
    """Normalize a signal source for deterministic comparison."""
    return " ".join(source.strip().lower().split())


def normalize_signal(signal: ThreatSignal) -> ThreatSignal:
    """Return a normalized copy of a threat signal."""
    return signal.model_copy(
        update={
            "indicator": normalize_indicator(signal.indicator),
            "source": normalize_source(signal.source),
        }
    )


def deduplicate_signals(
    signals: Iterable[ThreatSignal],
) -> list[ThreatSignal]:
    """
    Deduplicate signals representing the same normalized evidence.

    When duplicate evidence is found, retain the signal with the
    highest confidence. Timestamps and metadata from the retained
    signal are preserved.
    """
    deduplicated: dict[tuple[str, str, str], ThreatSignal] = {}

    for raw_signal in signals:
        signal = normalize_signal(raw_signal)

        key = (
            signal.category.value,
            signal.indicator,
            signal.source,
        )

        existing = deduplicated.get(key)

        if existing is None or signal.confidence > existing.confidence:
            deduplicated[key] = signal

    return list(deduplicated.values())