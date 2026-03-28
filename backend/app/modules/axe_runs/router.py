from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth_deps import Principal, require_auth

from .schemas import AXERunCreate, AXERunListResponse, AXERunResponse
from .service import get_axe_run_service

router = APIRouter(
    prefix="/api/axe/runs",
    tags=["axe-runs"],
)


@router.post("", response_model=AXERunResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    payload: AXERunCreate,
    principal: Principal = Depends(require_auth),
):
    service = get_axe_run_service()
    run = await service.create_run(payload, principal)
    return run


@router.get("/{run_id}", response_model=AXERunResponse)
async def get_run(
    run_id: UUID,
    principal: Principal = Depends(require_auth),
):
    service = get_axe_run_service()
    run = await service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.get("", response_model=AXERunListResponse)
async def list_runs(
    session_id: UUID | None = None,
    limit: int = 20,
    principal: Principal = Depends(require_auth),
):
    service = get_axe_run_service()
    return await service.list_runs(principal, session_id, limit)
