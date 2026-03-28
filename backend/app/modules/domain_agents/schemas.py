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
    decision_context: DecisionContext | None = None
    purpose_evaluation_id: str | None = Field(default=None, max_length=160)
    routing_decision_id: str | None = Field(default=None, max_length=160)
    execute_now: bool = Field(default=False)


class DomainSkillRunDraft(BaseModel):
    """Draft SkillRun request prepared by Domain Agent."""

    skill_key: str
    idempotency_key: str
    trigger_type: DomainTriggerType
    mission_id: Optional[str] = None
    causation_id: Optional[str] = None
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    decision_context_id: str | None = None
    purpose_evaluation_id: str | None = None
    routing_decision_id: str | None = None
    governance_snapshot: Dict[str, Any] = Field(default_factory=dict)


class DomainSkillRunPlanResponse(BaseModel):
    """Result of preparing (and optionally creating) SkillRuns."""

    resolution: DomainResolution
    review: DomainReviewDecision
    run_drafts: List[DomainSkillRunDraft] = Field(default_factory=list)
    created_run_ids: List[str] = Field(default_factory=list)
    supervisor_handoff: Optional[Dict[str, Any]] = None


class DecisionOutcome(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    MODIFIED_ACCEPT = "modified_accept"


class RequestedAutonomyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SensitivityClass(str, Enum):
    STANDARD = "standard"
    SENSITIVE = "sensitive"
    SENSITIVE_CORE = "sensitive_core"


class ControlMode(str, Enum):
    BRAIN_FIRST = "brain_first"
    HUMAN_OPTIONAL = "human_optional"
    HUMAN_REQUIRED = "human_required"


class DecisionContext(BaseModel):
    """Normalized context used for purpose and routing decisions."""

    decision_context_id: str = Field(..., min_length=1, max_length=160)
    tenant_id: str | None = Field(default=None, max_length=64)
    requested_by: str = Field(..., min_length=1, max_length=120)
    request_channel: str = Field(default="api", min_length=1, max_length=80)
    mission_id: str | None = Field(default=None, max_length=120)
    intent_summary: str = Field(..., min_length=1, max_length=2000)
    requested_autonomy_level: RequestedAutonomyLevel = Field(
        default=RequestedAutonomyLevel.MEDIUM
    )
    sensitivity_class: SensitivityClass = Field(default=SensitivityClass.STANDARD)
    context: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = Field(default=None, max_length=160)
    causation_id: str | None = Field(default=None, max_length=160)


class PurposeEvaluation(BaseModel):
    """Purpose and sovereignty evaluation outcome for a decision context."""

    purpose_evaluation_id: str | None = Field(default=None, max_length=160)
    decision_context_id: str = Field(..., min_length=1, max_length=160)
    purpose_profile_id: str = Field(..., min_length=1, max_length=120)
    outcome: DecisionOutcome
    purpose_score: float = Field(default=0.0, ge=0.0, le=1.0)
    sovereignty_score: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_human_review: bool = Field(default=False)
    required_modifications: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    governance_snapshot: Dict[str, Any] = Field(default_factory=dict)


class TaskProfile(BaseModel):
    """Routing-facing representation of a task."""

    task_profile_id: str = Field(..., min_length=1, max_length=160)
    task_class: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=4000)
    required_capabilities: List[str] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    required_worker_traits: List[str] = Field(default_factory=list)
    optimization_weights: Dict[str, float] = Field(default_factory=dict)
    routing_sensitivity: str = Field(default="medium", min_length=1, max_length=32)
    split_allowed: bool = Field(default=False)


class WorkerProfileProjection(BaseModel):
    """Projected worker profile used for upper-layer routing."""

    worker_id: str = Field(..., min_length=1, max_length=120)
    worker_class: str = Field(..., min_length=1, max_length=80)
    label: str = Field(..., min_length=1, max_length=200)
    capabilities: List[str] = Field(default_factory=list)
    sovereignty: float = Field(default=0.0, ge=0.0, le=1.0)
    trust: float = Field(default=0.0, ge=0.0, le=1.0)
    cost_efficiency: float = Field(default=0.0, ge=0.0, le=1.0)
    speed: float = Field(default=0.0, ge=0.0, le=1.0)
    context_capacity: float = Field(default=0.0, ge=0.0, le=1.0)
    autonomy_level: float = Field(default=0.0, ge=0.0, le=1.0)
    supports_sensitive_core: bool = Field(default=False)
    requires_sandbox: bool = Field(default=False)
    status: str = Field(default="active", min_length=1, max_length=40)


class RoutingDecision(BaseModel):
    """Upper-layer routing decision artifact before SkillRun creation."""

    routing_decision_id: str = Field(..., min_length=1, max_length=160)
    decision_context_id: str = Field(..., min_length=1, max_length=160)
    task_profile_id: str = Field(..., min_length=1, max_length=160)
    purpose_evaluation_id: str | None = Field(default=None, max_length=160)
    worker_candidates: List[str] = Field(default_factory=list)
    filtered_candidates: List[str] = Field(default_factory=list)
    scoring_breakdown: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    selected_worker: str | None = Field(default=None, max_length=120)
    selected_skill_or_plan: str | None = Field(default=None, max_length=200)
    strategy: str = Field(default="single_worker", min_length=1, max_length=64)
    reasoning: str = Field(default="", max_length=4000)


