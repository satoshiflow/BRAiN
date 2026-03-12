"""Domain Agent package.

This package introduces BRAiN's domain-aware orchestration layer.

It is intentionally small in the first iteration so that future implementers can
extend it without being locked into a premature runtime design.
"""

from .schemas import (
    DomainAgentConfig,
    DomainDecompositionRequest,
    DomainSkillRunDraft,
    DomainSkillRunPlanRequest,
    DomainSkillRunPlanResponse,
    DomainTriggerType,
    DomainResolution,
    DomainReviewDecision,
    SpecialistCandidate,
)
from .service import DomainAgentRegistry, DomainAgentService
from .service import get_domain_agent_registry, get_domain_agent_service

__all__ = [
    "DomainAgentConfig",
    "DomainAgentRegistry",
    "DomainAgentService",
    "DomainDecompositionRequest",
    "DomainSkillRunDraft",
    "DomainSkillRunPlanRequest",
    "DomainSkillRunPlanResponse",
    "DomainTriggerType",
    "DomainResolution",
    "DomainReviewDecision",
    "SpecialistCandidate",
    "get_domain_agent_registry",
    "get_domain_agent_service",
]
