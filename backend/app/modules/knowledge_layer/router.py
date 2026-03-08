from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db

from .schemas import KnowledgeItemCreate, KnowledgeItemListResponse, KnowledgeItemResponse, KnowledgeSearchQuery, RunLessonIngestResponse
from .service import get_knowledge_layer_service


router = APIRouter(prefix="/api/knowledge-items", tags=["knowledge-layer"], dependencies=[Depends(require_auth)])


@router.post("", response_model=KnowledgeItemResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_item(
    payload: KnowledgeItemCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    item = await get_knowledge_layer_service().create_item(db, payload, principal)
    return KnowledgeItemResponse.model_validate(item)


@router.get("/{item_id}", response_model=KnowledgeItemResponse)
async def get_knowledge_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    item = await get_knowledge_layer_service().get_item(db, item_id, principal.tenant_id)
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
    items = await get_knowledge_layer_service().search(db, principal.tenant_id, KnowledgeSearchQuery(query=query, type=type, module=module, limit=limit))
    return KnowledgeItemListResponse(items=[KnowledgeItemResponse.model_validate(item) for item in items], total=len(items))


@router.post("/run-lessons/{skill_run_id}", response_model=RunLessonIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_run_lesson(
    skill_run_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    try:
        item = await get_knowledge_layer_service().ingest_run_lesson(db, skill_run_id, principal)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RunLessonIngestResponse(skill_run_id=skill_run_id, knowledge_item=KnowledgeItemResponse.model_validate(item))
