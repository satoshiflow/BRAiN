"""Config Management - Router"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.core.auth_deps import require_auth, require_role, get_current_principal, Principal
from app.core.security import UserRole
from .schemas import ConfigCreate, ConfigUpdate, ConfigResponse, ConfigListResponse, ConfigBulkUpdate
from .service import get_config_service

router = APIRouter(prefix="/api/config", tags=["config"])

@router.get("", response_model=ConfigListResponse, dependencies=[Depends(require_auth)])
async def list_configs(
    environment: Optional[str] = Query(None),
    include_secrets: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """List all configs (secrets redacted unless admin)."""
    service = get_config_service()
    configs = await service.get_configs(db, environment=environment, include_secrets=include_secrets)
    return ConfigListResponse(
        items=[ConfigResponse.model_validate(c) for c in configs],
        total=len(configs),
        environment=environment or "all"
    )

@router.get("/{key}", response_model=ConfigResponse, dependencies=[Depends(require_auth)])
async def get_config(
    key: str,
    environment: str = Query("default"),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Get a specific config by key."""
    service = get_config_service()
    config = await service.get_config(db, key, environment)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Config {key} not found")
    return ConfigResponse.model_validate(config)

@router.put("/{key}", response_model=ConfigResponse, dependencies=[Depends(require_role(UserRole.ADMIN))])
async def set_config(
    key: str,
    config_data: ConfigCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Create or update a config (admin only)."""
    service = get_config_service()
    config = await service.set_config(db, config_data, principal.principal_id)
    return ConfigResponse.model_validate(config)

@router.delete("/{key}", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def delete_config(
    key: str,
    environment: str = Query("default"),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Delete a config (admin only)."""
    service = get_config_service()
    success = await service.delete_config(db, key, environment)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Config {key} not found")
    return {"success": True, "message": f"Config {key} deleted"}

@router.post("/bulk", response_model=ConfigListResponse, dependencies=[Depends(require_role(UserRole.ADMIN))])
async def bulk_update(
    bulk_data: ConfigBulkUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Bulk update configs (admin only)."""
    service = get_config_service()
    configs = await service.bulk_update(db, bulk_data.configs, bulk_data.environment, principal.principal_id)
    return ConfigListResponse(
        items=[ConfigResponse.model_validate(c) for c in configs],
        total=len(configs),
        environment=bulk_data.environment
    )
