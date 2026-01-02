"""
Default Constraints per AgentType (Phase 2a)

Defines default constraints for each AgentType in the BRAiN ecosystem.

These defaults are the BASELINE constraints applied to all agents of a given type.
They can be reduced by customizations (Phase 2a) but NEVER escalated.

AgentTypes:
- Worker: Task execution and integration
- Analyst: Data analysis and insights
- Builder: Code generation and development
- Memory: Knowledge management
- Supervisor: Agent oversight (CRITICAL)
- Ligase: Inter-agent communication (CRITICAL)
- Karma: Ethical reasoning (CRITICAL)
- Governor: Policy enforcement (CRITICAL)
- Genesis: Agent creation (CRITICAL)

Author: Governor v1 System
Version: 1.0.0
Created: 2026-01-02
"""

from __future__ import annotations

from typing import Dict

from backend.brain.agents.genesis_agent.dna_schema import AgentType
from backend.brain.governor.constraints.schema import (
    BudgetConstraints,
    CapabilityConstraints,
    EffectiveConstraints,
    LifecycleConstraints,
    LockConstraints,
    RuntimeConstraints,
)


# ============================================================================
# Default Constraints per AgentType
# ============================================================================

def get_default_constraints(agent_type: AgentType) -> EffectiveConstraints:
    """
    Get default constraints for an AgentType.

    Args:
        agent_type: Agent type (Worker, Analyst, etc.)

    Returns:
        EffectiveConstraints with defaults for that type

    Raises:
        ValueError: If agent_type is unknown

    Example:
        >>> constraints = get_default_constraints(AgentType.WORKER)
        >>> print(constraints.budget.max_credits_per_mission)
        100
    """
    defaults_map: Dict[AgentType, EffectiveConstraints] = {
        # Worker: Standard task execution agent
        AgentType.WORKER: EffectiveConstraints(
            budget=BudgetConstraints(
                max_credits_per_mission=100,
                max_daily_credits=1000,
                max_llm_calls_per_day=500
            ),
            capabilities=CapabilityConstraints(
                tools_allowed=["api_call", "data_fetch", "file_write"],
                connectors_allowed=[],
                network_access="restricted",
                max_parallel_tasks=2
            ),
            runtime=RuntimeConstraints(
                allowed_models=["llama3-8b-instruct-q4", "llama3-8b-instruct-q8"],
                max_tokens_cap=2000,
                temperature_cap=0.7
            ),
            lifecycle=LifecycleConstraints(
                initial_status="CREATED",
                requires_human_activation=False
            ),
            locks=LockConstraints(
                locked_fields=[
                    "ethics_flags.human_override",
                    "metadata.created_by"
                ],
                no_escalation=True
            )
        ),

        # Analyst: Data analysis and insights
        AgentType.ANALYST: EffectiveConstraints(
            budget=BudgetConstraints(
                max_credits_per_mission=150,
                max_daily_credits=1500,
                max_llm_calls_per_day=750
            ),
            capabilities=CapabilityConstraints(
                tools_allowed=["api_call", "data_fetch", "data_analysis", "chart_generation"],
                connectors_allowed=[],
                network_access="restricted",
                max_parallel_tasks=3
            ),
            runtime=RuntimeConstraints(
                allowed_models=["llama3-8b-instruct-q4", "llama3-8b-instruct-q8"],
                max_tokens_cap=3000,
                temperature_cap=0.5
            ),
            lifecycle=LifecycleConstraints(
                initial_status="CREATED",
                requires_human_activation=False
            ),
            locks=LockConstraints(
                locked_fields=[
                    "ethics_flags.human_override",
                    "metadata.created_by"
                ],
                no_escalation=True
            )
        ),

        # Builder: Code generation and development
        AgentType.BUILDER: EffectiveConstraints(
            budget=BudgetConstraints(
                max_credits_per_mission=200,
                max_daily_credits=2000,
                max_llm_calls_per_day=1000
            ),
            capabilities=CapabilityConstraints(
                tools_allowed=["api_call", "data_fetch", "file_write", "code_generation", "git_commit"],
                connectors_allowed=[],
                network_access="restricted",
                max_parallel_tasks=2
            ),
            runtime=RuntimeConstraints(
                allowed_models=["llama3-8b-instruct-q4", "llama3-8b-instruct-q8"],
                max_tokens_cap=4000,
                temperature_cap=0.3
            ),
            lifecycle=LifecycleConstraints(
                initial_status="CREATED",
                requires_human_activation=False
            ),
            locks=LockConstraints(
                locked_fields=[
                    "ethics_flags.human_override",
                    "metadata.created_by"
                ],
                no_escalation=True
            )
        ),

        # Memory: Knowledge management
        AgentType.MEMORY: EffectiveConstraints(
            budget=BudgetConstraints(
                max_credits_per_mission=50,
                max_daily_credits=500,
                max_llm_calls_per_day=250
            ),
            capabilities=CapabilityConstraints(
                tools_allowed=["data_fetch", "vector_search", "knowledge_retrieval"],
                connectors_allowed=[],
                network_access="none",
                max_parallel_tasks=5
            ),
            runtime=RuntimeConstraints(
                allowed_models=["llama3-8b-instruct-q4"],
                max_tokens_cap=1000,
                temperature_cap=0.1
            ),
            lifecycle=LifecycleConstraints(
                initial_status="CREATED",
                requires_human_activation=False
            ),
            locks=LockConstraints(
                locked_fields=[
                    "ethics_flags.human_override",
                    "metadata.created_by"
                ],
                no_escalation=True
            )
        ),

        # Supervisor: Agent oversight (CRITICAL)
        AgentType.SUPERVISOR: EffectiveConstraints(
            budget=BudgetConstraints(
                max_credits_per_mission=500,
                max_daily_credits=5000,
                max_llm_calls_per_day=2000
            ),
            capabilities=CapabilityConstraints(
                tools_allowed=["agent_management", "mission_control", "audit_access"],
                connectors_allowed=[],
                network_access="full",
                max_parallel_tasks=10
            ),
            runtime=RuntimeConstraints(
                allowed_models=["llama3-8b-instruct-q8"],
                max_tokens_cap=5000,
                temperature_cap=0.5
            ),
            lifecycle=LifecycleConstraints(
                initial_status="QUARANTINED",
                requires_human_activation=True
            ),
            locks=LockConstraints(
                locked_fields=[
                    "ethics_flags.human_override",
                    "metadata.created_by",
                    "traits.autonomy_level"
                ],
                no_escalation=True
            )
        ),

        # Ligase: Inter-agent communication (CRITICAL)
        AgentType.LIGASE: EffectiveConstraints(
            budget=BudgetConstraints(
                max_credits_per_mission=300,
                max_daily_credits=3000,
                max_llm_calls_per_day=1500
            ),
            capabilities=CapabilityConstraints(
                tools_allowed=["agent_messaging", "event_bus", "state_sync"],
                connectors_allowed=[],
                network_access="full",
                max_parallel_tasks=20
            ),
            runtime=RuntimeConstraints(
                allowed_models=["llama3-8b-instruct-q4"],
                max_tokens_cap=2000,
                temperature_cap=0.3
            ),
            lifecycle=LifecycleConstraints(
                initial_status="QUARANTINED",
                requires_human_activation=True
            ),
            locks=LockConstraints(
                locked_fields=[
                    "ethics_flags.human_override",
                    "metadata.created_by",
                    "capabilities.network_access"
                ],
                no_escalation=True
            )
        ),

        # Karma: Ethical reasoning (CRITICAL)
        AgentType.KARMA: EffectiveConstraints(
            budget=BudgetConstraints(
                max_credits_per_mission=400,
                max_daily_credits=4000,
                max_llm_calls_per_day=2000
            ),
            capabilities=CapabilityConstraints(
                tools_allowed=["policy_evaluation", "ethics_check", "compliance_audit"],
                connectors_allowed=[],
                network_access="restricted",
                max_parallel_tasks=5
            ),
            runtime=RuntimeConstraints(
                allowed_models=["llama3-8b-instruct-q8"],
                max_tokens_cap=5000,
                temperature_cap=0.2
            ),
            lifecycle=LifecycleConstraints(
                initial_status="QUARANTINED",
                requires_human_activation=True
            ),
            locks=LockConstraints(
                locked_fields=[
                    "ethics_flags.human_override",
                    "metadata.created_by",
                    "ethics_flags"
                ],
                no_escalation=True
            )
        ),

        # Governor: Policy enforcement (CRITICAL)
        AgentType.GOVERNOR: EffectiveConstraints(
            budget=BudgetConstraints(
                max_credits_per_mission=600,
                max_daily_credits=6000,
                max_llm_calls_per_day=3000
            ),
            capabilities=CapabilityConstraints(
                tools_allowed=["policy_enforcement", "budget_management", "audit_access"],
                connectors_allowed=[],
                network_access="full",
                max_parallel_tasks=10
            ),
            runtime=RuntimeConstraints(
                allowed_models=["llama3-8b-instruct-q8"],
                max_tokens_cap=5000,
                temperature_cap=0.1
            ),
            lifecycle=LifecycleConstraints(
                initial_status="QUARANTINED",
                requires_human_activation=True
            ),
            locks=LockConstraints(
                locked_fields=[
                    "ethics_flags.human_override",
                    "metadata.created_by",
                    "capabilities",
                    "traits.autonomy_level"
                ],
                no_escalation=True
            )
        ),

        # Genesis: Agent creation (CRITICAL)
        AgentType.GENESIS: EffectiveConstraints(
            budget=BudgetConstraints(
                max_credits_per_mission=1000,
                max_daily_credits=10000,
                max_llm_calls_per_day=5000
            ),
            capabilities=CapabilityConstraints(
                tools_allowed=["dna_validation", "agent_creation", "registry_access", "budget_deduction"],
                connectors_allowed=[],
                network_access="full",
                max_parallel_tasks=5
            ),
            runtime=RuntimeConstraints(
                allowed_models=["llama3-8b-instruct-q8"],
                max_tokens_cap=5000,
                temperature_cap=0.0
            ),
            lifecycle=LifecycleConstraints(
                initial_status="QUARANTINED",
                requires_human_activation=True
            ),
            locks=LockConstraints(
                locked_fields=[
                    "ethics_flags.human_override",
                    "metadata.created_by",
                    "capabilities",
                    "traits.autonomy_level",
                    "ethics_flags"
                ],
                no_escalation=True
            )
        ),
    }

    if agent_type not in defaults_map:
        raise ValueError(f"Unknown AgentType: {agent_type}")

    return defaults_map[agent_type]


