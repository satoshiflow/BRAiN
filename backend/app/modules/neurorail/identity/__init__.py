"""
NeuroRail Identity Module.

Manages the hierarchical trace chain:
mission_id → plan_id → job_id → attempt_id → resource_uuid
"""

from backend.app.modules.neurorail.identity.schemas import (
    MissionIdentity,
    PlanIdentity,
    JobIdentity,
    AttemptIdentity,
    ResourceIdentity,
    TraceChain,
    CreateMissionRequest,
    CreatePlanRequest,
    CreateJobRequest,
    CreateAttemptRequest,
    CreateResourceRequest,
)
from backend.app.modules.neurorail.identity.service import (
    IdentityService,
    get_identity_service,
)
from backend.app.modules.neurorail.identity.router import router

__all__ = [
    # Schemas
    "MissionIdentity",
    "PlanIdentity",
    "JobIdentity",
    "AttemptIdentity",
    "ResourceIdentity",
    "TraceChain",
    "CreateMissionRequest",
    "CreatePlanRequest",
    "CreateJobRequest",
    "CreateAttemptRequest",
    "CreateResourceRequest",
    # Service
    "IdentityService",
    "get_identity_service",
    # Router
    "router",
]
