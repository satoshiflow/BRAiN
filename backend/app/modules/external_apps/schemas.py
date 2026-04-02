from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.modules.skill_engine.schemas import SkillRunResponse
from app.modules.task_queue.schemas import TaskResponse


PaperclipTargetType = Literal["company", "project", "issue", "agent", "execution"]
PaperclipPermission = Literal["view", "request_escalation", "request_approval", "request_retry"]
PaperclipAction = Literal["request_escalation", "request_approval", "request_retry"]


class PaperclipHandoffRequest(BaseModel):
    target_type: PaperclipTargetType
    target_ref: str = Field(min_length=1, max_length=255)
    skill_run_id: str | None = Field(default=None, min_length=1, max_length=64)
    mission_id: str | None = Field(default=None, min_length=1, max_length=120)
    decision_id: str | None = Field(default=None, min_length=1, max_length=160)
    correlation_id: str | None = Field(default=None, min_length=1, max_length=160)
    permissions: list[PaperclipPermission] = Field(default_factory=lambda: ["view"])

    @field_validator("permissions")
    @classmethod
    def _ensure_permissions(cls, value: list[PaperclipPermission]) -> list[PaperclipPermission]:
        if not value:
            raise ValueError("permissions must not be empty")
        return list(dict.fromkeys(value))


class PaperclipHandoffResponse(BaseModel):
    handoff_url: str
    expires_at: str
    jti: str
    target_type: PaperclipTargetType
    target_ref: str


class PaperclipHandoffExchangeRequest(BaseModel):
    token: str = Field(min_length=16)


class PaperclipHandoffExchangeResponse(BaseModel):
    jti: str
    principal_id: str
    tenant_id: str | None = None
    skill_run_id: str | None = None
    mission_id: str | None = None
    decision_id: str | None = None
    correlation_id: str | None = None
    target_type: PaperclipTargetType
    target_ref: str
    permissions: list[PaperclipPermission]
    suggested_path: str
    governance_banner: str
    expires_at: str


class PaperclipExecutionContextResponse(BaseModel):
    target_type: Literal["execution"] = "execution"
    target_ref: str
    task: TaskResponse
    skill_run: SkillRunResponse | None = None
    governance_banner: str
    available_actions: list[PaperclipAction] = Field(default_factory=list)


class PaperclipActionRequest(BaseModel):
    token: str = Field(min_length=16)
    action: PaperclipAction
    reason: str = Field(min_length=3, max_length=1000)


class PaperclipActionRequestResponse(BaseModel):
    request_id: str
    action: PaperclipAction
    status: Literal["requested"] = "requested"
    target_ref: str
    skill_run_id: str | None = None
    message: str


PaperclipActionRequestStatus = Literal["pending", "approved", "rejected"]


class PaperclipActionRequestItem(BaseModel):
    request_id: str
    tenant_id: str | None = None
    principal_id: str
    action: PaperclipAction
    reason: str
    status: PaperclipActionRequestStatus
    target_type: Literal["execution"] = "execution"
    target_ref: str
    skill_run_id: str | None = None
    mission_id: str | None = None
    decision_id: str | None = None
    correlation_id: str | None = None
    created_at: str
    updated_at: str
    approved_by: str | None = None
    approved_at: str | None = None
    rejected_by: str | None = None
    rejected_at: str | None = None
    decision_reason: str | None = None
    execution_result: dict[str, str] = Field(default_factory=dict)


class PaperclipActionRequestListResponse(BaseModel):
    items: list[PaperclipActionRequestItem] = Field(default_factory=list)
    total: int


class PaperclipActionRequestDecision(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)
