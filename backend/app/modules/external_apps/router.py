from __future__ import annotations

from jose import JWTError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role, require_viewer
from app.core.database import get_db

from .schemas import (
    PaperclipActionRequest,
    PaperclipActionRequestDecision,
    PaperclipActionRequestItem,
    PaperclipActionRequestListResponse,
    PaperclipActionRequestResponse,
    PaperclipExecutionContextResponse,
    PaperclipHandoffExchangeRequest,
    PaperclipHandoffExchangeResponse,
    PaperclipHandoffRequest,
    PaperclipHandoffResponse,
)
from .service import get_paperclip_handoff_service


router = APIRouter(
    prefix="/api/external-apps/paperclip",
    tags=["external-apps"],
)


@router.post(
    "/handoff",
    response_model=PaperclipHandoffResponse,
    dependencies=[Depends(require_auth), Depends(require_viewer)],
)
async def create_paperclip_handoff(
    payload: PaperclipHandoffRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> PaperclipHandoffResponse:
    service = get_paperclip_handoff_service()
    try:
        return await service.create_handoff(
            db,
            principal=principal,
            payload=payload,
            backend_base_url=str(request.base_url).rstrip("/"),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post(
    "/handoff/exchange",
    response_model=PaperclipHandoffExchangeResponse,
)
async def exchange_paperclip_handoff(
    payload: PaperclipHandoffExchangeRequest,
    db: AsyncSession = Depends(get_db),
) -> PaperclipHandoffExchangeResponse:
    service = get_paperclip_handoff_service()
    try:
        return await service.exchange_handoff(db, payload=payload)
    except PermissionError as exc:
        await service.record_exchange_failure(db, payload=payload, reason=str(exc))
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except JWTError as exc:
        await service.record_exchange_failure(db, payload=payload, reason="Invalid or expired handoff token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired handoff token") from exc
    except ValueError as exc:
        await service.record_exchange_failure(db, payload=payload, reason=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        await service.record_exchange_failure(db, payload=payload, reason=str(exc))
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get(
    "/executions/{task_id}",
    response_model=PaperclipExecutionContextResponse,
    dependencies=[Depends(require_auth), Depends(require_viewer)],
)
async def get_paperclip_execution_context(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> PaperclipExecutionContextResponse:
    service = get_paperclip_handoff_service()
    try:
        return await service.get_execution_context(db, task_id=task_id, principal=principal)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/actions",
    response_model=PaperclipActionRequestResponse,
)
async def request_paperclip_action(
    payload: PaperclipActionRequest,
    db: AsyncSession = Depends(get_db),
) -> PaperclipActionRequestResponse:
    service = get_paperclip_handoff_service()
    try:
        return await service.request_action(db, payload=payload)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired handoff token") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/action-requests",
    response_model=PaperclipActionRequestListResponse,
    dependencies=[Depends(require_auth), Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN, SystemRole.SERVICE))],
)
async def list_paperclip_action_requests(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> PaperclipActionRequestListResponse:
    return await get_paperclip_handoff_service().list_action_requests(db, principal=principal)


@router.post(
    "/action-requests/{request_id}/approve",
    response_model=PaperclipActionRequestItem,
    dependencies=[Depends(require_auth), Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))],
)
async def approve_paperclip_action_request(
    request_id: str,
    payload: PaperclipActionRequestDecision,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> PaperclipActionRequestItem:
    service = get_paperclip_handoff_service()
    try:
        return await service.approve_action_request(db, principal=principal, request_id=request_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/action-requests/{request_id}/reject",
    response_model=PaperclipActionRequestItem,
    dependencies=[Depends(require_auth), Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))],
)
async def reject_paperclip_action_request(
    request_id: str,
    payload: PaperclipActionRequestDecision,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> PaperclipActionRequestItem:
    service = get_paperclip_handoff_service()
    try:
        return await service.reject_action_request(db, principal=principal, request_id=request_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
