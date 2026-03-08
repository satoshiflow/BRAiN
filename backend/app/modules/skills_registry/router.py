from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db

from .schemas import (
    OwnerScope,
    SkillDefinitionCreate,
    SkillDefinitionListResponse,
    SkillDefinitionResponse,
    SkillDefinitionStatus,
    SkillDefinitionTransitionResponse,
    SkillDefinitionUpdate,
    SkillRegistryResolveResponse,
    VersionSelector,
)
from .service import get_skill_registry_service


router = APIRouter(prefix="/api", tags=["skill-registry"], dependencies=[Depends(require_auth)])


def _transition_response(item: SkillDefinitionResponse, previous_status: SkillDefinitionStatus) -> SkillDefinitionTransitionResponse:
    return SkillDefinitionTransitionResponse(
        skill_key=item.skill_key,
        version=item.version,
        previous_status=previous_status,
        status=item.status,
    )


@router.get("/skill-definitions", response_model=SkillDefinitionListResponse)
async def list_skill_definitions(
    skill_key: str | None = Query(default=None),
    status_filter: SkillDefinitionStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    service = get_skill_registry_service()
    items = await service.list_definitions(
        db,
        tenant_id=principal.tenant_id,
        include_system=True,
        skill_key=skill_key,
        status=status_filter.value if status_filter else None,
    )
    return SkillDefinitionListResponse(items=[SkillDefinitionResponse.model_validate(item) for item in items], total=len(items))


@router.post("/skill-definitions", response_model=SkillDefinitionResponse, status_code=status.HTTP_201_CREATED)
async def create_skill_definition(
    payload: SkillDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_skill_registry_service()
    try:
        item = await service.create_definition(db, payload, principal)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return SkillDefinitionResponse.model_validate(item)


@router.get("/skill-definitions/{skill_key}/versions/{version}", response_model=SkillDefinitionResponse)
async def get_skill_definition(
    skill_key: str,
    version: int,
    owner_scope: OwnerScope | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    service = get_skill_registry_service()
    item = await service.get_definition(db, skill_key, version, principal.tenant_id, include_system=True, owner_scope=owner_scope.value if owner_scope else None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill definition '{skill_key}' version {version} not found")
    return SkillDefinitionResponse.model_validate(item)


@router.patch("/skill-definitions/{skill_key}/versions/{version}", response_model=SkillDefinitionResponse)
async def update_skill_definition(
    skill_key: str,
    version: int,
    payload: SkillDefinitionUpdate,
    owner_scope: OwnerScope | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_skill_registry_service()
    try:
        item = await service.update_definition(db, skill_key, version, payload, principal, owner_scope=owner_scope.value if owner_scope else None)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill definition '{skill_key}' version {version} not found")
    return SkillDefinitionResponse.model_validate(item)


async def _transition_skill_definition(
    skill_key: str,
    version: int,
    target_status: SkillDefinitionStatus,
    owner_scope: OwnerScope | None,
    db: AsyncSession,
    principal: Principal,
) -> SkillDefinitionTransitionResponse:
    service = get_skill_registry_service()
    current = await service.get_definition(db, skill_key, version, principal.tenant_id, include_system=True, owner_scope=owner_scope.value if owner_scope else None)
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill definition '{skill_key}' version {version} not found")
    previous_status = SkillDefinitionStatus(current.status)
    try:
        item = await service.transition_definition(db, skill_key, version, target_status, principal, owner_scope=owner_scope.value if owner_scope else None)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill definition '{skill_key}' version {version} not found")
    return _transition_response(SkillDefinitionResponse.model_validate(item), previous_status)


@router.post("/skill-definitions/{skill_key}/versions/{version}/submit-review", response_model=SkillDefinitionTransitionResponse)
async def submit_skill_definition_review(
    skill_key: str,
    version: int,
    owner_scope: OwnerScope | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    return await _transition_skill_definition(skill_key, version, SkillDefinitionStatus.REVIEW, owner_scope, db, principal)


@router.post("/skill-definitions/{skill_key}/versions/{version}/approve", response_model=SkillDefinitionTransitionResponse)
async def approve_skill_definition(
    skill_key: str,
    version: int,
    owner_scope: OwnerScope | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    return await _transition_skill_definition(skill_key, version, SkillDefinitionStatus.APPROVED, owner_scope, db, principal)


@router.post("/skill-definitions/{skill_key}/versions/{version}/activate", response_model=SkillDefinitionTransitionResponse)
async def activate_skill_definition(
    skill_key: str,
    version: int,
    owner_scope: OwnerScope | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    return await _transition_skill_definition(skill_key, version, SkillDefinitionStatus.ACTIVE, owner_scope, db, principal)


@router.post("/skill-definitions/{skill_key}/versions/{version}/reject", response_model=SkillDefinitionTransitionResponse)
async def reject_skill_definition(
    skill_key: str,
    version: int,
    owner_scope: OwnerScope | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    return await _transition_skill_definition(skill_key, version, SkillDefinitionStatus.REJECTED, owner_scope, db, principal)


@router.post("/skill-definitions/{skill_key}/versions/{version}/deprecate", response_model=SkillDefinitionTransitionResponse)
async def deprecate_skill_definition(
    skill_key: str,
    version: int,
    owner_scope: OwnerScope | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    return await _transition_skill_definition(skill_key, version, SkillDefinitionStatus.DEPRECATED, owner_scope, db, principal)


@router.post("/skill-definitions/{skill_key}/versions/{version}/retire", response_model=SkillDefinitionTransitionResponse)
async def retire_skill_definition(
    skill_key: str,
    version: int,
    owner_scope: OwnerScope | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    return await _transition_skill_definition(skill_key, version, SkillDefinitionStatus.RETIRED, owner_scope, db, principal)


@router.get("/skill-registry/resolve", response_model=SkillRegistryResolveResponse)
async def resolve_skill_definition(
    skill_key: str = Query(..., min_length=1),
    selector: VersionSelector = Query(default=VersionSelector.ACTIVE),
    version_value: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    service = get_skill_registry_service()
    try:
        item = await service.resolve_definition(db, skill_key, principal.tenant_id, selector, version_value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SkillRegistryResolveResponse(
        skill_key=item.skill_key,
        version=item.version,
        owner_scope=item.owner_scope,
        tenant_id=item.tenant_id,
        checksum_sha256=item.checksum_sha256,
        required_capabilities=item.required_capabilities,
        optional_capabilities=item.optional_capabilities,
        status=item.status,
    )
