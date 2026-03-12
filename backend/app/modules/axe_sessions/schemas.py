"""Schemas for AXE chat session API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


SessionStatus = Literal["active", "deleted"]
MessageRole = Literal["user", "assistant"]


class AXEChatSessionCreateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)


class AXEChatSessionUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class AXEChatMessageCreateRequest(BaseModel):
    role: MessageRole
    content: str = Field(..., min_length=1, max_length=20000)
    attachments: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AXEChatMessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: MessageRole
    content: str
    attachments: list[str]
    metadata: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AXEChatSessionSummaryResponse(BaseModel):
    id: UUID
    title: str
    preview: str | None = None
    status: SessionStatus
    message_count: int = 0
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AXEChatSessionDetailResponse(AXEChatSessionSummaryResponse):
    messages: list[AXEChatMessageResponse] = Field(default_factory=list)
