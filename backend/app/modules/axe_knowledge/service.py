"""AXE Knowledge Service Layer.

This module provides the service layer for AXE Knowledge document management,
including CRUD operations, search, and statistics.

TASK-003: AXE Knowledge Service Layer
"""
from __future__ import annotations

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from .models import AXEKnowledgeDocumentORM
from .schemas import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentUpdate,
    KnowledgeDocumentResponse,
    KnowledgeDocumentListResponse,
    DocumentCategory,
)


class CategoryStats(BaseModel):
    """Statistics for a document category."""
    category: str
    count: int


class AXEKnowledgeService:
    """Service layer for AXE Knowledge document management."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.
        
        Args:
            db: Async SQLAlchemy session
        """
        self.db = db

    def _orm_to_list_response(self, orm: AXEKnowledgeDocumentORM) -> KnowledgeDocumentListResponse:
        """Convert ORM object to list response schema."""
        return KnowledgeDocumentListResponse(
            id=str(orm.id),  # FIX: Convert UUID to string
            name=orm.name,
            description=orm.description,
            category=orm.category,
            content_type=orm.content_type,
            tags=orm.tags if orm.tags else [],
            is_enabled=orm.is_enabled,
            access_count=orm.access_count,
            importance_score=orm.importance_score,
            created_at=orm.created_at,
            updated_at=orm.updated_at
        )

    def _orm_to_response(self, orm: AXEKnowledgeDocumentORM) -> KnowledgeDocumentResponse:
        """Convert ORM object to full response schema."""
        # CRITICAL FIX: Access doc_metadata directly (not metadata - that's SQLAlchemy reserved!)
        # The model defines: doc_metadata: Mapped[dict] = mapped_column("metadata", JSON, ...)
        # So the Python attribute is doc_metadata, database column is metadata
        metadata_value = orm.doc_metadata if hasattr(orm, 'doc_metadata') and orm.doc_metadata else {}

        return KnowledgeDocumentResponse(
            id=str(orm.id),  # FIX: Convert UUID to string
            name=orm.name,
            description=orm.description,
            category=orm.category,
            content=orm.content,
            content_type=orm.content_type,
            metadata=metadata_value,  # Use doc_metadata attribute
            tags=orm.tags if orm.tags else [],
            is_enabled=orm.is_enabled,
            access_count=orm.access_count,
            importance_score=orm.importance_score,
            version=orm.version,
            parent_id=str(orm.parent_id) if orm.parent_id else None,  # FIX: Convert UUID to string
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            created_by=orm.created_by
        )

    async def get_all(
        self,
        category: Optional[str] = None,
        enabled_only: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        tags: Optional[List[str]] = None,
        search_query: Optional[str] = None,
    ) -> List[KnowledgeDocumentListResponse]:
        """Get all knowledge documents with optional filtering.
        
        Args:
            category: Filter by category name
            enabled_only: If True, only return enabled documents
            limit: Maximum number of documents to return
            offset: Pagination offset
            tags: Filter by tags (OR logic - any matching tag)
            search_query: Search in name and content
            
        Returns:
            List of KnowledgeDocumentListResponse schemas
        """
        query = select(AXEKnowledgeDocumentORM)

        conditions = []
        if enabled_only:
            conditions.append(AXEKnowledgeDocumentORM.is_enabled == True)
        if category:
            conditions.append(AXEKnowledgeDocumentORM.category == category)
        if tags:
            # OR logic: document has ANY of the provided tags
            tag_conditions = [AXEKnowledgeDocumentORM.tags.contains([tag]) for tag in tags]
            conditions.append(or_(*tag_conditions))
        if search_query:
            search_term = f"%{search_query}%"
            conditions.append(
                or_(
                    AXEKnowledgeDocumentORM.name.ilike(search_term),
                    AXEKnowledgeDocumentORM.content.ilike(search_term),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(AXEKnowledgeDocumentORM.importance_score))

        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        result = await self.db.execute(query)
        orm_objects = result.scalars().all()
        return [self._orm_to_list_response(orm) for orm in orm_objects]

    async def get_top_documents(
        self,
        limit: int = 5,
        enabled_only: bool = True,
        category: Optional[str] = None,
    ) -> List[KnowledgeDocumentResponse]:
        """Get top documents for middleware/context injection.

        Returns documents ordered by importance score (highest first).
        Full content included for middleware.

        Args:
            limit: Maximum number of documents to return
            enabled_only: If True, only return enabled documents
            category: Optional category filter

        Returns:
            List of KnowledgeDocumentResponse schemas
        """
        # Get ORM objects directly for full content
        query = select(AXEKnowledgeDocumentORM)
        conditions = []

        if enabled_only:
            conditions.append(AXEKnowledgeDocumentORM.is_enabled == True)
        if category:
            conditions.append(AXEKnowledgeDocumentORM.category == category)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(AXEKnowledgeDocumentORM.importance_score)).limit(limit)

        result = await self.db.execute(query)
        orm_objects = result.scalars().all()
        return [self._orm_to_response(orm) for orm in orm_objects]

    async def get_by_id(self, document_id: str) -> Optional[KnowledgeDocumentResponse]:
        """Get a knowledge document by its ID.

        Args:
            document_id: ID of the document (UUID string)

        Returns:
            KnowledgeDocumentResponse schema or None if not found
        """
        result = await self.db.execute(
            select(AXEKnowledgeDocumentORM).where(AXEKnowledgeDocumentORM.id == document_id)
        )
        orm = result.scalar_one_or_none()
        return self._orm_to_response(orm) if orm else None

    async def search(
        self,
        query: str,
        enabled_only: bool = True,
        limit: Optional[int] = None,
    ) -> List[AXEKnowledgeDocumentORM]:
        """Full-text search in name, content, and description.
        
        Args:
            query: Search query string
            enabled_only: If True, only search enabled documents
            limit: Maximum number of results to return
            
        Returns:
            List of matching AXEKnowledgeDocumentORM instances
        """
        search_term = f"%{query}%"
        
        conditions = [
            or_(
                AXEKnowledgeDocumentORM.name.ilike(search_term),
                AXEKnowledgeDocumentORM.content.ilike(search_term),
                AXEKnowledgeDocumentORM.description.ilike(search_term),
            )
        ]
        
        if enabled_only:
            conditions.append(AXEKnowledgeDocumentORM.is_enabled == True)
            
        stmt = select(AXEKnowledgeDocumentORM).where(and_(*conditions))
        
        if limit:
            stmt = stmt.limit(limit)
            
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create(self, data: KnowledgeDocumentCreate, created_by: str) -> KnowledgeDocumentResponse:
        """Create a new knowledge document.

        Args:
            data: Document creation data
            created_by: ID of the user creating the document

        Returns:
            Created KnowledgeDocumentResponse schema
        """
        document = AXEKnowledgeDocumentORM(
            name=data.name,
            content=data.content,
            description=data.description,
            category=data.category.value if isinstance(data.category, DocumentCategory) else data.category,
            content_type=data.content_type,
            doc_metadata=data.metadata or {},  # Fixed: use doc_metadata
            tags=data.tags or [],
            version=1,
            access_count=0,
            is_enabled=True,
            importance_score=data.importance_score,
            parent_id=data.parent_id,
            created_by=created_by,
        )

        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)

        logger.info(f"[AXEKnowledge] Created document: {document.id} - {document.name}")
        return self._orm_to_response(document)

    async def update(
        self,
        document_id: str,
        data: KnowledgeDocumentUpdate,
    ) -> Optional[KnowledgeDocumentResponse]:
        """Update a knowledge document.

        Automatically increments the version number.

        Args:
            document_id: ID of the document to update
            data: Document update data

        Returns:
            Updated KnowledgeDocumentResponse schema or None if not found
        """
        # Get ORM object directly for update
        result = await self.db.execute(
            select(AXEKnowledgeDocumentORM).where(AXEKnowledgeDocumentORM.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            return None

        # Update fields if provided
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            # Handle category enum
            if field == 'category' and isinstance(value, DocumentCategory):
                value = value.value
            # Map metadata to doc_metadata
            if field == 'metadata':
                field = 'doc_metadata'
            # Skip None values (not set)
            if value is not None and hasattr(document, field):
                setattr(document, field, value)

        # Increment version
        document.version += 1

        await self.db.commit()
        await self.db.refresh(document)

        logger.info(f"[AXEKnowledge] Updated document: {document.id} - v{document.version}")
        return self._orm_to_response(document)

    async def delete(self, document_id: str) -> bool:
        """Hard delete a knowledge document.

        Args:
            document_id: ID of the document to delete

        Returns:
            True if deleted, False if not found
        """
        result = await self.db.execute(
            select(AXEKnowledgeDocumentORM).where(AXEKnowledgeDocumentORM.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            return False

        await self.db.delete(document)
        await self.db.commit()

        logger.info(f"[AXEKnowledge] Deleted document: {document_id}")
        return True

    async def increment_access(self, document_id: str) -> bool:
        """Increment the access count for a document.

        Args:
            document_id: ID of the document

        Returns:
            True if successfully incremented, False if document not found
        """
        result = await self.db.execute(
            select(AXEKnowledgeDocumentORM).where(AXEKnowledgeDocumentORM.id == document_id)
        )
        document = result.scalar_one_or_none()
        if not document:
            return False

        document.access_count += 1

        await self.db.commit()

        logger.debug(f"[AXEKnowledge] Incremented access: {document.id} (count: {document.access_count})")
        return True

    async def get_categories_stats(self) -> Dict[str, int]:
        """Get document count per category.

        Returns:
            Dict mapping category name to document count
        """
        stmt = (
            select(
                AXEKnowledgeDocumentORM.category,
                func.count(AXEKnowledgeDocumentORM.id).label("count"),
            )
            .where(AXEKnowledgeDocumentORM.is_enabled == True)
            .group_by(AXEKnowledgeDocumentORM.category)
            .order_by(desc("count"))
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return {row.category: row.count for row in rows}
