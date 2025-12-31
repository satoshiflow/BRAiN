"""
NeuroRail Telemetry Schemas.

Defines metrics models for execution monitoring.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Execution Metrics
# ============================================================================

class ExecutionMetrics(BaseModel):
    """
    Metrics for a single execution (attempt).
    """
    entity_id: str = Field(..., description="Entity ID (attempt_id, job_id, or mission_id)")
    entity_type: str = Field(..., description="Entity type: attempt, job, mission")

    # Timing
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None

    # Resource Usage
    llm_tokens_consumed: int = 0
    cpu_time_ms: float = 0.0
    memory_peak_mb: float = 0.0

    # Attempts & Retries
    attempt_count: int = 0
    retry_count: int = 0

    # Outcome
    success: Optional[bool] = None
    error_type: Optional[str] = None
    error_category: Optional[str] = None  # "mechanical" or "ethical"

    class Config:
        json_schema_extra = {
            "example": {
                "entity_id": "a_abc123def456",
                "entity_type": "attempt",
                "started_at": "2025-12-30T14:00:00Z",
                "completed_at": "2025-12-30T14:00:05Z",
                "duration_ms": 5234.5,
                "llm_tokens_consumed": 500,
                "cpu_time_ms": 100.0,
                "memory_peak_mb": 50.0,
                "attempt_count": 1,
                "retry_count": 0,
                "success": True,
                "error_type": None,
                "error_category": None
            }
        }


# ============================================================================
# Aggregated Metrics
# ============================================================================

class AggregatedMetrics(BaseModel):
    """
    Aggregated metrics over a time window.
    """
    time_window: str = Field(..., description="Time window: 1h, 24h, 7d")

    # Mission Metrics
    total_missions: int = 0
    successful_missions: int = 0
    failed_missions: int = 0

    # Job Metrics
    total_jobs: int = 0
    successful_jobs: int = 0
    failed_mechanical_jobs: int = 0
    failed_ethical_jobs: int = 0
    timeout_jobs: int = 0

    # Attempt Metrics
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0

    # Duration Statistics (milliseconds)
    avg_mission_duration_ms: float = 0.0
    p50_mission_duration_ms: float = 0.0
    p95_mission_duration_ms: float = 0.0
    p99_mission_duration_ms: float = 0.0

    avg_job_duration_ms: float = 0.0
    p95_job_duration_ms: float = 0.0

    avg_attempt_duration_ms: float = 0.0
    p95_attempt_duration_ms: float = 0.0

    # Resource Consumption
    total_llm_tokens: int = 0
    total_cpu_time_ms: float = 0.0

    # Failure Analysis
    mechanical_failures: int = 0
    ethical_failures: int = 0
    timeout_failures: int = 0

    # Rates
    success_rate: float = 0.0  # 0.0 to 1.0
    mechanical_failure_rate: float = 0.0
    ethical_failure_rate: float = 0.0


# ============================================================================
# Real-Time Snapshot
# ============================================================================

class RealtimeSnapshot(BaseModel):
    """
    Real-time snapshot of current system state.
    """
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Active Entities
    active_missions: int = 0
    active_jobs: int = 0
    active_attempts: int = 0

    # Queue Depths
    pending_missions: int = 0
    pending_jobs: int = 0

    # Resources in Use
    resources_by_type: Dict[str, int] = Field(default_factory=dict)
    # e.g., {"llm_token": 5000, "cpu_time": 1000}

    # System Health
    error_rate_1h: float = 0.0  # Errors per hour
    avg_latency_1h_ms: float = 0.0
    p95_latency_1h_ms: float = 0.0


# ============================================================================
# Metric Event (for real-time streaming)
# ============================================================================

class MetricEvent(BaseModel):
    """
    Metric event for real-time streaming to ControlDeck.
    """
    event_id: str
    timestamp: datetime
    metric_type: str  # "execution_complete", "resource_allocated", "state_change"
    entity_id: str
    entity_type: str
    data: Dict[str, Any]
