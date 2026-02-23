"""
Skills Module - API Router

FastAPI endpoints for skill management and execution.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth_deps import require_role, get_current_principal, Principal, require_auth
from app.core.security import UserRole
from app.core.rate_limit import limiter, RateLimits

from .schemas import (
    SkillCreate,
    SkillUpdate,
    SkillResponse,
    SkillListResponse,
    SkillExecutionRequest,
    SkillExecutionResult,
    SkillCategory,
    SkillCategoriesResponse,
)
from .service import get_skill_service, SkillService
from .models import SkillModel


router = APIRouter(prefix="/api/skills", tags=["skills"])


# ============================================================================
# Helper Functions
# ============================================================================

def skill_to_response(skill: SkillModel) -> SkillResponse:
    """Convert a SkillModel to SkillResponse"""
    from .schemas import SkillManifest

    return SkillResponse(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        category=SkillCategory(skill.category.value if hasattr(skill.category, 'value') else skill.category),
        manifest=SkillManifest(**skill.manifest),
        handler_path=skill.handler_path,
        enabled=skill.enabled,
        is_builtin=getattr(skill, 'is_builtin', False),
        created_at=skill.created_at,
        updated_at=skill.updated_at,
    )


# ============================================================================
# Skill CRUD Endpoints
# ============================================================================

@router.get("", response_model=SkillListResponse, dependencies=[Depends(require_auth)])
async def list_skills(
    category: Optional[SkillCategory] = Query(None, description="Filter by category"),
    enabled_only: bool = Query(False, description="Only return enabled skills"),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    List all skills with optional filtering.

    Args:
        category: Filter by skill category (api, file, communication, analysis, custom)
        enabled_only: Only return enabled skills

    Returns:
        List of skills matching the filters
    """
    service = get_skill_service()
    skills = await service.get_skills(db, category=category, enabled_only=enabled_only)

    return SkillListResponse(
        items=[skill_to_response(skill) for skill in skills],
        total=len(skills)
    )


@router.get("/categories", response_model=SkillCategoriesResponse, dependencies=[Depends(require_auth)])
async def get_categories(
    principal: Principal = Depends(get_current_principal),
):
    """
    Get all available skill categories.

    Returns:
        List of categories with id and display name
    """
    categories = [
        {"id": "api", "name": "API", "description": "External API integrations"},
        {"id": "file", "name": "File", "description": "File system operations"},
        {"id": "communication", "name": "Communication", "description": "Messaging and communication"},
        {"id": "analysis", "name": "Analysis", "description": "Data analysis and processing"},
        {"id": "custom", "name": "Custom", "description": "User-defined skills"},
    ]

    return SkillCategoriesResponse(categories=categories)


