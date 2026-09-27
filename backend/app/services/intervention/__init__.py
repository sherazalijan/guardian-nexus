"""Guardian Nexus real-time intervention layer (Phase 3).

Converts existing ProtectionEvents into the intervention contract defined
in `app.models.intervention`. See
`app.services.intervention.policy.InterventionPolicyService`.
"""

from app.services.intervention.policy import InterventionPolicyService

__all__ = ["InterventionPolicyService"]
