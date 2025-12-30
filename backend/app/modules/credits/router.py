"""Credits API Router - Credit system v2.0 endpoints.

Implements Myzel-Hybrid-Charta:
- Agent/mission account management
- Credit consumption and refunds
- Transaction history and ledger integrity
- Regeneration control
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

from app.core.security import Principal, get_current_principal
from . import service
from .schemas import CreditsHealth, CreditsInfo

router = APIRouter(
    prefix="/api/credits",
    tags=["credits"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateAgentAccountRequest(BaseModel):
    agent_id: str
    skill_level: Optional[float] = Field(None, ge=0.0, le=1.0)


class CreateMissionBudgetRequest(BaseModel):
    mission_id: str
    complexity: float = Field(1.0, ge=0.5, le=5.0)
    estimated_duration_hours: float = Field(1.0, gt=0.0)


class ConsumeCreditsRequest(BaseModel):
    entity_id: str
    amount: float = Field(gt=0.0)
    reason: str
    metadata: Optional[dict] = None


class CheckSufficientCreditsRequest(BaseModel):
    entity_id: str
    required_amount: float = Field(gt=0.0)


class WithdrawCreditsRequest(BaseModel):
    entity_id: str
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    reason: str
    metadata: Optional[dict] = None


class RefundCreditsRequest(BaseModel):
    entity_id: str
    original_allocation: float = Field(gt=0.0)
    work_completed_percentage: float = Field(ge=0.0, le=1.0)
    reason: str


# ============================================================================
# Agent & Mission Account Endpoints
# ============================================================================

@router.post("/agents/create")
async def create_agent_account(
    request: CreateAgentAccountRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Create credit account for new agent."""
    try:
        return await service.create_agent_account(
            agent_id=request.agent_id,
            skill_level=request.skill_level,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/missions/create")
async def create_mission_budget(
    request: CreateMissionBudgetRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Create credit budget for new mission."""
    try:
        return await service.create_mission_budget(
            mission_id=request.mission_id,
            complexity=request.complexity,
            estimated_duration_hours=request.estimated_duration_hours,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Credit Operations Endpoints
# ============================================================================

@router.post("/consume")
async def consume_credits(
    request: ConsumeCreditsRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Consume credits from entity."""
    try:
        return await service.consume_credits(
            entity_id=request.entity_id,
            amount=request.amount,
            reason=request.reason,
            metadata=request.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/check-sufficient")
async def check_sufficient_credits(
    request: CheckSufficientCreditsRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Check if entity has sufficient credits."""
    has_sufficient = await service.check_sufficient_credits(
        entity_id=request.entity_id,
        required_amount=request.required_amount,
    )
    current_balance = await service.get_balance(request.entity_id)

    return {
        "entity_id": request.entity_id,
        "required_amount": request.required_amount,
        "current_balance": current_balance,
        "has_sufficient": has_sufficient,
    }


@router.post("/withdraw")
async def withdraw_credits(
    request: WithdrawCreditsRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Withdraw credits (ImmuneService Entzug)."""
    try:
        return await service.withdraw_credits(
            entity_id=request.entity_id,
            severity=request.severity,
            reason=request.reason,
            metadata=request.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refund")
async def refund_credits(
    request: RefundCreditsRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Refund credits (Synergie-Mechanik)."""
    try:
        return await service.refund_credits(
            entity_id=request.entity_id,
            original_allocation=request.original_allocation,
            work_completed_percentage=request.work_completed_percentage,
            reason=request.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Query Endpoints
# ============================================================================

@router.get("/balance/{entity_id}")
async def get_balance(
    entity_id: str,
    principal: Principal = Depends(get_current_principal),
):
    """Get current credit balance for entity."""
    balance = await service.get_balance(entity_id)
    return {
        "entity_id": entity_id,
        "balance": balance,
    }


@router.get("/history")
async def get_transaction_history(
    principal: Principal = Depends(get_current_principal),
    entity_id: Optional[str] = None,
    transaction_type: Optional[str] = None,
    limit: int = 100,
):
    """Get transaction history with optional filters."""
    return await service.get_transaction_history(
        entity_id=entity_id,
        transaction_type=transaction_type,
        limit=limit,
    )


@router.get("/ledger/statistics")
async def get_ledger_statistics(
    principal: Principal = Depends(get_current_principal),
):
    """Get ledger statistics."""
    return await service.get_ledger_statistics()


@router.get("/ledger/verify-integrity")
async def verify_ledger_integrity(
    principal: Principal = Depends(get_current_principal),
):
    """Verify ledger integrity (HMAC-SHA256 signatures)."""
    return await service.verify_ledger_integrity()


# ============================================================================
# Lifecycle Management Endpoints
# ============================================================================

@router.post("/regeneration/start")
async def start_regeneration(
    principal: Principal = Depends(get_current_principal),
):
    """Start background credit regeneration."""
    return await service.start_regeneration()


@router.post("/regeneration/stop")
async def stop_regeneration(
    principal: Principal = Depends(get_current_principal),
):
    """Stop background credit regeneration."""
    return await service.stop_regeneration()


# ============================================================================
# Health & Info (Legacy compatibility)
# ============================================================================

@router.get("/health", response_model=CreditsHealth)
async def credits_health(
    principal: Principal = Depends(get_current_principal),
):
    """Get Credits module health status."""
    return await service.get_health()


@router.get("/info", response_model=CreditsInfo)
async def credits_info(
    principal: Principal = Depends(get_current_principal),
):
    """Get Credits module information."""
    return await service.get_info()


# ============================================================================
# Phase 5-7: Advanced Credit System Endpoints
# ============================================================================

# --- Edge-of-Chaos Controller ---

@router.post("/eoc/regulate")
async def regulate_system(
    principal: Principal = Depends(get_current_principal),
    eoc_score: Optional[float] = None,
):
    """Regulate system based on Edge-of-Chaos score."""
    from .eoc_controller import get_eoc_controller

    controller = get_eoc_controller()
    decision = await controller.regulate(eoc_score)
    return decision


@router.get("/eoc/status")
async def get_eoc_status(
    principal: Principal = Depends(get_current_principal),
):
    """Get Edge-of-Chaos controller status."""
    from .eoc_controller import get_eoc_controller

    controller = get_eoc_controller()
    return controller.get_regulation_status()


@router.get("/eoc/history")
async def get_eoc_history(
    principal: Principal = Depends(get_current_principal),
    limit: int = 50,
):
    """Get regulation history."""
    from .eoc_controller import get_eoc_controller

    controller = get_eoc_controller()
    return controller.get_regulation_history(limit=limit)


# --- Mission Rating System ---

class RegisterAgentRequest(BaseModel):
    agent_id: str
    skills: Dict[str, float]
    specializations: List[str]


class FindMatchRequest(BaseModel):
    mission_id: str
    required_skills: Dict[str, float]
    complexity: float = 1.0
    estimated_duration_hours: float = 1.0
    priority: int = 5
    available_agents: Optional[List[str]] = None


class RateMissionRequest(BaseModel):
    mission_id: str
    agent_id: str
    quality_score: float = Field(ge=0.0, le=1.0)
    efficiency_score: float = Field(ge=0.0, le=1.0)
    collaboration_score: float = Field(ge=0.0, le=1.0)
    actual_duration_hours: float
    credits_consumed: float
    credits_allocated: float
    agent_feedback: Optional[str] = None
    supervisor_feedback: Optional[str] = None


@router.post("/rating/agents/register")
async def register_agent_profile(
    request: RegisterAgentRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Register agent skill profile."""
    from .mission_rating import get_rating_system

    rating_system = get_rating_system()
    profile = rating_system.register_agent(
        agent_id=request.agent_id,
        skills=request.skills,
        specializations=request.specializations,
    )

    return {
        "agent_id": profile.agent_id,
        "skills": profile.skills,
        "specializations": profile.specializations,
        "experience_level": profile.experience_level,
        "collaboration_score": profile.collaboration_score,
        "success_rate": profile.success_rate,
    }


@router.post("/rating/missions/match")
async def find_agent_matches(
    request: FindMatchRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Find best agent matches for mission."""
    from .mission_rating import get_rating_system, MissionRequirements

    rating_system = get_rating_system()
    requirements = MissionRequirements(
        mission_id=request.mission_id,
        required_skills=request.required_skills,
        complexity=request.complexity,
        estimated_duration_hours=request.estimated_duration_hours,
        priority=request.priority,
    )

    matches = rating_system.find_best_match(
        requirements=requirements,
        available_agents=request.available_agents,
    )

    return {"matches": matches}


@router.post("/rating/missions/rate")
async def rate_mission_performance(
    request: RateMissionRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Rate mission performance."""
    from .mission_rating import get_rating_system

    rating_system = get_rating_system()
    rating = rating_system.rate_mission(
        mission_id=request.mission_id,
        agent_id=request.agent_id,
        quality_score=request.quality_score,
        efficiency_score=request.efficiency_score,
        collaboration_score=request.collaboration_score,
        actual_duration_hours=request.actual_duration_hours,
        credits_consumed=request.credits_consumed,
        credits_allocated=request.credits_allocated,
        agent_feedback=request.agent_feedback,
        supervisor_feedback=request.supervisor_feedback,
    )

    return {
        "mission_id": rating.mission_id,
        "agent_id": rating.agent_id,
        "overall_score": rating.overall_score,
        "quality_score": rating.quality_score,
        "efficiency_score": rating.efficiency_score,
        "collaboration_score": rating.collaboration_score,
    }


@router.get("/rating/agents/{agent_id}/statistics")
async def get_agent_rating_statistics(
    agent_id: str,
    principal: Principal = Depends(get_current_principal),
):
    """Get agent rating statistics."""
    from .mission_rating import get_rating_system

    rating_system = get_rating_system()
    stats = rating_system.get_agent_statistics(agent_id)

    if not stats:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    return stats


# --- Evolution Analyzer ---

@router.post("/evolution/analyze")
async def analyze_system_evolution(
    principal: Principal = Depends(get_current_principal),
):
    """Analyze system evolution and generate recommendations."""
    from .evolution_analyzer import get_evolution_analyzer

    # Get system metrics (would come from RuntimeAuditor/SystemHealth)
    system_metrics = {}

    # Get ledger stats
    ledger_stats = await service.get_ledger_statistics()

    # Get agent stats (would come from MissionRatingSystem)
    agent_stats = []

    analyzer = get_evolution_analyzer()
    analysis = await analyzer.analyze_system_evolution(
        system_metrics=system_metrics,
        ledger_stats=ledger_stats,
        agent_stats=agent_stats,
    )

    return analysis


@router.get("/evolution/recommendations")
async def get_evolution_recommendations(
    principal: Principal = Depends(get_current_principal),
    limit: int = 10,
    requires_approval_only: bool = False,
):
    """Get growth recommendations."""
    from .evolution_analyzer import get_evolution_analyzer

    analyzer = get_evolution_analyzer()
    recommendations = analyzer.get_recent_recommendations(
        limit=limit,
        requires_approval_only=requires_approval_only,
    )

    return {
        "recommendations": [
            {
                "recommendation_id": r.recommendation_id,
                "recommendation_type": r.recommendation_type.value,
                "priority": r.priority,
                "title": r.title,
                "description": r.description,
                "reasoning": r.reasoning,
                "expected_impact": r.expected_impact,
                "requires_human_approval": r.requires_human_approval,
                "conditions": r.conditions,
                "risks": r.risks,
                "created_at": r.created_at.isoformat(),
            }
            for r in recommendations
        ]
    }


# --- Synergie-Mechanik ---

class RegisterMissionRequest(BaseModel):
    mission_id: str
    description: str
    requirements: Dict


class RecordCollaborationRequest(BaseModel):
    primary_agent_id: str
    collaborating_agent_id: str
    mission_id: str
    collaboration_type: str
    value_added: float = Field(ge=0.0, le=1.0)


@router.post("/synergie/missions/register")
async def register_mission_signature(
    request: RegisterMissionRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Register mission for deduplication tracking."""
    from .synergie_mechanik import get_synergie_mechanik

    synergie = get_synergie_mechanik()
    signature = synergie.register_mission(
        mission_id=request.mission_id,
        description=request.description,
        requirements=request.requirements,
    )

    return {
        "mission_id": signature.mission_id,
        "signature_hash": signature.signature_hash,
        "created_at": signature.created_at.isoformat(),
    }


@router.get("/synergie/missions/{mission_id}/duplicates")
async def check_mission_duplicates(
    mission_id: str,
    principal: Principal = Depends(get_current_principal),
):
    """Check for duplicate missions."""
    from .synergie_mechanik import get_synergie_mechanik

    synergie = get_synergie_mechanik()
    duplicates = synergie.check_for_duplicates(mission_id)

    return {"duplicates": duplicates}


@router.post("/synergie/collaboration/record")
async def record_collaboration_event(
    request: RecordCollaborationRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Record collaboration event."""
    from .synergie_mechanik import get_synergie_mechanik

    synergie = get_synergie_mechanik()
    event = synergie.record_collaboration(
        primary_agent_id=request.primary_agent_id,
        collaborating_agent_id=request.collaborating_agent_id,
        mission_id=request.mission_id,
        collaboration_type=request.collaboration_type,
        value_added=request.value_added,
    )

    return {
        "event_id": event.event_id,
        "timestamp": event.timestamp.isoformat(),
    }


@router.get("/synergie/statistics")
async def get_synergie_statistics(
    principal: Principal = Depends(get_current_principal),
):
    """Get Synergie-Mechanik statistics."""
    from .synergie_mechanik import get_synergie_mechanik

    synergie = get_synergie_mechanik()
    reuse_stats = synergie.get_reuse_statistics()
    collab_stats = synergie.get_collaboration_statistics()

    return {
        "reuse": reuse_stats,
        "collaboration": collab_stats,
    }


# --- Human Approval Gates ---

class RequestApprovalRequest(BaseModel):
    action_type: str
    action_description: str
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    requested_by: str
    context: Dict
    reasoning: str


class ApproveRequestRequest(BaseModel):
    request_id: str
    approver_id: str
    justification: Optional[str] = None


class RejectRequestRequest(BaseModel):
    request_id: str
    approver_id: str
    reason: str


@router.post("/approval/request")
async def request_human_approval(
    request: RequestApprovalRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Request human approval for action."""
    from .approval_gates import get_approval_gates, ActionSeverity

    gates = get_approval_gates()
    approval_request = gates.request_approval(
        action_type=request.action_type,
        action_description=request.action_description,
        severity=ActionSeverity(request.severity),
        requested_by=request.requested_by,
        context=request.context,
        reasoning=request.reasoning,
    )

    return gates._format_request_status(approval_request)


@router.post("/approval/approve")
async def approve_approval_request(
    request: ApproveRequestRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Approve pending request."""
    from .approval_gates import get_approval_gates

    gates = get_approval_gates()
    return gates.approve(
        request_id=request.request_id,
        approver_id=request.approver_id,
        justification=request.justification,
    )


@router.post("/approval/reject")
async def reject_approval_request(
    request: RejectRequestRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Reject pending request."""
    from .approval_gates import get_approval_gates

    gates = get_approval_gates()
    return gates.reject(
        request_id=request.request_id,
        approver_id=request.approver_id,
        reason=request.reason,
    )


@router.get("/approval/{request_id}/status")
async def check_approval_status(
    request_id: str,
    principal: Principal = Depends(get_current_principal),
):
    """Check approval request status."""
    from .approval_gates import get_approval_gates

    gates = get_approval_gates()
    return gates.check_status(request_id)


@router.get("/approval/pending")
async def get_pending_approvals(
    principal: Principal = Depends(get_current_principal),
    severity: Optional[str] = None,
):
    """Get pending approval requests."""
    from .approval_gates import get_approval_gates, ActionSeverity

    gates = get_approval_gates()
    severity_enum = ActionSeverity(severity) if severity else None
    pending = gates.get_pending_approvals(severity=severity_enum)

    return {"pending_approvals": pending}


@router.get("/approval/audit")
async def get_approval_audit_trail(
    principal: Principal = Depends(get_current_principal),
    limit: int = 50,
):
    """Get approval audit trail."""
    from .approval_gates import get_approval_gates

    gates = get_approval_gates()
    audit = gates.get_audit_trail(limit=limit)

    return {"audit_trail": audit}


# --- Shared Resource Pools ---

class ContributeResourceRequest(BaseModel):
    contributor_id: str
    resource_type: str
    title: str
    description: str
    content: Dict
    tags: List[str]
    access_policy: str = "public"
    allowed_agents: Optional[List[str]] = None


@router.post("/resources/contribute")
async def contribute_resource(
    request: ContributeResourceRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Contribute resource to shared pool."""
    from .resource_pools import get_resource_pools, ResourceType, AccessPolicy

    pools = get_resource_pools()
    result = pools.contribute_resource(
        contributor_id=request.contributor_id,
        resource_type=ResourceType(request.resource_type),
        title=request.title,
        description=request.description,
        content=request.content,
        tags=request.tags,
        access_policy=AccessPolicy(request.access_policy),
        allowed_agents=set(request.allowed_agents) if request.allowed_agents else None,
    )

    return result


@router.get("/resources/search")
async def search_resources(
    principal: Principal = Depends(get_current_principal),
    query: Optional[str] = None,
    resource_type: Optional[str] = None,
    tags: Optional[str] = None,
    min_quality: float = 0.0,
    verified_only: bool = False,
):
    """Search shared resources."""
    from .resource_pools import get_resource_pools, ResourceType

    pools = get_resource_pools()

    tags_list = tags.split(",") if tags else None
    resource_type_enum = ResourceType(resource_type) if resource_type else None

    results = pools.search_resources(
        query=query,
        resource_type=resource_type_enum,
        tags=tags_list,
        min_quality=min_quality,
        verified_only=verified_only,
    )

    return {"resources": results}


@router.get("/resources/{resource_id}")
async def access_resource(
    resource_id: str,
    principal: Principal = Depends(get_current_principal),
    user_id: str = "system",
    usage_type: str = "view",
):
    """Access shared resource."""
    from .resource_pools import get_resource_pools

    pools = get_resource_pools()
    resource = pools.access_resource(
        resource_id=resource_id,
        user_id=user_id,
        usage_type=usage_type,
    )

    if not resource:
        raise HTTPException(status_code=403, detail="Access denied")

    return resource


@router.get("/resources/contributor/{contributor_id}/rewards")
async def get_contribution_rewards(
    contributor_id: str,
    principal: Principal = Depends(get_current_principal),
):
    """Get contribution rewards for agent."""
    from .resource_pools import get_resource_pools

    pools = get_resource_pools()
    rewards = pools.calculate_contribution_rewards(contributor_id)

    return rewards


@router.get("/resources/statistics")
async def get_resource_pool_statistics(
    principal: Principal = Depends(get_current_principal),
):
    """Get resource pool statistics."""
    from .resource_pools import get_resource_pools

    pools = get_resource_pools()
    stats = pools.get_pool_statistics()

    return stats
