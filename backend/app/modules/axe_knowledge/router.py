"""
AXE Knowledge Documents - FastAPI Router

REST API endpoints for knowledge document management.
TASK-003: Backend Knowledge Module - COMPLETE IMPLEMENTATION

Endpoints:
- GET /                         - List documents with filters (OPERATOR)
- GET /top                      - Get top documents by importance (PUBLIC for middleware)
- GET /stats                    - Get category statistics (OPERATOR)
- GET /{document_id}            - Get specific document (OPERATOR)
- POST /                        - Create document (ADMIN)
- PATCH /{document_id}          - Update document (ADMIN)
- DELETE /{document_id}         - Delete document (ADMIN)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import require_role, UserRole, get_current_principal, Principal
from .service import AXEKnowledgeService
from .schemas import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentUpdate,
    KnowledgeDocumentResponse,
    KnowledgeDocumentListResponse,
    DocumentCategory
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/axe/knowledge", tags=["axe-knowledge"])


def get_service(db: AsyncSession = Depends(get_db)) -> AXEKnowledgeService:
    """Dependency injection for service layer"""
    return AXEKnowledgeService(db)


@router.get("/", response_model=List[KnowledgeDocumentListResponse])
async def list_documents(
    category: Optional[DocumentCategory] = Query(None, description="Filter by category"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags (OR logic)"),
    search: Optional[str] = Query(None, description="Search in name and content"),
    enabled_only: bool = Query(True, description="Only return enabled documents"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    service: AXEKnowledgeService = Depends(get_service),
    principal: Principal = Depends(require_role(UserRole.OPERATOR))
):
    """
    List knowledge documents with optional filters (OPERATOR role required)

    Supports:
    - Category filtering (system, domain, procedure, faq, reference, custom)
    - Tag filtering with OR logic (documents with any matching tag)
    - Full-text search in name and content
    - Pagination with limit/offset
    - Filter by enabled status

    Returns list of documents sorted by importance score (desc) and created date.
    """
    try:
        documents = await service.get_all(
            category=category,
            tags=tags,
            search_query=search,
            enabled_only=enabled_only,
            limit=limit,
            offset=offset
        )
        return documents
    except Exception as e:
        logger.error(f"Error listing documents: {e}", exc_info=True)
        raise HTTPException(500, "Failed to list documents")


@router.get("/top", response_model=List[KnowledgeDocumentResponse])
async def get_top_documents(
    limit: int = Query(3, ge=1, le=10, description="Number of top documents"),
    category: Optional[DocumentCategory] = Query(None, description="Filter by category"),
    service: AXEKnowledgeService = Depends(get_service)
):
    """
    Get top documents by importance score (PUBLIC endpoint - no auth)

    Used by SystemPromptMiddleware to inject most relevant knowledge into chat.
    Returns full document content including system prompts.

    No authentication required for performance - this is called on every chat request.
    """
    try:
        documents = await service.get_top_documents(
            limit=limit,
            enabled_only=True,
            category=category
        )
        return documents
    except Exception as e:
        logger.error(f"Error getting top documents: {e}", exc_info=True)
        raise HTTPException(500, "Failed to get top documents")


@router.get("/stats")
async def get_category_stats(
    service: AXEKnowledgeService = Depends(get_service),
    principal: Principal = Depends(require_role(UserRole.OPERATOR))
):
    """
    Get statistics about knowledge documents (OPERATOR role required)

    Returns document count per category for enabled documents.
    Useful for dashboard and analytics.
    """
    try:
        stats = await service.get_categories_stats()
        return {
            "by_category": stats,
            "total": sum(stats.values())
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(500, "Failed to get stats")


@router.get("/{document_id}", response_model=KnowledgeDocumentResponse)
async def get_document(
    document_id: str,
    service: AXEKnowledgeService = Depends(get_service),
    principal: Principal = Depends(require_role(UserRole.OPERATOR))
):
    """
    Get specific document by ID with full content (OPERATOR role required)

    Returns complete document including content, metadata, and access statistics.
    Increments access_count for usage tracking.
    """
    try:
        document = await service.get_by_id(document_id)
        if not document:
            raise HTTPException(404, f"Document {document_id} not found")

        # Increment access count for tracking (fire and forget)
        try:
            await service.increment_access(document_id)
        except Exception as e:
            logger.warning(f"Failed to increment access count: {e}")
            # Don't fail the request if access count update fails

        return document
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {e}", exc_info=True)
        raise HTTPException(500, "Failed to get document")


@router.post("/", response_model=KnowledgeDocumentResponse, status_code=201)
async def create_document(
    data: KnowledgeDocumentCreate,
    service: AXEKnowledgeService = Depends(get_service),
    principal: Principal = Depends(require_role(UserRole.ADMIN))
):
    """
    Create new knowledge document (ADMIN role required)

    Creates a new document with markdown content, category, tags, and metadata.
    Documents are enabled by default and can have importance scores for prioritization.

    Only ADMIN users can create documents to maintain content quality.
    """
    try:
        document = await service.create(data, created_by=principal.agent_id)
        logger.info(f"Document created: {document.name} by {principal.agent_id}")
        return document
    except Exception as e:
        logger.error(f"Error creating document: {e}", exc_info=True)
        raise HTTPException(500, "Failed to create document")


@router.patch("/{document_id}", response_model=KnowledgeDocumentResponse)
async def update_document(
    document_id: str,
    data: KnowledgeDocumentUpdate,
    service: AXEKnowledgeService = Depends(get_service),
    principal: Principal = Depends(require_role(UserRole.ADMIN))
):
    """
    Update existing document (ADMIN role required)

    Supports partial updates - only provided fields will be updated.
    Version number is automatically incremented on each update.

    Only ADMIN users can update documents to maintain content integrity.
    """
    try:
        document = await service.update(document_id, data)
        if not document:
            raise HTTPException(404, f"Document {document_id} not found")

        logger.info(f"Document updated: {document.name} by {principal.agent_id}")
        return document
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating document {document_id}: {e}", exc_info=True)
        raise HTTPException(500, "Failed to update document")


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    service: AXEKnowledgeService = Depends(get_service),
    principal: Principal = Depends(require_role(UserRole.ADMIN))
):
    """
    Delete document (ADMIN role required)

    Permanently deletes the document and all associated data.
    This operation cannot be undone.

    Only ADMIN users can delete documents to prevent accidental data loss.
    """
    try:
        success = await service.delete(document_id)
        if not success:
            raise HTTPException(404, f"Document {document_id} not found")

        logger.info(f"Document deleted: {document_id} by {principal.agent_id}")
        return None  # 204 No Content
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}", exc_info=True)
        raise HTTPException(500, "Failed to delete document")
