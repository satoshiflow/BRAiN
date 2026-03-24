"""Core schemas for the Domain Agent layer."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

class DomainTriggerType(str, Enum):
    API = "api"
    SCHEDULE = "schedule"
    MISSION = "mission"
    RETRY = "retry"


class DomainStatus(str, Enum):
    """Lifecycle status for a domain registration."""

    ACTIVE = "active"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    DRAFT = "draft"


class DomainReviewOutcome(str, Enum):
    """Possible review outcomes for domain-owned reasoning."""

    PASS = "pass"
    REVISE = "revise"
    ESCALATE = "escalate"
    REJECT = "reject"


class DomainBudgetProfile(BaseModel):
    """Lightweight budget guardrails for a domain."""

    max_parallel_runs: int = Field(default=3, ge=1, le=50)
    max_specialists_per_task: int = Field(default=3, ge=1, le=20)
    max_estimated_cost_usd: float = Field(default=0.0, ge=0.0)


class DomainAgentConfig(BaseModel):
    """Registry-facing configuration for one domain."""

    tenant_id: Optional[str] = Field(default=None, max_length=64)
    owner_scope: str = Field(default="tenant", max_length=16)
    domain_key: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: DomainStatus = Field(default=DomainStatus.DRAFT)
    allowed_skill_keys: List[str] = Field(default_factory=list)
    allowed_capability_keys: List[str] = Field(default_factory=list)
    allowed_specialist_roles: List[str] = Field(default_factory=list)
    review_profile: Dict[str, Any] = Field(default_factory=dict)
    risk_profile: Dict[str, Any] = Field(default_factory=dict)
    escalation_profile: Dict[str, Any] = Field(default_factory=dict)
    budget_profile: DomainBudgetProfile = Field(default_factory=DomainBudgetProfile)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DomainDecompositionRequest(BaseModel):
    """Generic request shape for domain-aware decomposition."""

    domain_key: str = Field(..., min_length=1, max_length=100)
    task_name: str = Field(..., min_length=1, max_length=200)
    task_description: str = Field(default="", max_length=4000)
    mission_id: Optional[str] = Field(default=None, max_length=120)
    tenant_id: Optional[str] = Field(default=None, max_length=64)
    available_capabilities: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)


class SpecialistCandidate(BaseModel):
    """Candidate specialist selected for domain work."""

    agent_id: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., min_length=1, max_length=100)
    score: float = Field(default=0.0, ge=0.0)
    reasons: List[str] = Field(default_factory=list)


class DomainResolution(BaseModel):
    """Outcome of resolving a task into domain-owned next steps."""

    domain_key: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    selected_skill_keys: List[str] = Field(default_factory=list)
    selected_capability_keys: List[str] = Field(default_factory=list)
    selected_specialists: List[SpecialistCandidate] = Field(default_factory=list)
    decomposition_notes: List[str] = Field(default_factory=list)
    requires_supervisor_review: bool = Field(default=False)


class DomainReviewDecision(BaseModel):
    """Domain-local review result before or after execution."""

    domain_key: str
    outcome: DomainReviewOutcome
    summary: str = Field(..., min_length=1, max_length=1000)
    reasons: List[str] = Field(default_factory=list)
    should_escalate: bool = Field(default=False)
    recommended_next_actions: List[str] = Field(default_factory=list)


class DomainSkillRunPlanRequest(BaseModel):
    """Request to convert a domain decomposition into SkillRun requests."""

    decomposition: DomainDecompositionRequest
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    trigger_type: DomainTriggerType = Field(default=DomainTriggerType.MISSION)
    mission_id: Optional[str] = Field(default=None, max_length=120)
    causation_id: Optional[str] = Field(default=None, max_length=160)
    supervisor_escalation_id: Optional[str] = Field(default=None, max_length=200)
    execute_now: bool = Field(default=False)


class DomainSkillRunDraft(BaseModel):
    """Draft SkillRun request prepared by Domain Agent."""

    skill_key: str
    idempotency_key: str
    trigger_type: DomainTriggerType
    mission_id: Optional[str] = None
    causation_id: Optional[str] = None
    input_payload: Dict[str, Any] = Field(default_factory=dict)


class DomainSkillRunPlanResponse(BaseModel):
    """Result of preparing (and optionally creating) SkillRuns."""

    resolution: DomainResolution
    review: DomainReviewDecision
    run_drafts: List[DomainSkillRunDraft] = Field(default_factory=list)
    created_run_ids: List[str] = Field(default_factory=list)
    supervisor_handoff: Optional[Dict[str, Any]] = None