class PurposeEvaluationCreateRequest(BaseModel):
    decision_context: DecisionContext
    evaluation: PurposeEvaluation


class PurposeEvaluationResponse(BaseModel):
    id: str
    tenant_id: str | None = None
    decision_context_id: str
    purpose_profile_id: str
    outcome: DecisionOutcome
    purpose_score: float
    sovereignty_score: float
    requires_human_review: bool
    required_modifications: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    governance_snapshot: Dict[str, Any] = Field(default_factory=dict)
    mission_id: str | None = None
    correlation_id: str | None = None
    created_by: str

    model_config = {"from_attributes": True}


class PurposeEvaluationListResponse(BaseModel):
    items: List[PurposeEvaluationResponse] = Field(default_factory=list)
    total: int


class RoutingDecisionCreateRequest(BaseModel):
    decision_context: DecisionContext
    task_profile: TaskProfile
    decision: RoutingDecision


class RoutingDecisionResponse(BaseModel):
    id: str
    tenant_id: str | None = None
    decision_context_id: str
    task_profile_id: str
    purpose_evaluation_id: str | None = None
    worker_candidates: List[str] = Field(default_factory=list)
    filtered_candidates: List[str] = Field(default_factory=list)
    scoring_breakdown: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    selected_worker: str | None = None
    selected_skill_or_plan: str | None = None
    strategy: str
    reasoning: str
    governance_snapshot: Dict[str, Any] = Field(default_factory=dict)
    mission_id: str | None = None
    correlation_id: str | None = None
    created_by: str

    model_config = {"from_attributes": True}


class RoutingDecisionListResponse(BaseModel):
    items: List[RoutingDecisionResponse] = Field(default_factory=list)
    total: int


class RoutingMemoryRebuildRequest(BaseModel):
    task_profile_id: str = Field(..., min_length=1, max_length=160)
    limit: int = Field(default=200, ge=1, le=2000)


class RoutingMemoryProjectionResponse(BaseModel):
    id: str
    tenant_id: str | None = None
    task_profile_id: str
    task_profile_fingerprint: str
    worker_outcome_history: List[Dict[str, Any]] = Field(default_factory=list)
    summary_metrics: Dict[str, Any] = Field(default_factory=dict)
    routing_lessons: List[str] = Field(default_factory=list)
    sample_size: int = 0
    derived_from_runs: List[str] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class RoutingMemoryListResponse(BaseModel):
    items: List[RoutingMemoryProjectionResponse] = Field(default_factory=list)
    total: int


class RoutingReplayComparisonResponse(BaseModel):
    task_profile_id: str
    sample_size: int
    baseline_worker: str | None = None
    recommended_worker: str | None = None
    baseline_success_rate: float = 0.0
    recommended_success_rate: float = 0.0
    baseline_avg_cost: float | None = None
    recommended_avg_cost: float | None = None
    recommendation_reason: str = ""


class RoutingAdaptationProposalRequest(BaseModel):
    task_profile_id: str = Field(..., min_length=1, max_length=160)
    routing_memory_id: str | None = Field(default=None, max_length=160)
    proposed_changes: Dict[str, Any] = Field(default_factory=dict)
    sandbox_validated: bool = Field(default=False)
    validation_evidence: Dict[str, Any] = Field(default_factory=dict)


class RoutingAdaptationProposalResponse(BaseModel):
    id: str
    tenant_id: str | None = None
    task_profile_id: str
    routing_memory_id: str | None = None
    proposed_changes: Dict[str, Any] = Field(default_factory=dict)
    status: str
    sandbox_validated: bool = False
    validation_evidence: Dict[str, Any] = Field(default_factory=dict)
    block_reason: str | None = None
    created_by: str

    model_config = {"from_attributes": True}


class RoutingAdaptationProposalListResponse(BaseModel):
    items: List[RoutingAdaptationProposalResponse] = Field(default_factory=list)
    total: int


class RoutingAdaptationTransitionRequest(BaseModel):
    status: str = Field(..., min_length=1, max_length=32)
    block_reason: str | None = Field(default=None, max_length=500)
    validation_evidence_patch: Dict[str, Any] = Field(default_factory=dict)


class RoutingAdaptationSimulationRequest(BaseModel):
    task_profile_id: str = Field(..., min_length=1, max_length=160)
    proposed_changes: Dict[str, Any] = Field(default_factory=dict)


class RoutingAdaptationSimulationResponse(BaseModel):
    task_profile_id: str
    sandbox_mode: bool
    baseline_worker: str | None = None
    recommended_worker: str | None = None
    baseline_success_rate: float = 0.0
    recommended_success_rate: float = 0.0
    baseline_avg_cost: float | None = None
    recommended_avg_cost: float | None = None
    projected_delta: Dict[str, Any] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)
