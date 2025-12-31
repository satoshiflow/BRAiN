"""
Governor Module (Phase 1 Stub).

Provides minimal governance for execution mode selection:
- Direct vs. Rail mode decision
- Dry-run logging (no enforcement)
- Shadow evaluation support

Phase 1: Observation only
Phase 2: Full budget enforcement and manifest-driven governance
"""

from backend.app.modules.governor.schemas import (
    ModeDecision,
    ManifestSpec,
    ShadowEvaluation,
    DecisionRequest,
)
from backend.app.modules.governor.service import (
    GovernorService,
    get_governor_service,
)
from backend.app.modules.governor.router import router

__all__ = [
    # Schemas
    "ModeDecision",
    "ManifestSpec",
    "ShadowEvaluation",
    "DecisionRequest",
    # Service
    "GovernorService",
    "get_governor_service",
    # Router
    "router",
]
