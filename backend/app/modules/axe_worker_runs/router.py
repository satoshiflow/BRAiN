"""AXE worker run endpoints (session-scoped polling surface)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, require_auth
from app.core.database import get_db

from .schemas import AXEWorkerRunCreateRequest, AXEWorkerRunListResponse, AXEWorkerRunResponse
from .service import AXEWorkerRunService


router = APIRouter(
    prefix="/api/axe",
    tags=["axe-workers"],
    dependencies=[Depends(require_auth)],
)


def get_service(db: AsyncSession = Depends(get_db)) -> AXEWorkerRunService:
    return AXEWorkerRunService(db)


@router.post("/workers", response_model=AXEWorkerRunResponse, status_code=status.HTTP_201_CREATED)
async def create_worker_run(
    payload: AXEWorkerRunCreateRequest,
    principal: Principal = Depends(require_auth),
    service: AXEWorkerRunService = Depends(get_service),
) -> AXEWorkerRunResponse:
    try:
        return await service.create_worker_run(principal=principal, payload=payload)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found") from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found") from exc


@router.get("/workers/{worker_run_id}", response_model=AXEWorkerRunResponse)
async def get_worker_run(
    worker_run_id: str,
    principal: Principal = Depends(require_auth),
    service: AXEWorkerRunService = Depends(get_service),
) -> AXEWorkerRunResponse:
    item = await service.get_worker_run(principal=principal, worker_run_id=worker_run_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker run not found")
    return item


@router.get("/sessions/{session_id}/workers", response_model=AXEWorkerRunListResponse)
async def list_worker_runs_for_session(
    session_id: UUID,
    principal: Principal = Depends(require_auth),
    service: AXEWorkerRunService = Depends(get_service),
) -> AXEWorkerRunListResponse:
    try:
        items = await service.list_worker_runs_for_session(principal=principal, session_id=session_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found") from exc
    return AXEWorkerRunListResponse(items=items)
