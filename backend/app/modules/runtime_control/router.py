from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db

from .schemas import (
    ExternalOpsObservabilityResponse,
    ResolverRequest,
    ResolverResponse,
    RuntimeActiveOverrideListResponse,
    RuntimeControlInfo,
    RuntimeOverrideRequestCreate,
    RuntimeOverrideRequestDecision,
    RuntimeOverrideRequestItem,
    RuntimeOverrideRequestListResponse,
    RuntimeRegistryVersionCreate,
    RuntimeRegistryVersionItem,
    RuntimeRegistryVersionListResponse,
    RuntimeRegistryVersionPromoteRequest,
    RuntimeControlTimelineResponse,
)
from .service import get_runtime_control_service


router = APIRouter(
    prefix="/api/runtime-control",
    tags=["runtime-control"],
    dependencies=[Depends(require_auth)],
)


@router.get("/info", response_model=RuntimeControlInfo)
async def get_runtime_control_info(
    principal: Principal = Depends(get_current_principal),
) -> RuntimeControlInfo:
    _ = principal
    service = get_runtime_control_service()
    return RuntimeControlInfo(
        name="BRAiN Runtime Control Plane",
        resolver_path="registry -> resolver -> policy -> override -> enforcement -> audit",
        override_priority=service.OVERRIDE_PRIORITY,
        notes=[
            "ControlDeck is a control surface, not source-of-truth.",
            "Slice-1 covers LLM routing, worker selection and budget-aware policy effects.",
            "Mutations should flow through governed change requests in next slices.",
        ],
    )


@router.post("/resolve", response_model=ResolverResponse)
async def resolve_runtime_decision(
    payload: ResolverRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> ResolverResponse:
    context = payload.context.model_copy(
        update={
            "tenant_id": payload.context.tenant_id or principal.tenant_id,
        }
    )
    service = get_runtime_control_service()
    return await service.resolve_with_persisted_overrides(context, db=db)


@router.get("/overrides/requests", response_model=RuntimeOverrideRequestListResponse)
async def list_override_requests(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> RuntimeOverrideRequestListResponse:
    service = get_runtime_control_service()
    return await service.list_override_requests(db, tenant_id=principal.tenant_id)


@router.post(
    "/overrides/requests",
    response_model=RuntimeOverrideRequestItem,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))],
)
async def create_override_request(
    payload: RuntimeOverrideRequestCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> RuntimeOverrideRequestItem:
    service = get_runtime_control_service()
    try:
        return await service.create_override_request(db, principal=principal, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/overrides/requests/{request_id}/approve",
    response_model=RuntimeOverrideRequestItem,
    dependencies=[Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))],
)
async def approve_override_request(
    request_id: str,
    payload: RuntimeOverrideRequestDecision,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> RuntimeOverrideRequestItem:
    service = get_runtime_control_service()
    try:
        return await service.approve_override_request(db, principal=principal, request_id=request_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/overrides/requests/{request_id}/reject",
    response_model=RuntimeOverrideRequestItem,
    dependencies=[Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))],
)
async def reject_override_request(
    request_id: str,
    payload: RuntimeOverrideRequestDecision,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> RuntimeOverrideRequestItem:
    service = get_runtime_control_service()
    try:
        return await service.reject_override_request(db, principal=principal, request_id=request_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/overrides/active", response_model=RuntimeActiveOverrideListResponse)
async def list_active_overrides(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> RuntimeActiveOverrideListResponse:
    service = get_runtime_control_service()
    return await service.list_active_overrides(db, tenant_id=principal.tenant_id)


@router.get(
    "/registry/versions",
    response_model=RuntimeRegistryVersionListResponse,
)
async def list_registry_versions(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> RuntimeRegistryVersionListResponse:
    service = get_runtime_control_service()
    return await service.list_registry_versions(db, tenant_id=principal.tenant_id)


@router.post(
    "/registry/versions",
    response_model=RuntimeRegistryVersionItem,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))],
)
async def create_registry_version(
    payload: RuntimeRegistryVersionCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> RuntimeRegistryVersionItem:
    service = get_runtime_control_service()
    return await service.create_registry_version(db, principal=principal, payload=payload)


@router.post(
    "/registry/versions/{version_id}/promote",
    response_model=RuntimeRegistryVersionItem,
    dependencies=[Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))],
)
async def promote_registry_version(
    version_id: str,
    payload: RuntimeRegistryVersionPromoteRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> RuntimeRegistryVersionItem:
    service = get_runtime_control_service()
    try:
        return await service.promote_registry_version(
            db,
            principal=principal,
            version_id=version_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get(
    "/timeline",
    response_model=RuntimeControlTimelineResponse,
)
async def list_runtime_control_timeline(
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> RuntimeControlTimelineResponse:
    service = get_runtime_control_service()
    return await service.list_timeline(db, tenant_id=principal.tenant_id, limit=min(max(limit, 1), 500))


@router.get(
    "/external-ops/observability",
    response_model=ExternalOpsObservabilityResponse,
)
async def get_external_ops_observability(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> ExternalOpsObservabilityResponse:
    service = get_runtime_control_service()
    return await service.get_external_ops_observability(db, tenant_id=principal.tenant_id)