@router.get("/{skill_id}", response_model=SkillResponse, dependencies=[Depends(require_auth)])
async def get_skill(
    skill_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    Get a skill by ID.

    Args:
        skill_id: UUID of the skill

    Returns:
        Skill details
    """
    service = get_skill_service()
    skill = await service.get_skill(db, skill_id)

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill with ID {skill_id} not found"
        )

    return skill_to_response(skill)


@router.post("", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(
    skill_data: SkillCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.OPERATOR, UserRole.ADMIN)),
):
    """
    Create a new skill.

    Args:
        skill_data: Skill creation data including name, manifest, and handler_path

    Returns:
        Created skill
    """
    service = get_skill_service()

    try:
        skill = await service.create_skill(db, skill_data)
        logger.info(f"Skill '{skill.name}' (ID: {skill.id}) created by {principal.principal_id}")
        return skill_to_response(skill)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create skill: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create skill"
        )


@router.put("/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: UUID,
    skill_data: SkillUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.OPERATOR, UserRole.ADMIN)),
):
    """
    Update an existing skill.

    Args:
        skill_id: UUID of the skill to update
        skill_data: Updated skill data

    Returns:
        Updated skill
    """
    service = get_skill_service()

    try:
        skill = await service.update_skill(db, skill_id, skill_data)

        if not skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill with ID {skill_id} not found"
            )

        logger.info(f"Skill '{skill.name}' (ID: {skill.id}) updated by {principal.principal_id}")
        return skill_to_response(skill)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update skill: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update skill"
        )


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.ADMIN)),
):
    """
    Delete a skill.
    Built-in skills cannot be deleted, only disabled.

    Args:
        skill_id: UUID of the skill to delete
    """
    service = get_skill_service()
    
    # Check if skill is a builtin
    skill = await service.get_skill(db, skill_id)
    if skill and skill.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Built-in skills cannot be deleted. Use the toggle endpoint to disable them."
        )

    deleted = await service.delete_skill(db, skill_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill with ID {skill_id} not found"
        )

    logger.info(f"Skill ID {skill_id} deleted by {principal.principal_id}")


# ============================================================================
# Built-in Skills Endpoints
# ============================================================================

@router.get("/builtins/status", dependencies=[Depends(require_auth)])
async def get_builtin_skills_status(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    Get status of all built-in skills.
    
    Returns:
        List of built-in skills with their enabled status
    """
    from .builtins_seeder import get_builtin_status
    builtins = await get_builtin_status(db)
    return {"builtins": builtins}


@router.post("/{skill_id}/toggle", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def toggle_builtin_skill(
    skill_id: UUID,
    enabled: bool = True,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    Enable or disable a skill (especially for built-ins).
    
    Args:
        skill_id: UUID of the skill to toggle
        enabled: True to enable, False to disable
        
    Returns:
        Success status
    """
    from .builtins_seeder import toggle_builtin
    
    success = await toggle_builtin(db, str(skill_id), enabled)
    
    if not success:
        # Try regular skill toggle via service
        service = get_skill_service()
        skill = await service.get_skill(db, skill_id)
        if not skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill with ID {skill_id} not found"
            )
        # Update enabled status
        from .schemas import SkillUpdate
        await service.update_skill(db, skill_id, SkillUpdate(enabled=enabled))
    
    action = "enabled" if enabled else "disabled"
    logger.info(f"Skill {skill_id} {action} by {principal.principal_id}")
    
    return {"success": True, "skill_id": str(skill_id), "enabled": enabled}


# ============================================================================
# Skill Execution Endpoints
# ============================================================================

@router.post("/{skill_id}/execute", response_model=SkillExecutionResult)
@limiter.limit(RateLimits.SKILLS_EXECUTE)
async def execute_skill(
    request: Request,
    skill_id: UUID,
    skill_request: SkillExecutionRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.OPERATOR, UserRole.ADMIN)),
):
    """
    Execute a skill with the given parameters.

    Args:
        skill_id: UUID of the skill to execute
        request: Execution request with parameters

    Returns:
        Execution result with success status and output
    """
    service = get_skill_service()

    # Override skill_id from URL
    skill_request.skill_id = skill_id

    # Log skill execution for audit trail (CRITICAL - RCE protection)
    logger.info(f"Skill {skill_id} executed by {principal.principal_id}")

    result = await service.execute_skill(db, skill_id, skill_request.params)

    return result


@router.post("/execute", response_model=SkillExecutionResult)
@limiter.limit(RateLimits.SKILLS_EXECUTE)
async def execute_skill_by_body(
    request: Request,
    skill_request: SkillExecutionRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.OPERATOR, UserRole.ADMIN)),
):
    """
    Execute a skill using skill_id from request body.

    Alternative endpoint that accepts skill_id in the request body.

    Args:
        skill_request: Execution request with skill_id and parameters

    Returns:
        Execution result with success status and output
    """
    service = get_skill_service()

    # Log skill execution for audit trail (CRITICAL - RCE protection)
    logger.info(f"Skill {skill_request.skill_id} executed by {principal.principal_id}")

    result = await service.execute_skill(db, skill_request.skill_id, skill_request.params)

    return result
