"""Schemas for AXE worker run endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


AXEWorkerStatus = Literal["queued", "running", "waiting_input", "completed", "failed"]
OpenCodeMode = Literal["plan", "build", "heal", "evolve"]
WorkerType = Literal["auto", "opencode", "miniworker"]
MiniworkerExecutionMode = Literal["proposal", "bounded_apply"]
MiniworkerExpectedOutput = Literal["patch", "analysis", "tests", "mixed"]


class AXEWorkerArtifact(BaseModel):
    type: str = Field(..., min_length=1, max_length=64)
    label: str = Field(..., min_length=1, max_length=160)
    url: str = Field(..., min_length=1, max_length=512)
    content: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class AXEWorkerRunCreateRequest(BaseModel):
    session_id: UUID
    message_id: UUID
    prompt: str = Field(..., min_length=1, max_length=20000)
    mode: OpenCodeMode = "plan"
    worker_type: WorkerType = "auto"
    execution_mode: MiniworkerExecutionMode = "proposal"
    expected_output: MiniworkerExpectedOutput = "patch"
    module: str | None = Field(default=None, min_length=1, max_length=128)
    entity_id: str | None = Field(default=None, min_length=1, max_length=256)
    file_scope: list[str] = Field(default_factory=list, max_length=20)
    max_files: int = Field(default=3, ge=1, le=20)


class AXEWorkerRunResponse(BaseModel):
    worker_run_id: str
    session_id: UUID
    message_id: UUID
    worker_type: WorkerType
    status: AXEWorkerStatus
    label: str
    detail: str
    updated_at: datetime
    artifacts: list[AXEWorkerArtifact] = Field(default_factory=list)


class AXEWorkerRunListResponse(BaseModel):
    items: list[AXEWorkerRunResponse] = Field(default_factory=list)
