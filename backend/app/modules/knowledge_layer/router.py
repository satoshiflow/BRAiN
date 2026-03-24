from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db
from app.modules.module_lifecycle.service import get_module_lifecycle_service

from .schemas import KnowledgeItemCreate, KnowledgeItemListResponse, KnowledgeItemResponse, KnowledgeSearchQuery, RunLessonIngestResponse
from .service import get_knowledge_layer_service


router = APIRouter(prefix="/api/knowledge-items", tags=["knowledge-layer"], dependencies=[Depends(require_auth)])


def _require_tenant(principal: Principal) -> str:
    if not principal.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required")
    return principal.tenant_id


async def _ensure_knowledge_layer_writable(db: AsyncSession) -> None:
    if db is None:
        return
    item = await get_module_lifecycle_service().get_module(db, "knowledge_layer")
    if item and item.lifecycle_status in {"deprecated", "retired"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"knowledge_layer is {item.lifecycle_status}; writes are blocked",
        )


@router.post("", response_model=KnowledgeItemResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_item(
    payload: KnowledgeItemCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    await _ensure_knowledge_layer_writable(db)
    _require_tenant(principal)
    item = await get_knowledge_layer_service().create_item(db, payload, principal)
    return KnowledgeItemResponse.model_validate(item)


@router.get("/{item_id}", response_model=KnowledgeItemResponse)
async def get_knowledge_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    tenant_id = _require_tenant(principal)
    item = await get_knowledge_layer_service().get_item(db, item_id, tenant_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    return KnowledgeItemResponse.model_validate(item)


@router.get("", response_model=KnowledgeItemListResponse)
async def search_knowledge_items(
    query: str = Query(..., min_length=1),
    type: str | None = Query(default=None),
    module: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    tenant_id = _require_tenant(principal)
    items = await get_knowledge_layer_service().search(db, tenant_id, KnowledgeSearchQuery(query=query, type=type, module=module, limit=limit))
    return KnowledgeItemListResponse(items=[KnowledgeItemResponse.model_validate(item) for item in items], total=len(items))


@router.post("/run-lessons/{skill_run_id}", response_model=RunLessonIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_run_lesson(
    skill_run_id: UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    _require_tenant(principal)
    await _ensure_knowledge_layer_writable(db)
    try:
        item = await get_knowledge_layer_service().ingest_run_lesson(db, skill_run_id, principal)
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = "Tue, 30 Jun 2026 00:00:00 GMT"
        response.headers["Link"] = f'</api/experience/skill-runs/{skill_run_id}/ingest>; rel="successor-version"'
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RunLessonIngestResponse(skill_run_id=skill_run_id, knowledge_item=KnowledgeItemResponse.model_validate(item))
