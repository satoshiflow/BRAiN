"""
Mission Templates Router - SECURED

API endpoints for mission template management.
All endpoints require authentication.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.core.auth_deps import (
    require_auth,
    require_role,
    SystemRole,
    Principal,
)
from app.core.rate_limit import limiter, RateLimits

from .schemas import (
    MissionTemplateCreate,
    MissionTemplateUpdate,
    MissionTemplateResponse,
    MissionTemplateListResponse,
    InstantiateTemplateRequest,
    InstantiateTemplateResponse,
    TemplateCategoriesResponse,
)
from .service import MissionTemplateService, get_template_service


router = APIRouter(
    prefix="/api/missions/templates",
    tags=["mission-templates"],
)


def get_service(db: AsyncSession = Depends(get_db)) -> MissionTemplateService:
    """Dependency to get the template service"""
    return get_template_service(db)


def _audit_log(
    action: str,
    principal: Principal,
    template_id: Optional[str] = None,
    details: Optional[dict] = None,
):
    """Log mission operations for audit trail"""
    audit_entry = {
        "action": action,
        "principal_id": principal.principal_id,
        "principal_type": principal.principal_type.value,
        "template_id": template_id,
        "tenant_id": principal.tenant_id,
        "details": details or {},
    }
    logger.info(f"[AUDIT] Mission operation: {audit_entry}")


def _check_template_ownership(template, principal: Principal) -> bool:
    """
    Check if principal owns the template or has admin privileges.
    
    Admins can modify any template. Regular users can only modify
    templates they own (where owner_id matches principal_id).
    
    For templates without an owner (legacy data), only admins can modify.
    """
    # Admin can modify any template
    if principal.has_role(SystemRole.ADMIN) or principal.has_role(SystemRole.SYSTEM_ADMIN):
        return True
    
    # Check if template has owner_id attribute and matches principal
    template_owner = getattr(template, "owner_id", None)
    if template_owner is None:
        # Legacy template without owner - only admin can modify
        return False
    
    return template_owner == principal.principal_id


# ============================================================================
# Template CRUD Endpoints
# ============================================================================

@router.get("", response_model=MissionTemplateListResponse)
async def list_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in name/description"),
    principal: Principal = Depends(require_auth),
    service: MissionTemplateService = Depends(get_service),
):
    """
    List all mission templates with optional filtering.
    
    Args:
        category: Filter by template category
        search: Search term for name/description
    
    Returns:
        List of templates matching the filters
    """
    _audit_log("list_templates", principal, details={"category": category, "search": search})
    
    templates = await service.list_templates(category=category, search=search)
    
    return MissionTemplateListResponse(
        items=[
            MissionTemplateResponse(
                id=t.id,
                name=t.name,
                description=t.description,
                category=t.category,
                steps=t.steps,
                variables=t.variables,
                owner_id=t.owner_id,
                created_at=t.created_at.isoformat() if t.created_at else None,
                updated_at=t.updated_at.isoformat() if t.updated_at else None,
            )
            for t in templates
        ],
        total=len(templates),
    )


@router.get("/categories", response_model=TemplateCategoriesResponse)
async def get_categories(
    principal: Principal = Depends(require_auth),
    service: MissionTemplateService = Depends(get_service),
):
    """
    Get all unique template categories.
    
    Returns:
        List of category names
    """
    _audit_log("get_categories", principal)
    
    categories = await service.get_categories()
    return TemplateCategoriesResponse(categories=categories)


@router.get("/{template_id}", response_model=MissionTemplateResponse)
async def get_template(
    template_id: str,
    principal: Principal = Depends(require_auth),
    service: MissionTemplateService = Depends(get_service),
):
    """
    Get a single template by ID.
    
    Args:
        template_id: The template ID
    
    Returns:
        Template details
    """
    _audit_log("get_template", principal, template_id=template_id)
    
    template = await service.get_template(template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}",
        )
    
    return MissionTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category,
        steps=template.steps,
        variables=template.variables,
        owner_id=template.owner_id,
        created_at=template.created_at.isoformat() if template.created_at else None,
        updated_at=template.updated_at.isoformat() if template.updated_at else None,
    )


@router.post(
    "",
    response_model=MissionTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    data: MissionTemplateCreate,
    principal: Principal = Depends(require_role(SystemRole.OPERATOR)),
    service: MissionTemplateService = Depends(get_service),
):
    """
    Create a new mission template.
    
    Requires OPERATOR role or higher.
    
    Example:
        ```json
        {
            "name": "Data Sync",
            "description": "Sync data from source to target",
            "category": "data",
            "steps": [
                {"order": 1, "action": "validate_source", "config": {}},
                {"order": 2, "action": "transform", "config": {}},
                {"order": 3, "action": "write_target", "config": {}}
            ],
            "variables": {
                "source_url": {"type": "string", "required": true},
                "target_url": {"type": "string", "required": true}
            }
        }
        ```
    
    Returns:
        Created template
    """
    _audit_log(
        "create_template",
        principal,
        details={"name": data.name, "category": data.category},
    )
    
    try:
        template = await service.create_template(data, owner_id=principal.principal_id)
        
        _audit_log(
            "template_created",
            principal,
            template_id=template.id,
            details={"name": template.name},
        )
        
        return MissionTemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            category=template.category,
            steps=template.steps,
            variables=template.variables,
            owner_id=template.owner_id,
            created_at=template.created_at.isoformat() if template.created_at else None,
            updated_at=template.updated_at.isoformat() if template.updated_at else None,
        )
    except Exception as e:
        _audit_log(
            "create_template_failed",
            principal,
            details={"name": data.name, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create template: {str(e)}",
        )


@router.put("/{template_id}", response_model=MissionTemplateResponse)
async def update_template(
    template_id: str,
    data: MissionTemplateUpdate,
    principal: Principal = Depends(require_auth),
    service: MissionTemplateService = Depends(get_service),
):
    """
    Update an existing template.
    
    Only provided fields will be updated.
    User must own the template or have admin role.
    
    Args:
        template_id: The template ID to update
        data: Fields to update
    
    Returns:
        Updated template
    """
    _audit_log(
        "update_template_attempt",
        principal,
        template_id=template_id,
        details={"fields_updated": [k for k, v in data.model_dump().items() if v is not None]},
    )
    
    template = await service.get_template(template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}",
        )
    
    # Ownership check
    if not _check_template_ownership(template, principal):
        _audit_log(
            "update_template_denied",
            principal,
            template_id=template_id,
            details={"reason": "ownership_violation"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this template",
        )
    
    updated_template = await service.update_template(template_id, data)
    
    _audit_log(
        "update_template_success",
        principal,
        template_id=template_id,
        details={"name": updated_template.name},
    )
    
    return MissionTemplateResponse(
        id=updated_template.id,
        name=updated_template.name,
        description=updated_template.description,
        category=updated_template.category,
        steps=updated_template.steps,
        variables=updated_template.variables,
        created_at=updated_template.created_at.isoformat() if updated_template.created_at else None,
        updated_at=updated_template.updated_at.isoformat() if updated_template.updated_at else None,
    )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    principal: Principal = Depends(require_auth),
    service: MissionTemplateService = Depends(get_service),
):
    """
    Delete a template by ID.
    
    User must own the template or have admin role.
    
    Args:
        template_id: The template ID to delete
    """
    _audit_log("delete_template_attempt", principal, template_id=template_id)
    
    template = await service.get_template(template_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {template_id}",
        )
    
    # Ownership check
    if not _check_template_ownership(template, principal):
        _audit_log(
            "delete_template_denied",
            principal,
            template_id=template_id,
            details={"reason": "ownership_violation"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this template",
        )
    
    deleted = await service.delete_template(template_id)
    
    if deleted:
        _audit_log("delete_template_success", principal, template_id=template_id)
    
    return None


# ============================================================================
# Template Instantiation Endpoint
# ============================================================================

@router.post(
    "/{template_id}/instantiate",
    response_model=InstantiateTemplateResponse,
)
@limiter.limit(RateLimits.MISSIONS_INSTANTIATE)
async def instantiate_template(
    request: Request,
    template_id: str,
    template_request: InstantiateTemplateRequest,
    principal: Principal = Depends(require_auth),
    service: MissionTemplateService = Depends(get_service),
):
    """
    Create a mission from a template.
    
    This endpoint instantiates a template with the provided variable values
    and creates a new mission.
    
    Example:
        ```json
        {
            "variables": {
                "source_url": "https://api.example.com/data",
                "target_url": "https://target.example.com/api"
            },
            "mission_name": "Daily Data Sync"
        }
        ```
    
    Args:
        template_id: The template to instantiate
        request: Variable values and optional mission name
    
    Returns:
        Created mission details
    """
    _audit_log(
        "instantiate_template_attempt",
        principal,
        template_id=template_id,
        details={
            "mission_name": template_request.mission_name,
            "variables_provided": list(template_request.variables.keys()) if template_request.variables else [],
        },
    )

    try:
        result = await service.instantiate_template(template_id, template_request)
        
        _audit_log(
            "instantiate_template_success",
            principal,
            template_id=template_id,
            details={
                "mission_id": result.mission_id,
                "mission_name": result.mission_name,
            },
        )
        
        return result
    except ValueError as e:
        _audit_log(
            "instantiate_template_failed",
            principal,
            template_id=template_id,
            details={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        _audit_log(
            "instantiate_template_failed",
            principal,
            template_id=template_id,
            details={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to instantiate template: {str(e)}",
        )
