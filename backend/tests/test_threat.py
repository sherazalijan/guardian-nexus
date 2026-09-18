from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.enums import ThreatCategory
from app.models.threat import ThreatSignal


def make_threat(**overrides):
    data = {
        "category": ThreatCategory.SCAM,
        "indicator": "urgent_payment",
        "evidence": "Caller demanded immediate payment.",
        "confidence": 0.95,
        "source": "test",
        "timestamp": datetime.now(timezone.utc),
    }
    data.update(overrides)
    return data


def test_valid_threat_signal():
    signal = ThreatSignal(**make_threat())

    assert signal.category == ThreatCategory.SCAM
    assert signal.confidence == 0.95
    assert signal.metadata == {}


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_must_be_between_zero_and_one(confidence):
    with pytest.raises(ValidationError):
        ThreatSignal(**make_threat(confidence=confidence))


@pytest.mark.parametrize(
    "field",
    ["indicator", "evidence", "source"],
)
def test_required_text_fields_cannot_be_empty(field):
    with pytest.raises(ValidationError):
        ThreatSignal(**make_threat(**{field: ""}))
