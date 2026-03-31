"""Config Management - Router"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db

from .schemas import (
    ConfigBulkUpdate,
    ConfigCreate,
    ConfigListResponse,
    ConfigResponse,
    VaultDefinitionsListResponse,
    VaultGenerateRequest,
    VaultGenerateResponse,
    VaultRotationDecisionRequest,
    VaultRotationListResponse,
    VaultRotationRequestCreate,
    VaultRotationRequestResponse,
    VaultUpsertRequest,
    VaultValidateRequest,
    VaultValidateResponse,
    VaultValuesListResponse,
    VaultValueResponse,
)
from .service import get_config_service


router = APIRouter(prefix="/api/config", tags=["config"])


def _can_write_vault(principal: Principal) -> bool:
    return principal.has_any_role([SystemRole.ADMIN.value, SystemRole.OPERATOR.value])


def _is_admin(principal: Principal) -> bool:
    return principal.has_role(SystemRole.ADMIN.value)


def _to_config_response(config, include_secret_value: bool) -> ConfigResponse:
    return ConfigResponse(
        id=config.id,
        key=config.key,
        value=config.value if include_secret_value or not config.is_secret else "***REDACTED***",
        type=config.type,
        environment=config.environment,
        is_secret=config.is_secret,
        description=config.description,
        version=config.version,
        created_by=config.created_by,
        updated_by=config.updated_by,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.get("", response_model=ConfigListResponse, dependencies=[Depends(require_auth)])
async def list_configs(
    environment: Optional[str] = Query(None),
    include_secrets: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """List raw config entries (legacy API, secrets redacted unless admin)."""
    service = get_config_service()
    allowed_secret_view = include_secrets and _is_admin(principal)
    configs = await service.get_configs(db, environment=environment, include_secrets=allowed_secret_view)
    return ConfigListResponse(
        items=[_to_config_response(item, include_secret_value=allowed_secret_view) for item in configs],
        total=len(configs),
        environment=environment or "all",
    )


@router.get("/{key}", response_model=ConfigResponse, dependencies=[Depends(require_auth)])
async def get_config(
    key: str,
    environment: str = Query("default"),
    include_secret: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Get a specific raw config entry (legacy API)."""
    service = get_config_service()
    config = await service.get_config(db, key, environment)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Config {key} not found")
    can_view_secret = include_secret and _is_admin(principal)
    return _to_config_response(config, include_secret_value=can_view_secret)


@router.put("/{key}", response_model=ConfigResponse, dependencies=[Depends(require_role(SystemRole.ADMIN))])
async def set_config(
    key: str,
    config_data: ConfigCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Create or update a config (admin only, legacy API)."""
    service = get_config_service()
    payload = config_data.model_copy(update={"key": key})
    config = await service.set_config(db, payload, principal.principal_id)
    return _to_config_response(config, include_secret_value=False)


@router.post("/bulk", response_model=ConfigListResponse, dependencies=[Depends(require_role(SystemRole.ADMIN))])
async def bulk_update(
    bulk_data: ConfigBulkUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Bulk update configs (admin only, legacy API)."""
    service = get_config_service()
    configs = await service.bulk_update(db, bulk_data.configs, bulk_data.environment, principal.principal_id)
    return ConfigListResponse(
        items=[_to_config_response(item, include_secret_value=False) for item in configs],
        total=len(configs),
        environment=bulk_data.environment,
    )


@router.get("/vault/definitions", response_model=VaultDefinitionsListResponse, dependencies=[Depends(require_auth)])
async def list_vault_definitions(
    principal: Principal = Depends(get_current_principal),
):
    """Return managed config key metadata for ControlDeck vault UI."""
    service = get_config_service()
    items = service.list_vault_definitions()
    return VaultDefinitionsListResponse(items=items, total=len(items))


@router.get("/vault/values", response_model=VaultValuesListResponse, dependencies=[Depends(require_auth)])
async def list_vault_values(
    classification: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Return effective vault values with masking by classification."""
    service = get_config_service()
    items = await service.list_vault_values(db=db, classification=classification)
    return VaultValuesListResponse(items=items, total=len(items))


@router.post("/vault/values/{key}", response_model=VaultValueResponse, dependencies=[Depends(require_auth)])
async def upsert_vault_value(
    key: str,
    payload: VaultUpsertRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Upsert a managed vault value with server-side validation."""
    if not _can_write_vault(principal):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role for vault write")

    service = get_config_service()
    definition = service._definition_for_key(key)
    if definition.classification == "secret" and not _is_admin(principal):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required for secret updates")

    try:
        return await service.upsert_vault_value(
            db,
            key=key,
            value=payload.value,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _ = exc
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Config storage unavailable",
        ) from exc


@router.post("/vault/validate/{key}", response_model=VaultValidateResponse, dependencies=[Depends(require_auth)])
async def validate_vault_value(
    key: str,
    payload: VaultValidateRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Validate candidate value for a managed key."""
    service = get_config_service()
    errors = service.validate_vault_candidate(key, payload.value)
    return VaultValidateResponse(valid=len(errors) == 0, errors=errors)


@router.post("/vault/generate/{key}", response_model=VaultGenerateResponse, dependencies=[Depends(require_auth)])
async def generate_vault_value(
    key: str,
    payload: VaultGenerateRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Generate and persist secure values for generator-capable keys."""
    if not _is_admin(principal):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required for secret generation")

    service = get_config_service()
    try:
        return await service.generate_vault_value(
            db,
            key=key,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            reason=payload.reason,
            length=payload.length,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _ = exc
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Config storage unavailable",
        ) from exc


@router.get("/vault/rotate/pending", response_model=VaultRotationListResponse, dependencies=[Depends(require_auth)])
async def list_pending_rotation_requests(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """List pending vault rotation requests."""
    if not _can_write_vault(principal):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role for rotation requests")

    service = get_config_service()
    try:
        items = await service.list_rotation_requests(db)
        return VaultRotationListResponse(items=items, total=len(items))
    except Exception as exc:
        _ = exc
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Config storage unavailable") from exc


@router.post("/vault/rotate/{key}/request", response_model=VaultRotationRequestResponse, dependencies=[Depends(require_auth)])
async def request_rotation(
    key: str,
    payload: VaultRotationRequestCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Create a pending rotation request for a vault key."""
    if not _can_write_vault(principal):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role for rotation requests")

    service = get_config_service()
    try:
        return await service.create_rotation_request(
            db,
            key=key,
            value=payload.value,
            generate=payload.generate,
            length=payload.length,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _ = exc
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Config storage unavailable") from exc


@router.post("/vault/rotate/{key}/approve", response_model=VaultValueResponse, dependencies=[Depends(require_auth)])
async def approve_rotation(
    key: str,
    payload: VaultRotationDecisionRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Approve and activate a pending vault rotation request (admin only)."""
    if not _is_admin(principal):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required for approval")

    service = get_config_service()
    try:
        return await service.approve_rotation_request(
            db,
            key=key,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _ = exc
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Config storage unavailable") from exc


@router.post("/vault/rotate/{key}/reject", response_model=VaultRotationRequestResponse, dependencies=[Depends(require_auth)])
async def reject_rotation(
    key: str,
    payload: VaultRotationDecisionRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Reject and clear a pending vault rotation request (admin only)."""
    if not _is_admin(principal):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required for rejection")

    service = get_config_service()
    try:
        return await service.reject_rotation_request(
            db,
            key=key,
            actor_id=principal.principal_id,
            actor_type=principal.principal_type.value,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        _ = exc
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Config storage unavailable") from exc
