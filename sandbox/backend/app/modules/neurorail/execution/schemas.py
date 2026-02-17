"""
NeuroRail Execution Schemas.

Defines execution context and result models.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from pydantic import BaseModel, Field


# ============================================================================
# Execution Context
# ============================================================================

class ExecutionContext(BaseModel):
    """
    Context for executing a job with NeuroRail observation.

    Phase 1: Observation only (no enforcement)
    Phase 2: Budget enforcement enabled
    """
    # Trace Chain IDs
    mission_id: str
    plan_id: str
    job_id: str
    attempt_id: str

    # Job Details
    job_type: str = Field(..., description="Job type: llm_call, tool_execution, policy_check, etc.")
    job_parameters: Dict[str, Any] = Field(default_factory=dict)

    # Observation Hooks (Phase 1)
    trace_enabled: bool = True
    telemetry_enabled: bool = True
    audit_enabled: bool = True

    # Budget (Phase 2 - currently not enforced)
    max_attempts: int = Field(default=3, description="Maximum retry attempts")
    timeout_ms: Optional[int] = Field(None, description="Timeout in milliseconds (not enforced in Phase 1)")
    max_llm_tokens: Optional[int] = Field(None, description="Max LLM tokens (not enforced in Phase 1)")

    # Parent Context (for orphan protection)
    parent_context: Optional[str] = Field(None, description="Parent job_id or mission_id")
    grace_period_ms: int = Field(default=60000, description="Grace period before orphan kill (60s default)")

    class Config:
        json_schema_extra = {
            "example": {
                "mission_id": "m_a1b2c3d4e5f6",
                "plan_id": "p_f6e5d4c3b2a1",
                "job_id": "j_123456789abc",
                "attempt_id": "a_abc123def456",
                "job_type": "llm_call",
                "job_parameters": {"model": "llama3.2", "prompt": "Test"},
                "trace_enabled": True,
                "telemetry_enabled": True,
                "audit_enabled": True,
                "max_attempts": 3,
                "timeout_ms": 30000,
                "max_llm_tokens": 1000
            }
        }


# ============================================================================
# Execution Result
# ============================================================================

class ExecutionResult(BaseModel):
    """
    Result of a job execution.
    """
    attempt_id: str
    status: str = Field(..., description="Attempt status: succeeded, failed_timeout, failed_resource, failed_error")

    # Outputs
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result (if successful)")
    error: Optional[str] = Field(None, description="Error message (if failed)")
    error_category: Optional[str] = Field(None, description="Error category: mechanical, ethical, system")
    error_code: Optional[str] = Field(None, description="Error code (e.g., NR-E001)")

    # Metrics
    duration_ms: float = Field(..., description="Execution duration in milliseconds")
    llm_tokens_used: int = Field(default=0, description="LLM tokens consumed")
    cpu_time_ms: float = Field(default=0.0, description="CPU time in milliseconds")
    memory_peak_mb: float = Field(default=0.0, description="Peak memory usage in MB")

    # Trace
    audit_events: list[str] = Field(default_factory=list, description="List of audit_ids generated")
    state_transitions: list[str] = Field(default_factory=list, description="List of state transition event_ids")

    class Config:
        json_schema_extra = {
            "example": {
                "attempt_id": "a_abc123def456",
                "status": "succeeded",
                "result": {"response": "LLM response text"},
                "error": None,
                "error_category": None,
                "error_code": None,
                "duration_ms": 1234.5,
                "llm_tokens_used": 500,
                "cpu_time_ms": 100.0,
                "memory_peak_mb": 50.0,
                "audit_events": ["aud_abc123", "aud_def456"],
                "state_transitions": ["evt_20251230140000", "evt_20251230140005"]
            }
        }


# ============================================================================
# Execution Request
# ============================================================================

class ExecutionRequest(BaseModel):
    """
    Request to execute a job with NeuroRail observation.
    """
    context: ExecutionContext
    executor: Optional[Any] = Field(None, description="Executor function (not serializable, set programmatically)")

    class Config:
        arbitrary_types_allowed = True
