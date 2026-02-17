"""
NeuroRail Identity Schemas.

Defines the hierarchical trace chain entities:
mission_id → plan_id → job_id → attempt_id → resource_uuid

All IDs use prefixed UUIDs for easy identification in logs and traces.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4
from pydantic import BaseModel, Field


# ============================================================================
# Trace Chain Entities
# ============================================================================

class MissionIdentity(BaseModel):
    """
    Top-level entity representing a mission.

    A mission is a high-level goal that gets decomposed into plans.
    """
    mission_id: str = Field(
        default_factory=lambda: f"m_{uuid4().hex[:12]}",
        description="Unique mission identifier (m_xxxxx)"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    parent_mission_id: Optional[str] = Field(
        default=None,
        description="Parent mission if this is a sub-mission"
    )
    tags: Dict[str, str] = Field(
        default_factory=dict,
        description="User-defined tags for filtering and organization"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "mission_id": "m_a1b2c3d4e5f6",
                "created_at": "2025-12-30T14:00:00Z",
                "parent_mission_id": None,
                "tags": {"environment": "production", "priority": "high"}
            }
        }


class PlanIdentity(BaseModel):
    """
    Execution plan for a mission.

    A plan defines how a mission will be executed (sequentially, in parallel, etc.).
    """
    plan_id: str = Field(
        default_factory=lambda: f"p_{uuid4().hex[:12]}",
        description="Unique plan identifier (p_xxxxx)"
    )
    mission_id: str = Field(..., description="Parent mission ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    plan_type: str = Field(
        default="sequential",
        description="Plan execution type: sequential, parallel, dag, conditional"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Plan-specific metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "p_f6e5d4c3b2a1",
                "mission_id": "m_a1b2c3d4e5f6",
                "created_at": "2025-12-30T14:00:01Z",
                "plan_type": "sequential",
                "metadata": {"total_jobs": 5}
            }
        }


class JobIdentity(BaseModel):
    """
    Individual job within a plan.

    A job is an atomic unit of work (e.g., LLM call, tool execution, policy check).
    """
    job_id: str = Field(
        default_factory=lambda: f"j_{uuid4().hex[:12]}",
        description="Unique job identifier (j_xxxxx)"
    )
    plan_id: str = Field(..., description="Parent plan ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    job_type: str = Field(
        ...,
        description="Job type: llm_call, tool_execution, policy_check, manual_confirm, etc."
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of job_ids that must complete before this job"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Job-specific metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "j_123456789abc",
                "plan_id": "p_f6e5d4c3b2a1",
                "created_at": "2025-12-30T14:00:02Z",
                "job_type": "llm_call",
                "dependencies": [],
                "metadata": {"model": "llama3.2", "prompt_length": 500}
            }
        }


class AttemptIdentity(BaseModel):
    """
    Single execution attempt of a job.

    A job may have multiple attempts due to retries on mechanical failures.
    """
    attempt_id: str = Field(
        default_factory=lambda: f"a_{uuid4().hex[:12]}",
        description="Unique attempt identifier (a_xxxxx)"
    )
    job_id: str = Field(..., description="Parent job ID")
    attempt_number: int = Field(..., description="Attempt number (1-indexed)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Attempt-specific metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "attempt_id": "a_abc123def456",
                "job_id": "j_123456789abc",
                "attempt_number": 1,
                "created_at": "2025-12-30T14:00:03Z",
                "metadata": {"retry_reason": None}
            }
        }


class ResourceIdentity(BaseModel):
    """
    Resource allocation tied to an attempt.

    Resources include LLM tokens, CPU time, memory, API calls, etc.
    """
    resource_uuid: str = Field(
        default_factory=lambda: f"r_{uuid4().hex[:12]}",
        description="Unique resource identifier (r_xxxxx)"
    )
    attempt_id: str = Field(..., description="Parent attempt ID")
    resource_type: str = Field(
        ...,
        description="Resource type: llm_token, cpu_time, memory_mb, api_call, etc."
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Resource-specific metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "resource_uuid": "r_def456abc123",
                "attempt_id": "a_abc123def456",
                "resource_type": "llm_token",
                "created_at": "2025-12-30T14:00:04Z",
                "metadata": {"tokens_allocated": 1000}
            }
        }


# ============================================================================
# Complete Trace Chain
# ============================================================================

class TraceChain(BaseModel):
    """
    Complete trace chain from mission to resource.

    Provides hierarchical context for any entity in the system.
    """
    mission: Optional[MissionIdentity] = None
    plan: Optional[PlanIdentity] = None
    job: Optional[JobIdentity] = None
    attempt: Optional[AttemptIdentity] = None
    resource: Optional[ResourceIdentity] = None

    def get_mission_id(self) -> Optional[str]:
        """Get mission_id from any level of the chain."""
        return self.mission.mission_id if self.mission else None

    def get_plan_id(self) -> Optional[str]:
        """Get plan_id from any level of the chain."""
        return self.plan.plan_id if self.plan else None

    def get_job_id(self) -> Optional[str]:
        """Get job_id from any level of the chain."""
        return self.job.job_id if self.job else None

    def get_attempt_id(self) -> Optional[str]:
        """Get attempt_id from any level of the chain."""
        return self.attempt.attempt_id if self.attempt else None

    def get_resource_uuid(self) -> Optional[str]:
        """Get resource_uuid if present."""
        return self.resource.resource_uuid if self.resource else None

    class Config:
        json_schema_extra = {
            "example": {
                "mission": {
                    "mission_id": "m_a1b2c3d4e5f6",
                    "created_at": "2025-12-30T14:00:00Z",
                    "tags": {"priority": "high"}
                },
                "plan": {
                    "plan_id": "p_f6e5d4c3b2a1",
                    "mission_id": "m_a1b2c3d4e5f6",
                    "plan_type": "sequential"
                },
                "job": {
                    "job_id": "j_123456789abc",
                    "plan_id": "p_f6e5d4c3b2a1",
                    "job_type": "llm_call"
                },
                "attempt": {
                    "attempt_id": "a_abc123def456",
                    "job_id": "j_123456789abc",
                    "attempt_number": 1
                }
            }
        }


# ============================================================================
# Identity Lookup Responses
# ============================================================================

class EntityLookupResponse(BaseModel):
    """Response for entity lookup by ID."""
    found: bool
    entity_type: str  # mission, plan, job, attempt, resource
    entity_id: str
    data: Optional[Dict[str, Any]] = None
    trace_chain: Optional[TraceChain] = None


class TraceChainResponse(BaseModel):
    """Response for trace chain lookup."""
    entity_type: str
    entity_id: str
    trace_chain: TraceChain
    created_at: datetime


# ============================================================================
# Identity Creation Requests
# ============================================================================

class CreateMissionRequest(BaseModel):
    """Request to create a new mission identity."""
    parent_mission_id: Optional[str] = None
    tags: Dict[str, str] = Field(default_factory=dict)


class CreatePlanRequest(BaseModel):
    """Request to create a new plan identity."""
    mission_id: str
    plan_type: str = "sequential"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CreateJobRequest(BaseModel):
    """Request to create a new job identity."""
    plan_id: str
    job_type: str
    dependencies: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CreateAttemptRequest(BaseModel):
    """Request to create a new attempt identity."""
    job_id: str
    attempt_number: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CreateResourceRequest(BaseModel):
    """Request to create a new resource identity."""
    attempt_id: str
    resource_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
