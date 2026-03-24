from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db

from .schemas import (
    ProviderAccountCreate,
    ProviderAccountResponse,
    ProviderAccountUpdate,
    ProviderBindingProjectionResponse,
    ProviderCredentialResponse,
    ProviderCredentialSetRequest,
    ProviderModelCreate,
    ProviderModelResponse,
    ProviderModelUpdate,
    ProviderRunRequest,
    ProviderRunResponse,
    ProviderTestRequest,
    ProviderTestResponse,
)
from .service import get_provider_portal_service


class ProviderListResponse(BaseModel):
    items: list[ProviderAccountResponse] = Field(default_factory=list)
    total: int


class ProviderModelListResponse(BaseModel):
    items: list[ProviderModelResponse] = Field(default_factory=list)
    total: int


router = APIRouter(prefix="/api/llm", tags=["provider-portal"], dependencies=[Depends(require_auth)])


def _inject_secret_metadata(model: ProviderAccountResponse, key_hint: str | None) -> ProviderAccountResponse:
    model.secret_configured = key_hint is not None
    model.key_hint_masked = key_hint
    return model


@router.get("/providers", response_model=ProviderListResponse)
async def list_providers(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    service = get_provider_portal_service()
    providers = await service.list_providers(db, principal.tenant_id)
    items: list[ProviderAccountResponse] = []
    for provider in providers:
        credential = await service._active_credential(db, provider.id)
        key_hint = credential.key_hint_last4 if credential else None
        items.append(_inject_secret_metadata(ProviderAccountResponse.model_validate(provider), key_hint))
    return ProviderListResponse(items=items, total=len(items))


@router.post("/providers", response_model=ProviderAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    payload: ProviderAccountCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_provider_portal_service()
    try:
        provider = await service.create_provider(db, payload, principal)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ProviderAccountResponse.model_validate(provider)


@router.patch("/providers/{provider_id}", response_model=ProviderAccountResponse)
async def update_provider(
    provider_id: UUID,
    payload: ProviderAccountUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_provider_portal_service()
    provider = await service.update_provider(db, provider_id, payload, principal)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider account not found")
    credential = await service._active_credential(db, provider.id)
    key_hint = credential.key_hint_last4 if credential else None
    return _inject_secret_metadata(ProviderAccountResponse.model_validate(provider), key_hint)


@router.post("/providers/{provider_id}/secret", response_model=ProviderCredentialResponse)
async def set_provider_secret(
    provider_id: UUID,
    payload: ProviderCredentialSetRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_provider_portal_service()
    credential = await service.set_credential(db, provider_id, payload, principal)
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider account not found")
    return ProviderCredentialResponse(
        provider_id=credential.provider_id,
        is_active=credential.is_active,
        key_hint_masked=credential.key_hint_last4,
        updated_at=credential.updated_at,
    )


@router.delete("/providers/{provider_id}/secret", response_model=ProviderCredentialResponse)
async def deactivate_provider_secret(
    provider_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_provider_portal_service()
    credential = await service.deactivate_credential(db, provider_id, principal)
    if credential is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active provider credential not found")
    return ProviderCredentialResponse(
        provider_id=credential.provider_id,
        is_active=credential.is_active,
        key_hint_masked=credential.key_hint_last4,
        updated_at=credential.updated_at,
    )


@router.post("/providers/{provider_id}/test", response_model=ProviderTestResponse)
async def test_provider_connection(
    provider_id: UUID,
    payload: ProviderTestRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN, SystemRole.OPERATOR)),
):
    service = get_provider_portal_service()
    result = await service.test_provider(db, provider_id, payload, principal)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider account not found")
    return ProviderTestResponse.model_validate(result)


@router.get("/providers/{provider_id}/binding-projection", response_model=ProviderBindingProjectionResponse)
async def get_binding_projection(
    provider_id: UUID,
    model_name: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    service = get_provider_portal_service()
    projection = await service.binding_projection(db, provider_id, model_name, principal.tenant_id)
    if projection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider account not found")
    return ProviderBindingProjectionResponse(provider_id=provider_id, projection=projection)


@router.get("/models", response_model=ProviderModelListResponse)
async def list_models(
    provider_id: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    service = get_provider_portal_service()
    items = await service.list_models(db, principal.tenant_id, provider_id)
    return ProviderModelListResponse(items=[ProviderModelResponse.model_validate(item) for item in items], total=len(items))


@router.post("/models", response_model=ProviderModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    payload: ProviderModelCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_provider_portal_service()
    try:
        model = await service.create_model(db, payload, principal)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider account not found")
    return ProviderModelResponse.model_validate(model)


@router.patch("/models/{model_id}", response_model=ProviderModelResponse)
async def update_model(
    model_id: UUID,
    payload: ProviderModelUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_provider_portal_service()
    model = await service.update_model(db, model_id, payload, principal)
    if model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider model not found")
    return ProviderModelResponse.model_validate(model)


@router.post("/run", response_model=ProviderRunResponse)
async def provider_run_stub(
    payload: ProviderRunRequest,
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    return ProviderRunResponse(
        accepted=True,
        message=(
            "Provider run contract accepted. Execute through canonical capability runtime/SkillRun pipeline, "
            "not direct portal execution."
        ),
    )
