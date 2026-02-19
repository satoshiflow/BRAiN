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

    async def get_all(
        self,
        category: Optional[str] = None,
        enabled_only: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        tags: Optional[List[str]] = None,
        search_query: Optional[str] = None,
    ) -> List[AXEKnowledgeDocumentORM]:
        """Get all knowledge documents with optional filtering.
        
        Args:
            category: Filter by category name
            enabled_only: If True, only return enabled documents
            limit: Maximum number of documents to return
            offset: Pagination offset
            tags: Filter by tags (OR logic - any matching tag)
            search_query: Search in name and content
            
        Returns:
            List of AXEKnowledgeDocumentORM instances
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
        return result.scalars().all()

    async def get_top_documents(
        self,
        limit: int = 5,
        enabled_only: bool = True,
        category: Optional[str] = None,
    ) -> List[AXEKnowledgeDocumentORM]:
        """Get top documents for middleware/context injection.
        
        Returns documents ordered by importance score (highest first).
        
        Args:
            limit: Maximum number of documents to return
            enabled_only: If True, only return enabled documents
            category: Optional category filter
            
        Returns:
            List of AXEKnowledgeDocumentORM instances
        """
        return await self.get_all(
            category=category,
            enabled_only=enabled_only,
            limit=limit,
        )

    async def get_by_id(self, document_id: str) -> Optional[AXEKnowledgeDocumentORM]:
        """Get a knowledge document by its ID.
        
        Args:
            document_id: ID of the document (UUID string)
            
        Returns:
            AXEKnowledgeDocumentORM instance or None if not found
        """
        result = await self.db.execute(
            select(AXEKnowledgeDocumentORM).where(AXEKnowledgeDocumentORM.id == document_id)
        )
        return result.scalar_one_or_none()

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

    async def create(self, data: KnowledgeDocumentCreate) -> AXEKnowledgeDocumentORM:
        """Create a new knowledge document.
        
        Args:
            data: Document creation data
            
        Returns:
            Created AXEKnowledgeDocumentORM instance
        """
        document = AXEKnowledgeDocumentORM(
            name=data.name,
            content=data.content,
            description=data.description,
            category=data.category.value if isinstance(data.category, DocumentCategory) else data.category,
            content_type=data.content_type,
            metadata=data.metadata or {},
            tags=data.tags or [],
            version=1,
            access_count=0,
            is_enabled=True,
            importance_score=data.importance_score,
            parent_id=data.parent_id,
        )
        
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        
        logger.info(f"[AXEKnowledge] Created document: {document.id} - {document.name}")
        return document

    async def update(
        self,
        document_id: str,
        data: KnowledgeDocumentUpdate,
    ) -> Optional[AXEKnowledgeDocumentORM]:
        """Update a knowledge document.
        
        Automatically increments the version number.
        
        Args:
            document_id: ID of the document to update
            data: Document update data
            
        Returns:
            Updated AXEKnowledgeDocumentORM instance or None if not found
        """
        document = await self.get_by_id(document_id)
        if not document:
            return None
            
        # Update fields if provided
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            # Handle category enum
            if field == 'category' and isinstance(value, DocumentCategory):
                value = value.value
            # Skip None values (not set)
            if value is not None and hasattr(document, field):
                setattr(document, field, value)
        
        # Increment version
        document.version += 1
        
        await self.db.commit()
        await self.db.refresh(document)
        
        logger.info(f"[AXEKnowledge] Updated document: {document.id} - v{document.version}")
        return document

    async def delete(self, document_id: str) -> Optional[AXEKnowledgeDocumentORM]:
        """Soft delete a knowledge document (sets is_enabled=False).
        
        Args:
            document_id: ID of the document to delete
            
        Returns:
            Updated AXEKnowledgeDocumentORM instance or None if not found
        """
        document = await self.get_by_id(document_id)
        if not document:
            return None
            
        document.is_enabled = False
        
        await self.db.commit()
        await self.db.refresh(document)
        
        logger.info(f"[AXEKnowledge] Soft-deleted document: {document.id}")
        return document

    async def increment_access(self, document_id: str) -> bool:
        """Increment the access count for a document.
        
        Args:
            document_id: ID of the document
            
        Returns:
            True if successfully incremented, False if document not found
        """
        document = await self.get_by_id(document_id)
        if not document:
            return False
            
        document.access_count += 1
        
        await self.db.commit()
        await self.db.refresh(document)
        
        logger.debug(f"[AXEKnowledge] Incremented access: {document.id} (count: {document.access_count})")
        return True

    async def get_categories_stats(self) -> List[CategoryStats]:
        """Get document count per category.
        
        Returns:
            List of CategoryStats with category name and document count
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
        
        return [
            CategoryStats(category=row.category, count=row.count)
            for row in rows
        ]
