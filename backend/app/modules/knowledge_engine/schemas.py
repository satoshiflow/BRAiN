from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    type: str = Field(default="note", min_length=1, max_length=40)
    tags: list[str] = Field(default_factory=list)
    visibility: str = Field(default="tenant", min_length=1, max_length=24)
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1)
    type: str | None = Field(default=None, min_length=1, max_length=40)
    tags: list[str] | None = None
    visibility: str | None = Field(default=None, min_length=1, max_length=24)
    metadata: dict[str, Any] | None = None


class KnowledgeItemResponse(BaseModel):
    id: UUID
    tenant_id: str | None
    title: str
    content: str
    type: str
    tags: list[str]
    visibility: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class KnowledgeListResponse(BaseModel):
    items: list[KnowledgeItemResponse] = Field(default_factory=list)
    total: int


class KnowledgeLinkCreate(BaseModel):
    source_id: UUID
    target_id: UUID
    relation_type: str = Field(..., min_length=1, max_length=60)


class KnowledgeLinkResponse(BaseModel):
    id: UUID
    source_id: UUID
    target_id: UUID
    relation_type: str
    created_at: datetime


class KnowledgeVersionCreate(BaseModel):
    diff: dict[str, Any] = Field(default_factory=dict)


class KnowledgeVersionResponse(BaseModel):
    id: UUID
    item_id: UUID
    version: int
    diff: dict[str, Any]
    created_at: datetime


class KnowledgeScoreResponse(BaseModel):
    item_id: UUID
    usage_count: int
    relevance_score: float
    last_used: datetime | None


class KnowledgeSearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    type: str | None = None
    tag: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=20, ge=1, le=100)


class KnowledgeIngestRequest(BaseModel):
    raw_text: str | None = None
    url: str | None = None
    code: str | None = None
    document_text: str | None = None
    title: str | None = None
    type: str = "doc"
    tags: list[str] = Field(default_factory=list)
    visibility: str = "tenant"
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeIngestResponse(BaseModel):
    item: KnowledgeItemResponse
    chunk_count: int


class RelatedKnowledgeResponse(BaseModel):
    item_id: UUID
    related: list[KnowledgeItemResponse] = Field(default_factory=list)


class CapabilityStoreRequest(BaseModel):
    item: KnowledgeItemCreate


class CapabilitySearchRequest(BaseModel):
    query: str
    type: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class CapabilityLinkRequest(BaseModel):
    source_id: UUID
    target_id: UUID
    relation_type: str


class HelpDocListResponse(BaseModel):
    items: list[KnowledgeItemResponse] = Field(default_factory=list)
    total: int


class HelpDocQuery(BaseModel):
    surface: str | None = None
    limit: int = Field(default=50, ge=1, le=200)
