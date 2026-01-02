"""
Governor v1 Package (Phase 2a)

Agent creation governance with deterministic policy evaluation.

Main exports:
- Governor: Main governance service
- GovernorApproval: Compatibility wrapper for Genesis integration
- DecisionRequest: Request model
- DecisionResult: Result model
- EffectiveConstraints: Constraints model
- GovernorConfig: Configuration

Example:
    >>> from backend.brain.governor import Governor, GovernorConfig
    >>> governor = Governor(redis, audit, config=GovernorConfig())
    >>> result = await governor.evaluate_creation(request)
"""

from backend.brain.governor.constraints.defaults import (
    get_agent_type_caps,
    get_default_constraints,
)
from backend.brain.governor.constraints.schema import (
    BudgetConstraints,
    CapabilityConstraints,
    EffectiveConstraints,
    LifecycleConstraints,
    LockConstraints,
    RuntimeConstraints,
)
from backend.brain.governor.decision.models import (
    ActorContext,
    DecisionRequest,
    DecisionResult,
    DecisionType,
    ReasonCode,
    RequestContext,
    RiskTier,
)
from backend.brain.governor.events import GovernorEvents
from backend.brain.governor.governor import (
    ApprovalResponse,
    Governor,
    GovernorApproval,
    GovernorConfig,
)


__all__ = [
    # Main service
    "Governor",
    "GovernorApproval",
    "GovernorConfig",
    "ApprovalResponse",
    # Models
    "DecisionRequest",
    "DecisionResult",
    "DecisionType",
    "ReasonCode",
    "RiskTier",
    "ActorContext",
    "RequestContext",
    # Constraints
    "EffectiveConstraints",
    "BudgetConstraints",
    "CapabilityConstraints",
    "RuntimeConstraints",
    "LifecycleConstraints",
    "LockConstraints",
    "get_default_constraints",
    "get_agent_type_caps",
    # Events
    "GovernorEvents",
]
