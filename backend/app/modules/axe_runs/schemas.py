from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AXERunCreate(BaseModel):
    skill_key: str
    session_id: UUID | None = None
    input_payload: dict[str, Any] = {}
    stream_tokens: bool = True


class AXERunResponse(BaseModel):
    id: UUID
    skill_key: str
    state: str
    skill_run_id: UUID | None = None
    session_id: UUID | None = None
    output: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class AXERunListResponse(BaseModel):
    items: list[AXERunResponse]
    total: int
