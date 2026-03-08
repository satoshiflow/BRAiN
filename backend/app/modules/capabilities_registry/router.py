from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db
from app.modules.skills_registry.schemas import VersionSelector

from .schemas import (
    OwnerScope,
    CapabilityDefinitionCreate,
    CapabilityDefinitionListResponse,
    CapabilityDefinitionResponse,
    CapabilityDefinitionStatus,
    CapabilityDefinitionTransitionResponse,
    CapabilityDefinitionUpdate,
    CapabilityRegistryResolveResponse,
)
from .service import get_capability_registry_service


router = APIRouter(prefix="/api", tags=["capability-registry"], dependencies=[Depends(require_auth)])


def _transition_response(item: CapabilityDefinitionResponse, previous_status: CapabilityDefinitionStatus) -> CapabilityDefinitionTransitionResponse:
    return CapabilityDefinitionTransitionResponse(
        capability_key=item.capability_key,
        version=item.version,
        previous_status=previous_status,
        status=item.status,
    )


@router.get("/capability-definitions", response_model=CapabilityDefinitionListResponse)
async def list_capability_definitions(
    capability_key: str | None = Query(default=None),
    status_filter: CapabilityDefinitionStatus | None = Query(default=None, alias="status"),
    domain: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    service = get_capability_registry_service()
    items = await service.list_definitions(
        db,
        tenant_id=principal.tenant_id,
        include_system=True,
        capability_key=capability_key,
        status=status_filter.value if status_filter else None,
        domain=domain,
    )
    return CapabilityDefinitionListResponse(items=[CapabilityDefinitionResponse.model_validate(item) for item in items], total=len(items))


@router.post("/capability-definitions", response_model=CapabilityDefinitionResponse, status_code=status.HTTP_201_CREATED)
async def create_capability_definition(
    payload: CapabilityDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_capability_registry_service()
    try:
        item = await service.create_definition(db, payload, principal)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return CapabilityDefinitionResponse.model_validate(item)


@router.get("/capability-definitions/{capability_key}/versions/{version}", response_model=CapabilityDefinitionResponse)
async def get_capability_definition(
    capability_key: str,
    version: int,
    owner_scope: OwnerScope | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    service = get_capability_registry_service()
    item = await service.get_definition(db, capability_key, version, principal.tenant_id, include_system=True, owner_scope=owner_scope.value if owner_scope else None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Capability definition '{capability_key}' version {version} not found")
    return CapabilityDefinitionResponse.model_validate(item)


@router.patch("/capability-definitions/{capability_key}/versions/{version}", response_model=CapabilityDefinitionResponse)
async def update_capability_definition(
    capability_key: str,
    version: int,
    payload: CapabilityDefinitionUpdate,
    owner_scope: OwnerScope | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_capability_registry_service()
    try:
        item = await service.update_definition(db, capability_key, version, payload, principal, owner_scope=owner_scope.value if owner_scope else None)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Capability definition '{capability_key}' version {version} not found")
    return CapabilityDefinitionResponse.model_validate(item)


async def _transition_capability_definition(
    capability_key: str,
    version: int,
    target_status: CapabilityDefinitionStatus,
    owner_scope: OwnerScope | None,
    db: AsyncSession,
    principal: Principal,
) -> CapabilityDefinitionTransitionResponse:
    service = get_capability_registry_service()
    current = await service.get_definition(db, capability_key, version, principal.tenant_id, include_system=True, owner_scope=owner_scope.value if owner_scope else None)
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Capability definition '{capability_key}' version {version} not found")
    previous_status = CapabilityDefinitionStatus(current.status)
    try:
        item = await service.transition_definition(db, capability_key, version, target_status, principal, owner_scope=owner_scope.value if owner_scope else None)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Capability definition '{capability_key}' version {version} not found")
    return _transition_response(CapabilityDefinitionResponse.model_validate(item), previous_status)


@router.post("/capability-definitions/{capability_key}/versions/{version}/activate", response_model=CapabilityDefinitionTransitionResponse)
async def activate_capability_definition(
    capability_key: str,
    version: int,
    owner_scope: OwnerScope | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    return await _transition_capability_definition(capability_key, version, CapabilityDefinitionStatus.ACTIVE, owner_scope, db, principal)


@router.post("/capability-definitions/{capability_key}/versions/{version}/block", response_model=CapabilityDefinitionTransitionResponse)
async def block_capability_definition(
    capability_key: str,
    version: int,
    owner_scope: OwnerScope | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    return await _transition_capability_definition(capability_key, version, CapabilityDefinitionStatus.BLOCKED, owner_scope, db, principal)


@router.post("/capability-definitions/{capability_key}/versions/{version}/unblock", response_model=CapabilityDefinitionTransitionResponse)
async def unblock_capability_definition(
    capability_key: str,
    version: int,
    owner_scope: OwnerScope | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    return await _transition_capability_definition(capability_key, version, CapabilityDefinitionStatus.ACTIVE, owner_scope, db, principal)


@router.post("/capability-definitions/{capability_key}/versions/{version}/deprecate", response_model=CapabilityDefinitionTransitionResponse)
async def deprecate_capability_definition(
    capability_key: str,
    version: int,
    owner_scope: OwnerScope | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    return await _transition_capability_definition(capability_key, version, CapabilityDefinitionStatus.DEPRECATED, owner_scope, db, principal)


@router.post("/capability-definitions/{capability_key}/versions/{version}/retire", response_model=CapabilityDefinitionTransitionResponse)
async def retire_capability_definition(
    capability_key: str,
    version: int,
    owner_scope: OwnerScope | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    return await _transition_capability_definition(capability_key, version, CapabilityDefinitionStatus.RETIRED, owner_scope, db, principal)


@router.get("/capability-registry/resolve", response_model=CapabilityRegistryResolveResponse)
async def resolve_capability_definition(
    capability_key: str = Query(..., min_length=1),
    selector: VersionSelector = Query(default=VersionSelector.ACTIVE),
    version_value: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    service = get_capability_registry_service()
    try:
        item = await service.resolve_definition(db, capability_key, principal.tenant_id, selector, version_value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return CapabilityRegistryResolveResponse(
        capability_key=item.capability_key,
        version=item.version,
        owner_scope=item.owner_scope,
        tenant_id=item.tenant_id,
        status=item.status,
        checksum_sha256=item.checksum_sha256,
        domain=item.domain,
        fallback_capability_key=item.fallback_capability_key,
    )