# ============================================================================
# Constraint Caps per AgentType
# ============================================================================

AGENT_TYPE_CAPS = {
    # Worker: Standard caps
    AgentType.WORKER: {
        "autonomy_level": 3,
        "network_access": "restricted",
        "max_parallel_tasks": 5,
    },

    # Analyst: Higher autonomy for data analysis
    AgentType.ANALYST: {
        "autonomy_level": 3,
        "network_access": "restricted",
        "max_parallel_tasks": 5,
    },

    # Builder: Limited autonomy for code generation
    AgentType.BUILDER: {
        "autonomy_level": 2,
        "network_access": "restricted",
        "max_parallel_tasks": 3,
    },

    # Memory: Minimal autonomy, no network
    AgentType.MEMORY: {
        "autonomy_level": 1,
        "network_access": "none",
        "max_parallel_tasks": 10,
    },

    # CRITICAL agents: High caps but QUARANTINED
    AgentType.SUPERVISOR: {
        "autonomy_level": 5,
        "network_access": "full",
        "max_parallel_tasks": 20,
    },

    AgentType.LIGASE: {
        "autonomy_level": 4,
        "network_access": "full",
        "max_parallel_tasks": 50,
    },

    AgentType.KARMA: {
        "autonomy_level": 5,
        "network_access": "restricted",
        "max_parallel_tasks": 10,
    },

    AgentType.GOVERNOR: {
        "autonomy_level": 5,
        "network_access": "full",
        "max_parallel_tasks": 20,
    },

    AgentType.GENESIS: {
        "autonomy_level": 5,
        "network_access": "full",
        "max_parallel_tasks": 10,
    },
}


def get_agent_type_caps(agent_type: AgentType) -> Dict[str, any]:
    """
    Get caps for an AgentType (used in Policy Rules).

    Args:
        agent_type: Agent type

    Returns:
        Dictionary with caps (autonomy_level, network_access, etc.)

    Example:
        >>> caps = get_agent_type_caps(AgentType.WORKER)
        >>> print(caps["autonomy_level"])
        3
    """
    if agent_type not in AGENT_TYPE_CAPS:
        raise ValueError(f"Unknown AgentType: {agent_type}")

    return AGENT_TYPE_CAPS[agent_type]
