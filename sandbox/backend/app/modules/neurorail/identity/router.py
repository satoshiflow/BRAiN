"""
NeuroRail Identity API Router.

Provides REST endpoints for:
- Creating trace chain entities
- Looking up entities by ID
- Reconstructing complete trace chains
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional
from datetime import datetime

from app.modules.neurorail.identity.service import (
    IdentityService,
    get_identity_service,
)
from app.modules.neurorail.identity.schemas import (
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
    EntityLookupResponse,
    TraceChainResponse,
)

router = APIRouter(prefix="/api/neurorail/v1/identity", tags=["NeuroRail Identity"])


# ============================================================================
# Mission Endpoints
# ============================================================================

@router.post("/mission", response_model=MissionIdentity, status_code=status.HTTP_201_CREATED)
async def create_mission(
    request: CreateMissionRequest,
    service: IdentityService = Depends(get_identity_service)
) -> MissionIdentity:
    """
    Create a new mission identity.

    Returns:
        Created mission with generated mission_id
    """
    try:
        return await service.create_mission(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create mission: {str(e)}"
        )


@router.get("/mission/{mission_id}", response_model=MissionIdentity)
async def get_mission(
    mission_id: str,
    service: IdentityService = Depends(get_identity_service)
) -> MissionIdentity:
    """
    Get mission identity by ID.

    Args:
        mission_id: Mission identifier (m_xxxxx)

    Returns:
        Mission identity

    Raises:
        404: Mission not found
    """
    mission = await service.get_mission(mission_id)
    if not mission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mission {mission_id} not found"
        )
    return mission


# ============================================================================
# Plan Endpoints
# ============================================================================

@router.post("/plan", response_model=PlanIdentity, status_code=status.HTTP_201_CREATED)
async def create_plan(
    request: CreatePlanRequest,
    service: IdentityService = Depends(get_identity_service)
) -> PlanIdentity:
    """
    Create a new plan identity.

    Returns:
        Created plan with generated plan_id

    Raises:
        400: Mission not found
    """
    try:
        return await service.create_plan(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create plan: {str(e)}"
        )


@router.get("/plan/{plan_id}", response_model=PlanIdentity)
async def get_plan(
    plan_id: str,
    service: IdentityService = Depends(get_identity_service)
) -> PlanIdentity:
    """
    Get plan identity by ID.

    Args:
        plan_id: Plan identifier (p_xxxxx)

    Returns:
        Plan identity

    Raises:
        404: Plan not found
    """
    plan = await service.get_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_id} not found"
        )
    return plan


# ============================================================================
# Job Endpoints
# ============================================================================

@router.post("/job", response_model=JobIdentity, status_code=status.HTTP_201_CREATED)
async def create_job(
    request: CreateJobRequest,
    service: IdentityService = Depends(get_identity_service)
) -> JobIdentity:
    """
    Create a new job identity.

    Returns:
        Created job with generated job_id

    Raises:
        400: Plan not found
    """
    try:
        return await service.create_job(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job: {str(e)}"
        )


@router.get("/job/{job_id}", response_model=JobIdentity)
async def get_job(
    job_id: str,
    service: IdentityService = Depends(get_identity_service)
) -> JobIdentity:
    """
    Get job identity by ID.

    Args:
        job_id: Job identifier (j_xxxxx)

    Returns:
        Job identity

    Raises:
        404: Job not found
    """
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    return job


# ============================================================================
# Attempt Endpoints
# ============================================================================

@router.post("/attempt", response_model=AttemptIdentity, status_code=status.HTTP_201_CREATED)
async def create_attempt(
    request: CreateAttemptRequest,
    service: IdentityService = Depends(get_identity_service)
) -> AttemptIdentity:
    """
    Create a new attempt identity.

    Returns:
        Created attempt with generated attempt_id

    Raises:
        400: Job not found
    """
    try:
        return await service.create_attempt(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create attempt: {str(e)}"
        )


@router.get("/attempt/{attempt_id}", response_model=AttemptIdentity)
async def get_attempt(
    attempt_id: str,
    service: IdentityService = Depends(get_identity_service)
) -> AttemptIdentity:
    """
    Get attempt identity by ID.

    Args:
        attempt_id: Attempt identifier (a_xxxxx)

    Returns:
        Attempt identity

    Raises:
        404: Attempt not found
    """
    attempt = await service.get_attempt(attempt_id)
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attempt {attempt_id} not found"
        )
    return attempt


# ============================================================================
# Resource Endpoints
# ============================================================================

@router.post("/resource", response_model=ResourceIdentity, status_code=status.HTTP_201_CREATED)
async def create_resource(
    request: CreateResourceRequest,
    service: IdentityService = Depends(get_identity_service)
) -> ResourceIdentity:
    """
    Create a new resource identity.

    Returns:
        Created resource with generated resource_uuid

    Raises:
        400: Attempt not found
    """
    try:
        return await service.create_resource(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create resource: {str(e)}"
        )


@router.get("/resource/{resource_uuid}", response_model=ResourceIdentity)
async def get_resource(
    resource_uuid: str,
    service: IdentityService = Depends(get_identity_service)
) -> ResourceIdentity:
    """
    Get resource identity by UUID.

    Args:
        resource_uuid: Resource identifier (r_xxxxx)

    Returns:
        Resource identity

    Raises:
        404: Resource not found
    """
    resource = await service.get_resource(resource_uuid)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource {resource_uuid} not found"
        )
    return resource


# ============================================================================
# Trace Chain Endpoints
# ============================================================================

@router.get("/trace/{entity_type}/{entity_id}", response_model=TraceChainResponse)
async def get_trace_chain(
    entity_type: str,
    entity_id: str,
    service: IdentityService = Depends(get_identity_service)
) -> TraceChainResponse:
    """
    Get complete trace chain for any entity.

    Reconstructs the full hierarchical context:
    mission → plan → job → attempt → resource

    Args:
        entity_type: Entity type (mission, plan, job, attempt, resource)
        entity_id: Entity identifier

    Returns:
        Complete trace chain

    Raises:
        400: Invalid entity type
        404: Entity not found
    """
    valid_types = ["mission", "plan", "job", "attempt", "resource"]
    if entity_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid entity type. Must be one of: {', '.join(valid_types)}"
        )

    try:
        trace_chain = await service.get_trace_chain(entity_type, entity_id)
        if not trace_chain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{entity_type.capitalize()} {entity_id} not found"
            )

        return TraceChainResponse(
            entity_type=entity_type,
            entity_id=entity_id,
            trace_chain=trace_chain,
            created_at=datetime.utcnow()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trace chain: {str(e)}"
        )
