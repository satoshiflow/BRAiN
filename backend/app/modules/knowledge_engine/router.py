from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db

from .schemas import (
    CapabilityLinkRequest,
    CapabilitySearchRequest,
    CapabilityStoreRequest,
    KnowledgeIngestRequest,
    KnowledgeIngestResponse,
    KnowledgeItemCreate,
    KnowledgeItemResponse,
    KnowledgeItemUpdate,
    KnowledgeLinkCreate,
    KnowledgeLinkResponse,
    KnowledgeListResponse,
    HelpDocListResponse,
    KnowledgeSearchQuery,
    KnowledgeVersionCreate,
    KnowledgeVersionResponse,
    RelatedKnowledgeResponse,
    SemanticSearchRequest,
)
from .service import get_knowledge_engine_service


router = APIRouter(prefix="/api/knowledge-engine", tags=["knowledge-engine"], dependencies=[Depends(require_auth)])


def _to_item_response(row: dict) -> KnowledgeItemResponse:
    return KnowledgeItemResponse(
        id=row["id"],
        tenant_id=row.get("tenant_id"),
        title=row["title"],
        content=row["content"],
        type=row["type"],
        tags=row.get("tags") or [],
        visibility=row.get("visibility") or "tenant",
        metadata=row.get("metadata") or {},
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("/items", response_model=KnowledgeItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: KnowledgeItemCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    row = await get_knowledge_engine_service().create_knowledge_item(db, principal, payload)
    return _to_item_response(row)


@router.patch("/items/{item_id}", response_model=KnowledgeItemResponse)
async def update_item(
    item_id: UUID,
    payload: KnowledgeItemUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    row = await get_knowledge_engine_service().update_knowledge_item(db, principal, item_id, payload)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge item not found")
    return _to_item_response(row)


@router.get("/items", response_model=KnowledgeListResponse)
async def list_items(
    query: str | None = Query(default=None),
    type: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    items = await get_knowledge_engine_service().list_items(
        db, principal, query=query, type_filter=type, tag=tag, limit=limit
    )
    return KnowledgeListResponse(items=[_to_item_response(item) for item in items], total=len(items))


@router.get("/items/{item_id}", response_model=KnowledgeItemResponse)
async def get_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    item = await get_knowledge_engine_service().get_item(db, principal, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge item not found")
    return _to_item_response(item)


@router.post("/links", response_model=KnowledgeLinkResponse, status_code=status.HTTP_201_CREATED)
async def link_items(
    payload: KnowledgeLinkCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    row = await get_knowledge_engine_service().link_knowledge_items(
        db, principal, payload.source_id, payload.target_id, payload.relation_type
    )
    return KnowledgeLinkResponse(**row)


@router.get("/items/{item_id}/related", response_model=RelatedKnowledgeResponse)
async def get_related(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    items = await get_knowledge_engine_service().get_related_items(db, principal, item_id)
    return RelatedKnowledgeResponse(item_id=item_id, related=[_to_item_response(item) for item in items])


@router.post("/items/{item_id}/versions", response_model=KnowledgeVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_version(
    item_id: UUID,
    payload: KnowledgeVersionCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    row = await get_knowledge_engine_service().version_knowledge_item(db, principal, item_id, payload.diff)
    return KnowledgeVersionResponse(**row)


@router.get("/items/{item_id}/versions", response_model=list[KnowledgeVersionResponse])
async def list_versions(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    rows = await get_knowledge_engine_service().list_versions(db, principal, item_id)
    return [KnowledgeVersionResponse(**row) for row in rows]


@router.get("/search", response_model=KnowledgeListResponse)
async def search_knowledge(
    query: str = Query(..., min_length=1),
    type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    items = await get_knowledge_engine_service().list_items(db, principal, query=query, type_filter=type, limit=limit)
    return KnowledgeListResponse(items=[_to_item_response(item) for item in items], total=len(items))


@router.post("/semantic-search", response_model=KnowledgeListResponse)
async def semantic_search(
    payload: SemanticSearchRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    items = await get_knowledge_engine_service().semantic_search(db, principal, payload.query, payload.limit)
    return KnowledgeListResponse(items=[_to_item_response(item) for item in items], total=len(items))


@router.post("/ingest", response_model=KnowledgeIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_knowledge(
    payload: KnowledgeIngestRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    item, chunk_count = await get_knowledge_engine_service().ingest(db, principal, payload)
    return KnowledgeIngestResponse(item=_to_item_response(item), chunk_count=chunk_count)


@router.get("/help", response_model=HelpDocListResponse)
async def list_help_docs(
    surface: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    items = await get_knowledge_engine_service().list_help_docs(db, principal, surface=surface, limit=limit)
    return HelpDocListResponse(items=[_to_item_response(item) for item in items], total=len(items))


@router.get("/help/{help_key}", response_model=KnowledgeItemResponse)
async def get_help_doc(
    help_key: str,
    surface: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    item = await get_knowledge_engine_service().get_help_doc(db, principal, help_key, surface=surface)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Help document not found")
    return _to_item_response(item)


# Skill-facing capability endpoints
@router.post("/capabilities/search", response_model=KnowledgeListResponse)
async def capability_search(
    payload: CapabilitySearchRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    items = await get_knowledge_engine_service().list_items(
        db,
        principal,
        query=payload.query,
        type_filter=payload.type,
        limit=payload.limit,
    )
    return KnowledgeListResponse(items=[_to_item_response(item) for item in items], total=len(items))


@router.post("/capabilities/store", response_model=KnowledgeItemResponse, status_code=status.HTTP_201_CREATED)
async def capability_store(
    payload: CapabilityStoreRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    row = await get_knowledge_engine_service().create_knowledge_item(db, principal, payload.item)
    return _to_item_response(row)


@router.post("/capabilities/link", response_model=KnowledgeLinkResponse, status_code=status.HTTP_201_CREATED)
async def capability_link(
    payload: CapabilityLinkRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    row = await get_knowledge_engine_service().link_knowledge_items(
        db,
        principal,
        payload.source_id,
        payload.target_id,
        payload.relation_type,
    )
    return KnowledgeLinkResponse(**row)
