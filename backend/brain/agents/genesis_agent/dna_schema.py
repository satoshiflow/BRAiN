"""
DNA Schema v2.0 for Genesis Agent System

This module defines the complete DNA structure for BRAiN agents, including:
- Metadata and identity
- Skills and proficiencies
- Behavioral modules
- Ethics and compliance flags
- Resource limits and capabilities
- Mission affinity

All DNA structures are immutable after creation to ensure reproducibility
and security.

Author: Genesis Agent System
Version: 2.0.0
Created: 2026-01-02
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class AgentStatus(str, Enum):
    """
    Agent lifecycle status states.

    Lifecycle Flow:
    CREATED → QUARANTINED → ACTIVE → DECOMMISSIONED → ARCHIVED

    - CREATED: Initial state after genesis
    - QUARANTINED: Under review/testing (Phase 3)
    - ACTIVE: Operational and accepting missions
    - DECOMMISSIONED: Retired but not deleted
    - ARCHIVED: Historical record only
    """
    CREATED = "CREATED"
    QUARANTINED = "QUARANTINED"
    ACTIVE = "ACTIVE"
    DECOMMISSIONED = "DECOMMISSIONED"
    ARCHIVED = "ARCHIVED"


class AgentType(str, Enum):
    """
    Base agent types in the BRAiN ecosystem.

    Each type has specific capabilities and responsibilities:
    - Worker: Task execution and integration
    - Analyst: Data analysis and insights
    - Builder: Code generation and development
    - Memory: Knowledge management
    - Supervisor: Agent oversight
    - Ligase: Inter-agent communication
    - Karma: Ethical reasoning
    - Governor: Policy enforcement
    - Genesis: Agent creation
    """
    WORKER = "Worker"
    ANALYST = "Analyst"
    BUILDER = "Builder"
    MEMORY = "Memory"
    SUPERVISOR = "Supervisor"
    LIGASE = "Ligase"
    KARMA = "Karma"
    GOVERNOR = "Governor"
    GENESIS = "Genesis"


class DNAMetadata(BaseModel):
    """
    Core identity and lineage metadata for an agent.

    Attributes:
        id: Unique agent identifier (UUID4)
        name: Human-readable agent name (lowercase, alphanumeric + underscore)
        type: Base agent type from AgentType enum
        version: Agent version (semantic versioning)
        dna_schema_version: DNA schema version (MANDATORY for registry)
        parent_id: Parent agent ID for lineage tracking (Phase 2+)
        template_hash: SHA256 hash of source template (MANDATORY, format: "sha256:...")
        template_version: Version from template YAML
        created_at: UTC timestamp of creation
        created_by: Creator identifier (IMMUTABLE, always "genesis_agent")

    Example:
        >>> metadata = DNAMetadata(
        ...     name="worker_api_01",
        ...     type=AgentType.WORKER,
        ...     dna_schema_version="2.0",
        ...     template_hash="sha256:abc123...",
        ...     template_version="1.0"
        ... )
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., max_length=100, pattern=r"^[a-z0-9_]+$")
    type: AgentType
    version: str = "1.0.0"
    dna_schema_version: str = Field(..., description="DNA schema version (MANDATORY)")
    parent_id: Optional[str] = None
    template_hash: str = Field(..., description="SHA256 hash of template (MANDATORY)")
    template_version: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="genesis_agent", description="Creator (IMMUTABLE)")

    @field_validator('created_by')
    @classmethod
    def validate_created_by(cls, v: str) -> str:
        """Ensure created_by is always 'genesis_agent' (immutable)."""
        if v != "genesis_agent":
            raise ValueError("created_by must be 'genesis_agent' (immutable)")
        return v


