"""
Governor Manifest Schemas (Phase 2).

Defines versioned, schema-validated manifests for deterministic governance.

Key Concepts:
- Immutable manifest versions with hash chain
- Rule priority system (lower number = higher priority)
- OR-logic support (when.any[], when.all[])
- Budget defaults + job-specific overrides
- Risk classes (INTERNAL, EXTERNAL, NON_IDEMPOTENT)
- Shadow mode for safe activation
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import hashlib
import json


# ============================================================================
# Budget Models
# ============================================================================

class Budget(BaseModel):
    """
    Budget limits for execution.

    All budgets are HARD limits enforced by enforcement layer.
    """
    # Time budget
    timeout_ms: Optional[int] = Field(
        None,
        description="Maximum execution time in milliseconds"
    )

    # Retry budget
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for mechanical failures"
    )

    # Parallelism budget
    max_parallel_attempts: Optional[int] = Field(
        None,
        ge=1,
        description="Maximum parallel attempts per mission"
    )
    max_global_parallel: Optional[int] = Field(
        None,
        ge=1,
        description="Maximum global parallel executions"
    )

    # Cost budget (if applicable)
    max_llm_tokens: Optional[int] = Field(
        None,
        ge=0,
        description="Maximum LLM tokens per attempt"
    )
    max_cost_credits: Optional[float] = Field(
        None,
        ge=0.0,
        description="Maximum cost in credits"
    )

    # Orphan protection
    grace_period_ms: int = Field(
        default=5000,
        ge=0,
        description="Grace period before orphan kill (ms)"
    )


# ============================================================================
# Risk Class Models
# ============================================================================

class RiskClass(BaseModel):
    """
    Risk classification for jobs.

    Determines recovery strategy and approval requirements.
    """
    name: str = Field(
        ...,
        description="Risk class name (e.g., INTERNAL, EXTERNAL, NON_IDEMPOTENT)"
    )

    description: str = Field(
        ...,
        description="Human-readable description"
    )

    recovery_strategy: Literal["RETRY", "ROLLBACK_REQUIRED", "MANUAL_CONFIRM"] = Field(
        ...,
        description="Default recovery strategy for this risk class"
    )

    require_approval: bool = Field(
        default=False,
        description="Whether this risk class requires manual approval"
    )

    budget_multiplier: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Budget multiplier for this risk class"
    )


# ============================================================================
# Rule Models
# ============================================================================

class RuleCondition(BaseModel):
    """
    Condition for rule matching.

    Supports:
    - Direct field matches: {"job_type": "llm_call"}
    - OR-logic: {"any": [{"job_type": "llm_call"}, {"uses_personal_data": True}]}
    - AND-logic: {"all": [{"environment": "production"}, {"risk_class": "EXTERNAL"}]}
    """
    # Direct field matches
    job_type: Optional[str] = None
    environment: Optional[str] = None
    risk_class: Optional[str] = None
    idempotent: Optional[bool] = None
    external_dependency: Optional[bool] = None
    uses_personal_data: Optional[bool] = None

    # Logical operators
    any: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="OR-logic: match if ANY condition matches"
    )
    all: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="AND-logic: match if ALL conditions match"
    )

    # Catch-all for custom fields
    extra_fields: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional custom condition fields"
    )


class ManifestRule(BaseModel):
    """
    Single governance rule in manifest.

    Rules are evaluated in priority order (lower = higher priority).
    First matching rule wins.
    """
    rule_id: str = Field(
        ...,
        description="Unique rule identifier"
    )

    priority: int = Field(
        ...,
        ge=0,
        le=10000,
        description="Rule priority (lower number = higher priority)"
    )

    description: str = Field(
        ...,
        description="Human-readable rule description"
    )

    # Condition
    when: RuleCondition = Field(
        ...,
        description="Condition for rule activation"
    )

    # Decision
    then: Dict[str, Any] = Field(
        ...,
        description="Decision to apply if rule matches"
    )

    # Then fields (structured)
    mode: Literal["DIRECT", "RAIL"] = Field(
        default="RAIL",
        description="Execution mode"
    )

    budget_override: Optional[Budget] = Field(
        None,
        description="Budget override for this rule"
    )

    recovery_strategy: Optional[Literal["RETRY", "ROLLBACK_REQUIRED", "MANUAL_CONFIRM"]] = Field(
        None,
        description="Recovery strategy override"
    )

    reason: str = Field(
        ...,
        description="Reason for this rule (audit trail)"
    )

    enabled: bool = Field(
        default=True,
        description="Whether this rule is active"
    )


# ============================================================================
# Manifest Model
# ============================================================================

class GovernorManifest(BaseModel):
    """
    Immutable versioned manifest for governance decisions.

    Key Properties:
    - Immutable: Once created, never modified (new version instead)
    - Hash-chained: Each version references previous hash
    - Deterministic: Same inputs → same decisions
    - Auditable: Complete version history
    """

    # Version metadata
    manifest_id: str = Field(
        ...,
        description="Unique manifest identifier (auto-generated)"
    )

    version: str = Field(
        ...,
        description="Semantic version (e.g., '1.0.0', '1.1.0')"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Manifest creation timestamp"
    )

    hash_prev: Optional[str] = Field(
        None,
        description="SHA256 hash of previous manifest (null for first version)"
    )

    hash_self: Optional[str] = Field(
        None,
        description="SHA256 hash of this manifest (computed)"
    )

    # Activation metadata
    effective_at: Optional[datetime] = Field(
        None,
        description="When this manifest becomes active (null = shadowed)"
    )

    shadow_mode: bool = Field(
        default=True,
        description="If True, manifest is in shadow evaluation mode"
    )

    shadow_start: Optional[datetime] = Field(
        None,
        description="When shadow evaluation started"
    )

    # Manifest content
    name: str = Field(
        ...,
        description="Manifest name (e.g., 'production_v1')"
    )

    description: str = Field(
        ...,
        description="Human-readable description"
    )

    rules: List[ManifestRule] = Field(
        ...,
        description="Governance rules (evaluated in priority order)"
    )

    budget_defaults: Budget = Field(
        ...,
        description="Default budgets for all jobs"
    )

    risk_classes: Dict[str, RiskClass] = Field(
        ...,
        description="Risk class definitions"
    )

    job_overrides: Optional[Dict[str, Budget]] = Field(
        default_factory=dict,
        description="Job-specific budget overrides (keyed by job_type)"
    )

    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional custom metadata"
    )

    @field_validator("rules")
    @classmethod
    def validate_rules_priority_unique(cls, rules: List[ManifestRule]) -> List[ManifestRule]:
        """Ensure rule priorities are unique."""
        priorities = [r.priority for r in rules]
        if len(priorities) != len(set(priorities)):
            raise ValueError("Rule priorities must be unique")
        return rules

    def compute_hash(self) -> str:
        """
        Compute SHA256 hash of manifest content.

        Returns:
            SHA256 hash as hex string
        """
        # Canonical JSON representation (sorted keys, no whitespace)
        content = {
            "version": self.version,
            "name": self.name,
            "rules": [r.model_dump() for r in self.rules],
            "budget_defaults": self.budget_defaults.model_dump(),
            "risk_classes": {k: v.model_dump() for k, v in self.risk_classes.items()},
        }

        canonical = json.dumps(content, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def model_post_init(self, __context: Any) -> None:
        """Compute hash after model initialization."""
        if self.hash_self is None:
            self.hash_self = self.compute_hash()


# ============================================================================
# Shadow Evaluation Models
# ============================================================================

class ShadowDecisionComparison(BaseModel):
    """Comparison of active vs shadow manifest decision."""

    mission_id: Optional[str] = None
    job_id: Optional[str] = None
    job_type: str

    active_mode: str
    shadow_mode: str

    active_budget: Budget
    shadow_budget: Budget

    mode_delta: bool = Field(
        ...,
        description="True if modes differ"
    )

    budget_delta: bool = Field(
        ...,
        description="True if budgets differ"
    )

    impact_assessment: str = Field(
        ...,
        description="Human-readable impact description"
    )

    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ShadowReport(BaseModel):
    """
    Aggregate report for shadow manifest evaluation.

    Used to determine if shadow manifest is safe to activate.
    """

    manifest_version: str
    shadow_start: datetime
    shadow_end: datetime
    evaluation_count: int

    # Divergence metrics
    mode_divergence_count: int = Field(
        ...,
        description="Number of decisions with different modes"
    )
    mode_divergence_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Rate of mode divergence (0.0-1.0)"
    )

    budget_divergence_count: int = Field(
        ...,
        description="Number of decisions with different budgets"
    )
    budget_divergence_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Rate of budget divergence (0.0-1.0)"
    )

    # Explosion detection
    would_have_blocked: int = Field(
        ...,
        description="Number of jobs that would have been blocked by shadow"
    )
    explosion_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Rate of would-have-blocked (0.0-1.0)"
    )

    # Rule trigger counts
    rule_trigger_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of how often each rule was triggered"
    )

    # Safety assessment
    safe_to_activate: bool = Field(
        ...,
        description="True if shadow report indicates safe activation"
    )

    activation_gate_reason: str = Field(
        ...,
        description="Reason for safe/unsafe activation decision"
    )

    # Comparisons
    sample_comparisons: List[ShadowDecisionComparison] = Field(
        default_factory=list,
        description="Sample decision comparisons (max 100)"
    )


# ============================================================================
# Activation Gate Config
# ============================================================================

class ActivationGateConfig(BaseModel):
    """
    Configuration for manifest activation gate.

    Thresholds determine if shadow manifest is safe to activate.
    """

    max_mode_divergence_rate: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Maximum acceptable mode divergence rate (5% default)"
    )

    max_explosion_rate: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Maximum acceptable explosion rate (10% default)"
    )

    min_evaluation_count: int = Field(
        default=100,
        ge=1,
        description="Minimum evaluations before activation (100 default)"
    )

    shadow_duration_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Minimum shadow duration in hours (24h default, max 7 days)"
    )
