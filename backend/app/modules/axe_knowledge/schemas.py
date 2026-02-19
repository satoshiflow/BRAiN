"""
AXE Knowledge Document Schemas
Pydantic models for validation and serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentCategory(str, Enum):
    """Categories for knowledge documents."""
    SYSTEM = "system"
    DOMAIN = "domain"
    PROCEDURE = "procedure"
    FAQ = "faq"
    REFERENCE = "reference"
    CUSTOM = "custom"


# =============================================================================
# Base Schemas
# =============================================================================

class KnowledgeDocumentBase(BaseModel):
    """Base schema with common fields for knowledge documents."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name/title of the document"
    )
    description: Optional[str] = Field(
        None,
        max_length=5000,
        description="Optional description or summary"
    )
    category: DocumentCategory = Field(
        default=DocumentCategory.CUSTOM,
        description="Document category"
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Main content of the document"
    )
    content_type: str = Field(
        default="text",
        max_length=50,
        description="Content format (text, markdown, html, etc.)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Flexible metadata storage"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="List of tags for categorization"
    )
    is_enabled: bool = Field(
        default=True,
        description="Whether the document is active"
    )
    importance_score: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Importance score from 0.0 to 10.0"
    )


# =============================================================================
# Create Schemas
# =============================================================================

class KnowledgeDocumentCreate(KnowledgeDocumentBase):
    """Schema for creating a new knowledge document."""
    
    parent_id: Optional[str] = Field(
        None,
        max_length=36,
        description="ID of parent document if this is a new version"
    )
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate and clean tags."""
        if v is None:
            return None
        # Remove duplicates and empty strings, lowercase
        cleaned = list(set(tag.lower().strip() for tag in v if tag.strip()))
        return cleaned


# =============================================================================
# Update Schemas
# =============================================================================

class KnowledgeDocumentUpdate(BaseModel):
    """Schema for updating an existing knowledge document."""
    
    model_config = ConfigDict(extra='forbid')
    
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255
    )
    description: Optional[str] = Field(
        None,
        max_length=5000
    )
    category: Optional[DocumentCategory] = None
    content: Optional[str] = Field(
        None,
        min_length=1
    )
    content_type: Optional[str] = Field(
        None,
        max_length=50
    )
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_enabled: Optional[bool] = None
    importance_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0
    )
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate and clean tags."""
        if v is None:
            return None
        cleaned = list(set(tag.lower().strip() for tag in v if tag.strip()))
        return cleaned


# =============================================================================
# Response Schemas
# =============================================================================

class KnowledgeDocumentVersionInfo(BaseModel):
    """Lightweight version information for related documents."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    version: int
    created_at: datetime


class KnowledgeDocumentResponse(KnowledgeDocumentBase):
    """Full document response schema."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    access_count: int
    version: int
    parent_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    
    # Optional related data
    parent: Optional[KnowledgeDocumentVersionInfo] = None
    versions: List[KnowledgeDocumentVersionInfo] = []


class KnowledgeDocumentListResponse(BaseModel):
    """Response schema for listing documents (excludes full content)."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    description: Optional[str] = None
    category: DocumentCategory
    content_type: str
    tags: Optional[List[str]] = None
    is_enabled: bool
    access_count: int
    importance_score: float
    version: int
    parent_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None


# =============================================================================
# Search Schemas
# =============================================================================

class DocumentSearchRequest(BaseModel):
    """Schema for searching/filtering knowledge documents."""
    
    query: Optional[str] = Field(
        None,
        description="Free-text search query"
    )
    category: Optional[DocumentCategory] = Field(
        None,
        description="Filter by category"
    )
    tags: Optional[List[str]] = Field(
        None,
        description="Filter by tags (all must match)"
    )
    is_enabled: Optional[bool] = Field(
        None,
        description="Filter by enabled status"
    )
    created_by: Optional[str] = Field(
        None,
        description="Filter by creator user ID"
    )
    min_importance: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum importance score"
    )
    max_importance: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Maximum importance score"
    )
    
    # Pagination
    skip: int = Field(
        default=0,
        ge=0,
        description="Number of records to skip"
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of records to return"
    )
    
    # Sorting
    sort_by: str = Field(
        default="created_at",
        pattern="^(created_at|updated_at|name|category|importance_score|access_count)$"
    )
    sort_order: str = Field(
        default="desc",
        pattern="^(asc|desc)$"
    )


class DocumentSearchResponse(BaseModel):
    """Response schema for document search results."""
    
    total: int = Field(..., description="Total number of matching documents")
    skip: int = Field(..., description="Number of records skipped")
    limit: int = Field(..., description="Records per page limit")
    documents: List[KnowledgeDocumentListResponse] = Field(
        ...,
        description="List of matching documents"
    )
