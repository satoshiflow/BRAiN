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
from . import service as external_apps_service
from .service import PaperclipHandoffService


router = APIRouter(tags=["external-apps"])


def _resolve_service(getter_name: str) -> PaperclipHandoffService:
    return getattr(external_apps_service, getter_name)()  # type: ignore[no-any-return]


def _build_executor_router(prefix: str, getter_name: str) -> APIRouter:
    executor_router = APIRouter(prefix=f"/api/external-apps/{prefix}", tags=["external-apps"])

    @executor_router.post(
        "/handoff",
        response_model=PaperclipHandoffResponse,
        dependencies=[Depends(require_auth), Depends(require_viewer)],
    )
    async def create_handoff(
        payload: PaperclipHandoffRequest,
        request: Request,
        db: AsyncSession = Depends(get_db),
        principal: Principal = Depends(get_current_principal),
    ) -> PaperclipHandoffResponse:
        service = _resolve_service(getter_name)
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

    @executor_router.post(
        "/handoff/exchange",
        response_model=PaperclipHandoffExchangeResponse,
    )
    async def exchange_handoff(
        payload: PaperclipHandoffExchangeRequest,
        db: AsyncSession = Depends(get_db),
    ) -> PaperclipHandoffExchangeResponse:
        service = _resolve_service(getter_name)
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

    @executor_router.get(
        "/executions/{task_id}",
        response_model=PaperclipExecutionContextResponse,
        dependencies=[Depends(require_auth), Depends(require_viewer)],
    )
    async def get_execution_context(
        task_id: str,
        db: AsyncSession = Depends(get_db),
        principal: Principal = Depends(get_current_principal),
    ) -> PaperclipExecutionContextResponse:
        service = _resolve_service(getter_name)
        try:
            return await service.get_execution_context(db, task_id=task_id, principal=principal)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @executor_router.post(
        "/actions",
        response_model=PaperclipActionRequestResponse,
    )
    async def request_action(
        payload: PaperclipActionRequest,
        db: AsyncSession = Depends(get_db),
    ) -> PaperclipActionRequestResponse:
        service = _resolve_service(getter_name)
        try:
            return await service.request_action(db, payload=payload)
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except JWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired handoff token") from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @executor_router.get(
        "/action-requests",
        response_model=PaperclipActionRequestListResponse,
        dependencies=[Depends(require_auth), Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN, SystemRole.SERVICE))],
    )
    async def list_action_requests(
        db: AsyncSession = Depends(get_db),
        principal: Principal = Depends(get_current_principal),
    ) -> PaperclipActionRequestListResponse:
        return await _resolve_service(getter_name).list_action_requests(db, principal=principal)

    @executor_router.post(
        "/action-requests/{request_id}/approve",
        response_model=PaperclipActionRequestItem,
        dependencies=[Depends(require_auth), Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))],
    )
    async def approve_action_request(
        request_id: str,
        payload: PaperclipActionRequestDecision,
        db: AsyncSession = Depends(get_db),
        principal: Principal = Depends(get_current_principal),
    ) -> PaperclipActionRequestItem:
        service = _resolve_service(getter_name)
        try:
            return await service.approve_action_request(db, principal=principal, request_id=request_id, payload=payload)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @executor_router.post(
        "/action-requests/{request_id}/reject",
        response_model=PaperclipActionRequestItem,
        dependencies=[Depends(require_auth), Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))],
    )
    async def reject_action_request(
        request_id: str,
        payload: PaperclipActionRequestDecision,
        db: AsyncSession = Depends(get_db),
        principal: Principal = Depends(get_current_principal),
    ) -> PaperclipActionRequestItem:
        service = _resolve_service(getter_name)
        try:
            return await service.reject_action_request(db, principal=principal, request_id=request_id, payload=payload)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return executor_router


router.include_router(_build_executor_router("paperclip", "get_paperclip_handoff_service"))
router.include_router(_build_executor_router("openclaw", "get_openclaw_handoff_service"))
