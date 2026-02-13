"""
Governance Manifest Schema (Phase 2b)

Defines the declarative manifest structure for adaptive constraint governance.

Manifests allow policies and reductions to be configured declaratively
instead of hard-coded, enabling:
- Adaptive constraint reductions based on customizations
- AgentType-specific governance rules
- Environment-based policy overrides
- Version-controlled governance evolution

Author: Governor v1 System (Phase 2b)
Version: 2b.1
Created: 2026-01-02
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Reduction Spec
# ============================================================================

class ReductionSpec(BaseModel):
    """
    Specification for constraint reductions.

    Reductions are MONOTONIC: they can only reduce constraints, never expand them.

    Example:
        >>> reduction = ReductionSpec(
        ...     max_llm_calls_per_day="-50%",  # Reduce by 50%
        ...     network_access="disable",       # Disable network
        ...     parallelism="single"             # Force sequential
        ... )
    """

    # Budget reductions
    max_llm_calls_per_day: Optional[str] = Field(
        None,
        description="Reduction for max_llm_calls_per_day (e.g., '-50%', '-100')"
    )

    max_credits_per_mission: Optional[str] = Field(
        None,
        description="Reduction for max_credits_per_mission (e.g., '-30%')"
    )

    max_daily_credits: Optional[str] = Field(
        None,
        description="Reduction for max_daily_credits (e.g., '-200')"
    )

    # Capability reductions
    network_access: Optional[str] = Field(
        None,
        description="Network access reduction (e.g., 'disable', 'restrict')"
    )

    parallelism: Optional[str] = Field(
        None,
        description="Parallelism reduction (e.g., 'single', '-50%')"
    )

    allowed_models: Optional[List[str]] = Field(
        None,
        description="Subset of allowed models (monotonic reduction)"
    )

    # Runtime reductions
    max_tokens_cap: Optional[str] = Field(
        None,
        description="Token cap reduction (e.g., '-500', '-25%')"
    )

    temperature_cap: Optional[str] = Field(
        None,
        description="Temperature cap reduction (e.g., '-0.2', 'min')"
    )

    @field_validator('network_access')
    @classmethod
    def validate_network_access(cls, v: Optional[str]) -> Optional[str]:
        """Validate network access reduction."""
        if v is not None and v not in ["disable", "restrict", "none"]:
            raise ValueError(
                f"network_access reduction must be 'disable', 'restrict', or 'none', got: {v}"
            )
        return v

    @field_validator('parallelism')
    @classmethod
    def validate_parallelism(cls, v: Optional[str]) -> Optional[str]:
        """Validate parallelism reduction."""
        if v is not None:
            if v not in ["single"] and not v.startswith("-"):
                raise ValueError(
                    f"parallelism reduction must be 'single' or start with '-', got: {v}"
                )
        return v


# ============================================================================
# Risk Override
# ============================================================================

class RiskOverride(BaseModel):
    """
    Risk tier overrides based on conditions.

    Example:
        >>> override = RiskOverride(
        ...     if_customizations="MEDIUM",
        ...     if_external_network="HIGH"
        ... )
    """

    if_customizations: Optional[str] = Field(
        None,
        description="Risk tier if customizations present (LOW/MEDIUM/HIGH/CRITICAL)"
    )

    if_external_network: Optional[str] = Field(
        None,
        description="Risk tier if external network access requested"
    )

    if_personal_data: Optional[str] = Field(
        None,
        description="Risk tier if processing personal data"
    )

    @field_validator('if_customizations', 'if_external_network', 'if_personal_data')
    @classmethod
    def validate_risk_tier(cls, v: Optional[str]) -> Optional[str]:
        """Validate risk tier values."""
        if v is not None and v not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            raise ValueError(
                f"Risk tier must be LOW/MEDIUM/HIGH/CRITICAL, got: {v}"
            )
        return v


# ============================================================================
# Lock Spec
# ============================================================================

class LockSpec(BaseModel):
    """
    Immutable fields specification.

    Example:
        >>> locks = LockSpec(
        ...     immutable=["ethics_flags", "human_override"],
        ...     no_escalation=True
        ... )
    """

    immutable: List[str] = Field(
        default_factory=lambda: [
            "ethics_flags",
            "human_override",
            "metadata.created_by"
        ],
        description="DNA field paths that cannot be modified (IMMUTABLE)"
    )

    no_escalation: bool = Field(
        default=True,
        description="Prevent any constraint escalations (IMMUTABLE for Phase 2b)"
    )


# ============================================================================
# Applies To Spec
# ============================================================================

class AppliesToSpec(BaseModel):
    """
    Scope specification for manifest applicability.

    Example:
        >>> applies_to = AppliesToSpec(
        ...     agent_types=["Worker", "Analyst"],
        ...     environments=["dev", "staging"]
        ... )
    """

    agent_types: Optional[List[str]] = Field(
        None,
        description="AgentTypes this manifest applies to (None = all)"
    )

    environments: Optional[List[str]] = Field(
        None,
        description="Environments this manifest applies to (dev/staging/production)"
    )

    projects: Optional[List[str]] = Field(
        None,
        description="Projects this manifest applies to"
    )


# ============================================================================
# Governance Manifest
# ============================================================================

class GovernanceManifest(BaseModel):
    """
    Complete governance manifest.

    A manifest defines adaptive governance rules declaratively:
    - Who it applies to (agent_types, environments, projects)
    - What reductions to apply (on_customization)
    - Risk tier overrides
    - Immutable field locks

    Example:
        >>> manifest = GovernanceManifest(
        ...     manifest_version=1,
        ...     policy_version="2b.1",
        ...     name="strict_governance",
        ...     applies_to=AppliesToSpec(
        ...         agent_types=["Worker", "Analyst"]
        ...     ),
        ...     reductions=ReductionSections(
        ...         on_customization=ReductionSpec(
        ...             max_llm_calls_per_day="-50%",
        ...             network_access="disable"
        ...         )
        ...     ),
        ...     risk_overrides=RiskOverride(
        ...         if_customizations="MEDIUM"
        ...     ),
        ...     locks=LockSpec()
        ... )
    """

    # Manifest metadata
    manifest_version: int = Field(
        1,
        description="Manifest schema version"
    )

    policy_version: str = Field(
        "2b.1",
        description="Policy version (e.g., '2b.1', '2b.2')"
    )

    name: str = Field(
        ...,
        description="Manifest name (e.g., 'default', 'strict', 'permissive')"
    )

    description: Optional[str] = Field(
        None,
        description="Human-readable description"
    )

    # Applicability
    applies_to: AppliesToSpec = Field(
        default_factory=AppliesToSpec,
        description="Scope of manifest applicability"
    )

    # Reductions
    reductions: ReductionSections = Field(
        default_factory=lambda: ReductionSections(),
        description="Constraint reduction rules"
    )

    # Risk overrides
    risk_overrides: RiskOverride = Field(
        default_factory=RiskOverride,
        description="Risk tier overrides based on conditions"
    )

    # Locks
    locks: LockSpec = Field(
        default_factory=LockSpec,
        description="Immutable field specifications"
    )

    # Metadata
    created_at: Optional[str] = Field(
        None,
        description="Manifest creation timestamp"
    )

    created_by: Optional[str] = Field(
        None,
        description="Manifest creator"
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "manifest_version": 1,
                "policy_version": "2b.1",
                "name": "strict_governance",
                "description": "Strict governance for Worker and Analyst agents",
                "applies_to": {
                    "agent_types": ["Worker", "Analyst"],
                    "environments": ["production"]
                },
                "reductions": {
                    "on_customization": {
                        "max_llm_calls_per_day": "-50%",
                        "network_access": "disable",
                        "parallelism": "single"
                    }
                },
                "risk_overrides": {
                    "if_customizations": "MEDIUM",
                    "if_external_network": "HIGH"
                },
                "locks": {
                    "immutable": [
                        "ethics_flags",
                        "human_override",
                        "metadata.created_by"
                    ],
                    "no_escalation": True
                }
            }
        }


class ReductionSections(BaseModel):
    """
    Reduction sections for different triggers.

    Currently only on_customization is supported.
    Future: on_risk_escalation, on_budget_pressure, etc.
    """

    on_customization: ReductionSpec = Field(
        default_factory=ReductionSpec,
        description="Reductions to apply when customizations are present"
    )
