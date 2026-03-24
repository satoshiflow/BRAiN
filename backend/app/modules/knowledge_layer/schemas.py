from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeItemCreate(BaseModel):
    type: str = Field(..., min_length=1, max_length=40)
    title: str = Field(..., min_length=1, max_length=255)
    source: str = Field(..., min_length=1, max_length=120)
    version: int = Field(default=1, ge=1)
    module: str = Field(..., min_length=1, max_length=120)
    tags: list[str] = Field(default_factory=list)
    content: str = Field(..., min_length=1)
    provenance_refs: list[dict[str, Any]] = Field(default_factory=list)
    valid_until: datetime | None = None


class KnowledgeItemResponse(BaseModel):
    id: UUID
    tenant_id: str | None
    type: str
    title: str
    source: str
    version: int
    owner: str
    module: str
    tags: list[str]
    content: str
    provenance_refs: list[dict[str, Any]]
    skill_run_id: UUID | None = None
    experience_record_id: UUID | None = None
    evaluation_result_id: UUID | None = None
    valid_until: datetime | None = None
    superseded_by_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeItemListResponse(BaseModel):
    items: list[KnowledgeItemResponse] = Field(default_factory=list)
    total: int


class KnowledgeSearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    type: str | None = None
    module: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class RunLessonIngestResponse(BaseModel):
    skill_run_id: UUID
    knowledge_item: KnowledgeItemResponse
