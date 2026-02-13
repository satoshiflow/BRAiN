"""
Governor Decision Models (Phase 2).

Models for deterministic governance decisions based on manifest rules.

Key Concepts:
- GovernorDecision: Complete decision with trace, mode, budget, recovery strategy
- BudgetResolution: Resolved budget from manifest rules
- DecisionContext: Job context for decision evaluation
- RecoveryStrategy: RETRY / ROLLBACK_REQUIRED / MANUAL_CONFIRM
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid

from app.modules.governor.manifest.schemas import Budget


# ============================================================================
# Decision Context
# ============================================================================

class DecisionContext(BaseModel):
    """
    Job context for governance decision.

    Contains all information needed for deterministic decision evaluation.
    """
    # Job identification
    job_type: str = Field(
        ...,
        description="Job type (e.g., 'llm_call', 'tool_execution')"
    )

    mission_id: Optional[str] = Field(
        None,
        description="Mission ID for tracking"
    )

    job_id: Optional[str] = Field(
        None,
        description="Job ID for tracking"
    )

    # Job characteristics (for rule matching)
    environment: Optional[str] = Field(
        None,
        description="Execution environment (dev/staging/production)"
    )

    risk_class: Optional[str] = Field(
        None,
        description="Risk classification (INTERNAL/EXTERNAL/NON_IDEMPOTENT)"
    )

    idempotent: Optional[bool] = Field(
        None,
        description="Whether job is idempotent"
    )

    external_dependency: Optional[bool] = Field(
        None,
        description="Whether job depends on external services"
    )

    uses_personal_data: Optional[bool] = Field(
        None,
        description="Whether job processes personal data (DSGVO)"
    )

    # Execution estimates (if available)
    estimated_duration_ms: Optional[float] = Field(
        None,
        description="Estimated execution duration in milliseconds"
    )

    estimated_cost: Optional[float] = Field(
        None,
        description="Estimated cost in credits"
    )

    estimated_tokens: Optional[int] = Field(
        None,
        description="Estimated LLM tokens"
    )

    # Custom context fields
    extra_context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional custom context fields"
    )


# ============================================================================
# Budget Resolution
# ============================================================================

class BudgetResolution(BaseModel):
    """
    Resolved budget from manifest rules.

    Tracks how budget was determined (defaults, rule override, job override).
    """
    budget: Budget = Field(
        ...,
        description="Resolved budget"
    )

    source: Literal["defaults", "rule_override", "job_override"] = Field(
        ...,
        description="How budget was resolved"
    )

    rule_id: Optional[str] = Field(
        None,
        description="Rule ID if budget came from rule override"
    )

    multiplier_applied: Optional[float] = Field(
        None,
        description="Budget multiplier from risk class (if applied)"
    )

    details: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional resolution details"
    )


# ============================================================================
# Recovery Strategy
# ============================================================================

class RecoveryStrategy(str, Enum):
    """
    Recovery strategy for failed executions.

    - RETRY: Automatic retry with exponential backoff
    - ROLLBACK_REQUIRED: Requires rollback before retry
    - MANUAL_CONFIRM: Requires manual operator confirmation
    """
    RETRY = "RETRY"
    ROLLBACK_REQUIRED = "ROLLBACK_REQUIRED"
    MANUAL_CONFIRM = "MANUAL_CONFIRM"


# ============================================================================
# Governor Decision
# ============================================================================

class GovernorDecision(BaseModel):
    """
    Complete governance decision from manifest evaluation.

    Immutable record of:
    - What mode was chosen (DIRECT/RAIL)
    - What budget was resolved
    - What recovery strategy applies
    - Which rules were triggered
    - Which manifest version was used
    """

    # Decision identification
    decision_id: str = Field(
        default_factory=lambda: f"dec_{uuid.uuid4().hex[:16]}",
        description="Unique decision identifier"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Decision timestamp"
    )

    # Trace context
    mission_id: Optional[str] = Field(
        None,
        description="Mission ID for tracking"
    )

    plan_id: Optional[str] = Field(
        None,
        description="Plan ID for tracking"
    )

    job_id: Optional[str] = Field(
        None,
        description="Job ID for tracking"
    )

    job_type: str = Field(
        ...,
        description="Job type"
    )

    # Decision output
    mode: Literal["DIRECT", "RAIL"] = Field(
        ...,
        description="Execution mode (DIRECT = skip rail, RAIL = enforce budgets)"
    )

    budget_resolution: BudgetResolution = Field(
        ...,
        description="Resolved budget with source tracking"
    )

    recovery_strategy: RecoveryStrategy = Field(
        default=RecoveryStrategy.RETRY,
        description="Recovery strategy for failures"
    )

    # Manifest context
    manifest_id: str = Field(
        ...,
        description="Manifest ID used for decision"
    )

    manifest_version: str = Field(
        ...,
        description="Manifest version used for decision"
    )

    triggered_rules: List[str] = Field(
        default_factory=list,
        description="Rule IDs that were triggered"
    )

    # Decision metadata
    reason: str = Field(
        ...,
        description="Human-readable reason for decision"
    )

    shadow_mode: bool = Field(
        default=False,
        description="Whether decision was made in shadow mode"
    )

    evidence: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Evidence/context used for decision"
    )

    # Immune system integration
    immune_alert_required: bool = Field(
        default=False,
        description="Whether immune system should be alerted"
    )

    health_impact: Optional[str] = Field(
        None,
        description="Expected health impact (for health monitoring)"
    )


# ============================================================================
# Decision Statistics
# ============================================================================

class DecisionStatistics(BaseModel):
    """Aggregate statistics for governance decisions."""

    total_decisions: int = Field(
        default=0,
        description="Total decisions made"
    )

    decisions_by_mode: Dict[str, int] = Field(
        default_factory=dict,
        description="Count by mode (DIRECT vs RAIL)"
    )

    decisions_by_manifest: Dict[str, int] = Field(
        default_factory=dict,
        description="Count by manifest version"
    )

    decisions_by_recovery: Dict[str, int] = Field(
        default_factory=dict,
        description="Count by recovery strategy"
    )

    rule_trigger_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of how often each rule was triggered"
    )

    average_decision_time_ms: float = Field(
        default=0.0,
        description="Average decision evaluation time"
    )

    immune_alerts_triggered: int = Field(
        default=0,
        description="Number of decisions that triggered immune alerts"
    )


# ============================================================================
# Decision Query
# ============================================================================

class DecisionQuery(BaseModel):
    """Query parameters for decision lookup."""

    mission_id: Optional[str] = None
    job_id: Optional[str] = None
    job_type: Optional[str] = None
    mode: Optional[Literal["DIRECT", "RAIL"]] = None
    manifest_version: Optional[str] = None
    recovery_strategy: Optional[RecoveryStrategy] = None
    shadow_mode: Optional[bool] = None

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of results"
    )

    offset: int = Field(
        default=0,
        ge=0,
        description="Result offset for pagination"
    )
