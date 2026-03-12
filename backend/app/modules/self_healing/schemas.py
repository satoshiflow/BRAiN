"""Schemas for Self-Healing module (Sprint E MVP foundation)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from app.modules.immune_orchestrator.schemas import ImmuneDecision, IncidentSignal
from app.modules.recovery_policy_engine.schemas import RecoveryDecision


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================================
# Healing Actions
# ============================================================================


class HealingAction(BaseModel):
    """Base class for all healing actions."""

    action_id: str
    action_type: str
    target_entity: str
    correlation_id: str
    blast_radius: int = Field(ge=1, le=1000)
    estimated_duration_seconds: int = Field(ge=1, le=600, default=60)
    requires_governance: bool = False
    rollback_strategy: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class RestartServiceAction(HealingAction):
    """Restart a failed service container."""

    action_type: Literal["restart_service"] = "restart_service"
    service_name: str
    container_id: Optional[str] = None
    graceful_shutdown: bool = True


class ClearCacheAction(HealingAction):
    """Clear Redis cache for entity."""

    action_type: Literal["clear_cache"] = "clear_cache"
    cache_key_pattern: str
    redis_instance: str = "default"


class ResetCircuitBreakerAction(HealingAction):
    """Reset circuit breaker state."""

    action_type: Literal["reset_circuit_breaker"] = "reset_circuit_breaker"
    circuit_name: str


class FlushQueueAction(HealingAction):
    """Clear stuck queue entries."""

    action_type: Literal["flush_queue"] = "flush_queue"
    queue_name: str
    max_items: int = Field(default=1000, ge=1, le=10000)


class NoOpAction(HealingAction):
    """Observe-only action (no intervention)."""

    action_type: Literal["noop"] = "noop"


# ============================================================================
# Execution Context
# ============================================================================


@dataclass
class ExecutionContext:
    """Context for healing action execution."""

    tenant_id: str
    actor: str
    correlation_id: str
    original_signal: IncidentSignal
    decision: ImmuneDecision
    policy: RecoveryDecision
    timestamp: datetime
    timeout_seconds: int = 60
    dry_run: bool = False


# ============================================================================
# Action Result
# ============================================================================


@dataclass
class ActionResult:
    """Result of healing action execution."""

    action_id: str
    action_type: str
    status: Literal["success", "failure", "timeout", "skipped"]
    execution_time_ms: int
    error_message: Optional[str] = None
    context: Dict[str, Any] = None
    rollback_executed: bool = False
    audit_ref: Optional[str] = None
    event_ref: Optional[str] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}


# ============================================================================
# Verification Result
# ============================================================================


@dataclass
class VerificationResult:
    """Result of healing verification."""

    verification_id: str
    action_id: str
    effectiveness_score: float  # 0.0-1.0
    checks_passed: int
    checks_failed: int
    symptom_resolved: bool
    new_incidents_detected: bool
    recommendation: Literal["success", "monitor", "escalate", "rollback"]
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


# ============================================================================
# Safety Validation
# ============================================================================


@dataclass
class ValidationResult:
    """Result of safety rail validation."""

    valid: bool
    reason: Optional[str] = None
    violated_rules: list[str] = None

    def __post_init__(self):
        if self.violated_rules is None:
            self.violated_rules = []
