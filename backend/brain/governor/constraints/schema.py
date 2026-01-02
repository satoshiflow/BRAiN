"""
EffectiveConstraints Schema (Phase 2a)

Defines constraints that are applied to agents based on:
- AgentType defaults
- Policy rule overrides
- Customization reductions (Phase 2a: no escalations allowed)

Constraints cover:
- Budget limits (credits, LLM calls)
- Capabilities (tools, connectors, network access, parallelism)
- Runtime (models, tokens, temperature)
- Lifecycle (status, activation)
- Locks (immutable fields, escalation prevention)

Author: Governor v1 System
Version: 1.0.0
Created: 2026-01-02
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Budget Constraints
# ============================================================================

class BudgetConstraints(BaseModel):
    """
    Budget constraints for agent resource consumption.

    Attributes:
        max_credits_per_mission: Maximum credits per single mission
        max_daily_credits: Maximum credits per day (rolling window)
        max_llm_calls_per_day: Maximum LLM calls per day
    """
    max_credits_per_mission: int = Field(
        ...,
        ge=0,
        description="Maximum credits per mission"
    )

    max_daily_credits: int = Field(
        ...,
        ge=0,
        description="Maximum credits per day (rolling 24h window)"
    )

    max_llm_calls_per_day: int = Field(
        ...,
        ge=0,
        description="Maximum LLM calls per day"
    )


# ============================================================================
# Capability Constraints
# ============================================================================

class CapabilityConstraints(BaseModel):
    """
    Capability constraints for agent permissions.

    Attributes:
        tools_allowed: Whitelist of allowed tool names
        connectors_allowed: Whitelist of allowed connector IDs
        network_access: Network access level (none/restricted/full)
        max_parallel_tasks: Maximum parallel tasks (0 = sequential only)
    """
    tools_allowed: List[str] = Field(
        default_factory=list,
        description="Whitelist of allowed tool names"
    )

    connectors_allowed: List[str] = Field(
        default_factory=list,
        description="Whitelist of allowed connector IDs"
    )

    network_access: str = Field(
        default="restricted",
        description="Network access level (none/restricted/full)"
    )

    max_parallel_tasks: int = Field(
        default=1,
        ge=0,
        description="Maximum parallel tasks (0 = sequential only)"
    )


# ============================================================================
# Runtime Constraints
# ============================================================================

class RuntimeConstraints(BaseModel):
    """
    Runtime constraints for LLM configuration.

    Attributes:
        allowed_models: Whitelist of allowed LLM models
        max_tokens_cap: Maximum tokens per LLM call
        temperature_cap: Maximum temperature for LLM calls
    """
    allowed_models: List[str] = Field(
        default_factory=list,
        description="Whitelist of allowed LLM models"
    )

    max_tokens_cap: int = Field(
        default=2000,
        ge=100,
        le=100000,
        description="Maximum tokens per LLM call"
    )

    temperature_cap: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Maximum temperature for LLM calls"
    )


# ============================================================================
# Lifecycle Constraints
# ============================================================================

class LifecycleConstraints(BaseModel):
    """
    Lifecycle constraints for agent activation.

    Attributes:
        initial_status: Initial status after creation (CREATED or QUARANTINED)
        requires_human_activation: Whether human must activate agent
    """
    initial_status: str = Field(
        default="CREATED",
        description="Initial status (CREATED or QUARANTINED)"
    )

    requires_human_activation: bool = Field(
        default=False,
        description="Whether human must activate agent"
    )


# ============================================================================
# Lock Constraints
# ============================================================================

class LockConstraints(BaseModel):
    """
    Lock constraints to prevent tampering.

    Attributes:
        locked_fields: List of DNA field paths that cannot be modified
        no_escalation: Prevent any capability/budget escalations (IMMUTABLE)
    """
    locked_fields: List[str] = Field(
        default_factory=list,
        description="DNA field paths that cannot be modified (e.g., 'ethics_flags.human_override')"
    )

    no_escalation: bool = Field(
        default=True,
        description="Prevent any capability/budget escalations (IMMUTABLE for Phase 2a)"
    )


# ============================================================================
# Effective Constraints
# ============================================================================

class EffectiveConstraints(BaseModel):
    """
    Complete effective constraints for an agent.

    These constraints are the result of:
    1. AgentType defaults (from defaults.py)
    2. Policy rule overrides (if triggered)
    3. Customization reductions (Phase 2a: no escalations)

    All constraints are IMMUTABLE after agent creation.

    Example:
        >>> constraints = EffectiveConstraints(
        ...     budget=BudgetConstraints(
        ...         max_credits_per_mission=100,
        ...         max_daily_credits=1000,
        ...         max_llm_calls_per_day=500
        ...     ),
        ...     capabilities=CapabilityConstraints(
        ...         tools_allowed=["api_call"],
        ...         network_access="restricted"
        ...     ),
        ...     runtime=RuntimeConstraints(
        ...         allowed_models=["llama3-8b-instruct-q4"],
        ...         max_tokens_cap=2000
        ...     ),
        ...     lifecycle=LifecycleConstraints(
        ...         initial_status="CREATED"
        ...     ),
        ...     locks=LockConstraints(
        ...         locked_fields=["ethics_flags.human_override"],
        ...         no_escalation=True
        ...     )
        ... )
    """

    # Constraint categories
    budget: BudgetConstraints = Field(
        ...,
        description="Budget constraints"
    )

    capabilities: CapabilityConstraints = Field(
        ...,
        description="Capability constraints"
    )

    runtime: RuntimeConstraints = Field(
        ...,
        description="Runtime constraints"
    )

    lifecycle: LifecycleConstraints = Field(
        ...,
        description="Lifecycle constraints"
    )

    locks: LockConstraints = Field(
        ...,
        description="Lock constraints (immutable fields)"
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "budget": {
                    "max_credits_per_mission": 100,
                    "max_daily_credits": 1000,
                    "max_llm_calls_per_day": 500
                },
                "capabilities": {
                    "tools_allowed": ["api_call", "data_fetch"],
                    "connectors_allowed": [],
                    "network_access": "restricted",
                    "max_parallel_tasks": 1
                },
                "runtime": {
                    "allowed_models": ["llama3-8b-instruct-q4"],
                    "max_tokens_cap": 2000,
                    "temperature_cap": 0.7
                },
                "lifecycle": {
                    "initial_status": "CREATED",
                    "requires_human_activation": False
                },
                "locks": {
                    "locked_fields": [
                        "ethics_flags.human_override",
                        "metadata.created_by"
                    ],
                    "no_escalation": True
                }
            }
        }
