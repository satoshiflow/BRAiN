"""
AXE Knowledge Document Models
SQLAlchemy ORM models for the knowledge base system.
"""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class AXEKnowledgeDocumentORM(Base):
    """
    AXE Knowledge Document ORM Model
    
    Stores knowledge documents for the AXE system with support for
    versioning, categorization, and metadata.
    """
    
    __tablename__ = "axe_knowledge_documents"
    
    # Primary Key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        index=True,
        default=lambda: str(uuid4())
    )

    __table_args__ = (
        Index("idx_axe_knowledge_category_enabled", "category", "is_enabled"),
        Index("idx_axe_knowledge_importance", "importance_score"),
        Index("idx_axe_knowledge_created_at", "created_at"),
    )
    
    # Basic Information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    # Categorization
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        default="custom"
    )
    
    # Content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    content_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="text"
    )
    
    # Metadata and Tags
    doc_metadata: Mapped[Optional[dict]] = mapped_column(
        "metadata",
        JSON,
        nullable=True,
        default=dict
    )
    tags: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True,
        default=list
    )
    
    # Status and Metrics
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True
    )
    access_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    importance_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0
    )
    
    # Versioning
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("axe_knowledge_documents.id"),
        nullable=True,
        index=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Creator Reference (simple string, no User relationship)
    created_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    
    # Relationships (self-referential only)
    parent: Mapped[Optional["AXEKnowledgeDocumentORM"]] = relationship(
        "AXEKnowledgeDocumentORM",
        remote_side=[id],
        back_populates="versions"
    )
    versions: Mapped[List["AXEKnowledgeDocumentORM"]] = relationship(
        "AXEKnowledgeDocumentORM",
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<AXEKnowledgeDocumentORM(id={self.id}, name={self.name}, category={self.category}, version={self.version})>"
    
    def increment_access(self) -> None:
        """Increment the access count for this document."""
        self.access_count += 1
    
    def create_new_version(self, new_content: str, modified_by: Optional[str] = None) -> "AXEKnowledgeDocumentORM":
        """
        Create a new version of this document.
        
        Args:
            new_content: The updated content
            modified_by: ID of the user creating the new version
            
        Returns:
            A new AXEKnowledgeDocumentORM instance representing the new version
        """
        return AXEKnowledgeDocumentORM(
            id=str(uuid4()),
            name=self.name,
            description=self.description,
            category=self.category,
            content=new_content,
            content_type=self.content_type,
            doc_metadata=self.doc_metadata.copy() if self.doc_metadata else {},
            tags=self.tags.copy() if self.tags else [],
            is_enabled=self.is_enabled,
            access_count=0,
            importance_score=self.importance_score,
            version=self.version + 1,
            parent_id=self.id,
            created_by=modified_by or self.created_by
        )
