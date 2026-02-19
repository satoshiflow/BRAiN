"""
AXE Identity API Router

FastAPI endpoints for managing AXE identities.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.core.security import get_current_principal, require_role, UserRole, Principal
from .service import AXEIdentityService
from .schemas import (
    AXEIdentityCreate,
    AXEIdentityUpdate,
    AXEIdentityResponse,
    AXEIdentityListResponse
)
from typing import List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/axe/identity", tags=["axe-identity"])


def get_service(db: AsyncSession = Depends(get_db)) -> AXEIdentityService:
    """Dependency injection for service"""
    return AXEIdentityService(db)


@router.get("/", response_model=List[AXEIdentityResponse])
async def list_identities(
    service: AXEIdentityService = Depends(get_service),
    principal: Principal = Depends(require_role(UserRole.OPERATOR))
):
    """
    List all AXE identities.

    Requires OPERATOR role or higher.
    """
    return await service.get_all()


@router.get("/active", response_model=AXEIdentityResponse)
async def get_active_identity(
    service: AXEIdentityService = Depends(get_service)
):
    """
    Get currently active identity.

    Public endpoint (no auth required) - used by chat system.
    Returns default identity if no identity is active.
    """
    identity = await service.get_active()
    if not identity:
        identity = await service.get_default()
    return identity


@router.get("/{identity_id}", response_model=AXEIdentityResponse)
async def get_identity(
    identity_id: str,
    service: AXEIdentityService = Depends(get_service),
    principal: Principal = Depends(require_role(UserRole.OPERATOR))
):
    """
    Get specific identity by ID.

    Requires OPERATOR role or higher.
    """
    identity = await service.get_by_id(identity_id)
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Identity not found: {identity_id}"
        )
    return identity


@router.post("/", response_model=AXEIdentityResponse, status_code=status.HTTP_201_CREATED)
async def create_identity(
    data: AXEIdentityCreate,
    service: AXEIdentityService = Depends(get_service),
    principal: Principal = Depends(require_role(UserRole.ADMIN))
):
    """
    Create new AXE identity.

    Requires ADMIN role.
    """
    try:
        return await service.create(data, created_by=principal.agent_id)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Identity with name '{data.name}' already exists"
        )


@router.patch("/{identity_id}", response_model=AXEIdentityResponse)
async def update_identity(
    identity_id: str,
    data: AXEIdentityUpdate,
    service: AXEIdentityService = Depends(get_service),
    principal: Principal = Depends(require_role(UserRole.ADMIN))
):
    """
    Update existing identity.

    Requires ADMIN role.
    """
    identity = await service.update(identity_id, data)
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Identity not found: {identity_id}"
        )
    return identity


@router.post("/{identity_id}/activate", response_model=AXEIdentityResponse)
async def activate_identity(
    identity_id: str,
    service: AXEIdentityService = Depends(get_service),
    principal: Principal = Depends(require_role(UserRole.ADMIN))
):
    """
    Activate identity (deactivates all others).

    Requires ADMIN role.
    """
    identity = await service.activate(identity_id)
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Identity not found: {identity_id}"
        )
    return identity


@router.delete("/{identity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_identity(
    identity_id: str,
    service: AXEIdentityService = Depends(get_service),
    principal: Principal = Depends(require_role(UserRole.ADMIN))
):
    """
    Delete identity.

    Cannot delete active identity.
    Requires ADMIN role.
    """
    try:
        success = await service.delete(identity_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Identity not found: {identity_id}"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