class Skill(BaseModel):
    """
    Represents a specific skill with proficiency level.

    Attributes:
        skill_id: Unique skill identifier (e.g., "api_calls", "data_processing")
        proficiency: Skill level from 0.0 (novice) to 1.0 (expert)
        domains: List of specific domains for this skill

    Example:
        >>> skill = Skill(
        ...     skill_id="api_calls",
        ...     proficiency=0.85,
        ...     domains=["rest", "graphql", "grpc"]
        ... )
    """
    skill_id: str
    proficiency: float = Field(..., ge=0.0, le=1.0)
    domains: List[str] = Field(default_factory=list)

    @field_validator('proficiency')
    @classmethod
    def validate_proficiency(cls, v: float) -> float:
        """Ensure proficiency is between 0 and 1."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Proficiency must be between 0 and 1, got {v}")
        return v


class AgentTraits(BaseModel):
    """
    Core behavioral traits and functions.

    Attributes:
        base_type: Base agent type (must match metadata.type)
        primary_function: Main responsibility/purpose
        autonomy_level: Decision-making independence (1-5)
            1 = Fully supervised
            2 = Supervised with some autonomy
            3 = Semi-autonomous
            4 = Mostly autonomous
            5 = Fully autonomous

    Example:
        >>> traits = AgentTraits(
        ...     base_type=AgentType.WORKER,
        ...     primary_function="task_execution",
        ...     autonomy_level=2
        ... )
    """
    base_type: AgentType
    primary_function: str
    autonomy_level: int = Field(..., ge=1, le=5)

    @field_validator('autonomy_level')
    @classmethod
    def validate_autonomy(cls, v: int) -> int:
        """Ensure autonomy level is between 1 and 5."""
        if not (1 <= v <= 5):
            raise ValueError(f"Autonomy level must be between 1 and 5, got {v}")
        return v


class BehaviorModules(BaseModel):
    """
    Behavioral configuration modules.

    Attributes:
        communication_style: How the agent communicates (concise, formal, technical, etc.)
        decision_making: Decision framework (rule_based, data_driven, best_practices, etc.)
        collaboration_preference: Preferred collaboration mode (sync, async, hybrid)
        error_handling: Error handling strategy (retry_with_backoff, escalate_on_uncertainty, etc.)

    Example:
        >>> behavior = BehaviorModules(
        ...     communication_style="concise",
        ...     decision_making="rule_based",
        ...     collaboration_preference="sync",
        ...     error_handling="retry_with_backoff"
        ... )
    """
    communication_style: str
    decision_making: str
    collaboration_preference: str
    error_handling: str


class EthicsFlags(BaseModel):
    """
    Ethics and compliance configuration (IMMUTABLE).

    These flags ensure EU AI Act and DSGVO compliance.

    Attributes:
        data_privacy: Privacy level (strict, standard, relaxed)
        transparency: Audit requirements (full_audit, basic_audit, minimal)
        bias_awareness: Bias detection (enabled, disabled)
        human_override: Human override policy (always_allowed, conditional, never - IMMUTABLE)

    Important:
        All fields are immutable for security and compliance reasons.
        human_override must ALWAYS be "always_allowed" per EU AI Act Art. 16.

    Example:
        >>> ethics = EthicsFlags(
        ...     data_privacy="strict",
        ...     transparency="full_audit",
        ...     bias_awareness="enabled",
        ...     human_override="always_allowed"
        ... )
    """
    data_privacy: str = "strict"
    transparency: str = "full_audit"
    bias_awareness: str = "enabled"
    human_override: str = Field(
        default="always_allowed",
        description="Human override policy (IMMUTABLE, EU AI Act Art. 16)"
    )

    @field_validator('human_override')
    @classmethod
    def validate_human_override(cls, v: str) -> str:
        """Ensure human_override is always 'always_allowed' (immutable)."""
        if v != "always_allowed":
            raise ValueError(
                "human_override must be 'always_allowed' (IMMUTABLE, EU AI Act Art. 16)"
            )
        return v


class Capabilities(BaseModel):
    """
    Agent capabilities and permissions.

    Attributes:
        tools_allowed: List of allowed tool names
        connectors_allowed: List of allowed connector IDs
        network_access: Network access level (none, restricted, full)

    Example:
        >>> capabilities = Capabilities(
        ...     tools_allowed=["api_call", "data_fetch"],
        ...     connectors_allowed=[],
        ...     network_access="restricted"
        ... )
    """
    tools_allowed: List[str] = Field(default_factory=list)
    connectors_allowed: List[str] = Field(default_factory=list)
    network_access: str = "restricted"  # none | restricted | full


class RuntimeConfig(BaseModel):
    """
    Runtime LLM configuration.

    Attributes:
        model_policy: Model selection strategy (cheap, balanced, premium)
        temperature_cap: Maximum temperature for LLM calls
        max_tokens_cap: Maximum tokens per LLM call
        allowed_models: Whitelist of allowed LLM models

    Example:
        >>> runtime = RuntimeConfig(
        ...     model_policy="balanced",
        ...     temperature_cap=0.7,
        ...     max_tokens_cap=2000,
        ...     allowed_models=["llama3-8b-instruct-q4"]
        ... )
    """
    model_policy: str = "balanced"  # cheap | balanced | premium
    temperature_cap: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens_cap: int = 2000
    allowed_models: List[str] = Field(default_factory=list)

    @field_validator('temperature_cap')
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Ensure temperature is between 0 and 2."""
        if not (0.0 <= v <= 2.0):
            raise ValueError(f"Temperature must be between 0 and 2, got {v}")
        return v


class ResourceLimits(BaseModel):
    """
    Resource consumption limits.

    Attributes:
        max_credits_per_mission: Maximum credits per mission
        max_llm_calls_per_day: Daily LLM call limit
        timeout_seconds: Maximum execution time per mission

    Example:
        >>> limits = ResourceLimits(
        ...     max_credits_per_mission=100,
        ...     max_llm_calls_per_day=500,
        ...     timeout_seconds=300
        ... )
    """
    max_credits_per_mission: int = 100
    max_llm_calls_per_day: int = 500
    timeout_seconds: int = 300


