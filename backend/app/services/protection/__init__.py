"""Guardian Nexus real-time protection layer.

Converts existing scam-detection/risk-engine output into the user-facing
protection contract defined in `app.models.protection`. See
`app.services.protection.service.ProtectionService` for the entry point.
"""

from app.services.protection.service import (
    ProtectionAnalysisResult,
    ProtectionService,
)

__all__ = ["ProtectionAnalysisResult", "ProtectionService"]