class MissionAffinity(BaseModel):
    """
    Mission preferences and requirements.

    Attributes:
        preferred_types: List of preferred mission types
        required_context: List of required context keys

    Example:
        >>> affinity = MissionAffinity(
        ...     preferred_types=["execution", "integration"],
        ...     required_context=["api_endpoint", "payload"]
        ... )
    """
    preferred_types: List[str] = Field(default_factory=list)
    required_context: List[str] = Field(default_factory=list)


class AgentDNA(BaseModel):
    """
    Complete DNA structure for a BRAiN agent.

    This is the top-level DNA container that combines all sub-components
    into a complete, validated agent definition.

    Attributes:
        metadata: Agent identity and lineage
        traits: Behavioral traits and autonomy
        skills: List of skills with proficiencies
        behavior_modules: Communication and decision-making patterns
        ethics_flags: Ethics and compliance (IMMUTABLE)
        capabilities: Tools and network permissions
        runtime: LLM runtime configuration
        memory_seeds: Initial knowledge/context strings
        resource_limits: Budget and execution limits
        mission_affinity: Mission preferences

    Important:
        - metadata.created_by must be "genesis_agent" (IMMUTABLE)
        - ethics_flags.human_override must be "always_allowed" (IMMUTABLE)
        - metadata.dna_schema_version is MANDATORY
        - metadata.template_hash is MANDATORY

    Example:
        >>> dna = AgentDNA(
        ...     metadata=DNAMetadata(
        ...         name="worker_api_01",
        ...         type=AgentType.WORKER,
        ...         dna_schema_version="2.0",
        ...         template_hash="sha256:abc123...",
        ...         template_version="1.0"
        ...     ),
        ...     traits=AgentTraits(
        ...         base_type=AgentType.WORKER,
        ...         primary_function="task_execution",
        ...         autonomy_level=2
        ...     ),
        ...     skills=[
        ...         Skill(skill_id="api_calls", proficiency=0.8, domains=["rest"])
        ...     ],
        ...     # ... other components
        ... )
    """
    metadata: DNAMetadata
    traits: AgentTraits
    skills: List[Skill] = Field(default_factory=list)
    behavior_modules: BehaviorModules
    ethics_flags: EthicsFlags
    capabilities: Capabilities
    runtime: RuntimeConfig
    memory_seeds: List[str] = Field(default_factory=list)
    resource_limits: ResourceLimits
    mission_affinity: MissionAffinity

    @field_validator('skills')
    @classmethod
    def validate_skills(cls, v: List[Skill]) -> List[Skill]:
        """Validate all skills have proficiency between 0 and 1."""
        for skill in v:
            if not (0.0 <= skill.proficiency <= 1.0):
                raise ValueError(
                    f"Skill {skill.skill_id} has invalid proficiency: {skill.proficiency}"
                )
        return v

    def model_post_init(self, __context: Any) -> None:
        """
        Post-initialization validation.

        Ensures:
        - Base type consistency between metadata and traits
        - Mandatory fields are present
        """
        # Validate base_type consistency
        if self.traits.base_type != self.metadata.type:
            raise ValueError(
                f"Base type mismatch: metadata.type={self.metadata.type}, "
                f"traits.base_type={self.traits.base_type}"
            )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "metadata": {
                    "name": "worker_api_01",
                    "type": "Worker",
                    "version": "1.0.0",
                    "dna_schema_version": "2.0",
                    "template_hash": "sha256:abc123def456...",
                    "template_version": "1.0",
                    "created_by": "genesis_agent"
                },
                "traits": {
                    "base_type": "Worker",
                    "primary_function": "task_execution",
                    "autonomy_level": 2
                },
                "skills": [
                    {
                        "skill_id": "api_calls",
                        "proficiency": 0.80,
                        "domains": ["rest", "graphql"]
                    }
                ],
                "behavior_modules": {
                    "communication_style": "concise",
                    "decision_making": "rule_based",
                    "collaboration_preference": "sync",
                    "error_handling": "retry_with_backoff"
                },
                "ethics_flags": {
                    "data_privacy": "strict",
                    "transparency": "full_audit",
                    "bias_awareness": "enabled",
                    "human_override": "always_allowed"
                },
                "capabilities": {
                    "tools_allowed": ["api_call", "data_fetch"],
                    "connectors_allowed": [],
                    "network_access": "restricted"
                },
                "runtime": {
                    "model_policy": "balanced",
                    "temperature_cap": 0.7,
                    "max_tokens_cap": 2000,
                    "allowed_models": ["llama3-8b-instruct-q4"]
                },
                "memory_seeds": [
                    "Task execution best practices",
                    "API integration patterns"
                ],
                "resource_limits": {
                    "max_credits_per_mission": 100,
                    "max_llm_calls_per_day": 500,
                    "timeout_seconds": 300
                },
                "mission_affinity": {
                    "preferred_types": ["execution", "integration"],
                    "required_context": ["api_endpoint", "payload"]
                }
            }
        }


# Type aliases for convenience
DNA = AgentDNA
