"""
Blueprint System Schemas

Agent template definitions with trait profiles and capabilities.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BlueprintCapability(BaseModel):
    """A capability that a blueprint provides."""

    id: str  # Unique capability ID
    name: str  # Human-readable name
    description: str  # Detailed description
    required_tools: List[str] = Field(default_factory=list)  # Tools needed
    required_permissions: List[str] = Field(default_factory=list)  # Permissions needed


class AgentBlueprint(BaseModel):
    """
    Complete agent template definition.

    Blueprints define predefined agent archetypes with:
    - Base configuration (model, temperature, etc.)
    - Trait profile (default trait values)
    - Capabilities and tools
    - Evolution parameters
    - Ethics constraints
    """

    # Identity
    id: str  # Unique blueprint ID (e.g., "fleet_coordinator_v1")
    name: str  # Human-readable name
    version: str = "1.0.0"  # Blueprint version
    description: str  # Detailed description

    # Configuration
    base_config: Dict[str, Any] = Field(
        default_factory=dict
    )  # AgentConfig fields
    trait_profile: Dict[str, Any] = Field(
        default_factory=dict
    )  # Default trait values (trait_id -> value)

    # Capabilities
    capabilities: List[BlueprintCapability] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)  # Tool names
    permissions: List[str] = Field(default_factory=list)  # Permission names

    # Evolution
    allow_mutations: bool = True  # Allow evolution
    mutation_rate: float = Field(
        default=0.1, ge=0.0, le=1.0
    )  # Mutation probability
    fitness_criteria: Dict[str, float] = Field(
        default_factory=dict
    )  # metric -> weight

    # Ethics
    ethics_constraints: Dict[str, Any] = Field(
        default_factory=dict
    )  # Custom constraints
    required_policy_compliance: List[str] = Field(
        default_factory=list
    )  # Policy IDs

    # Metadata
    author: str = "system"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list)

    def get_trait_value(self, trait_id: str, default: Any = None) -> Any:
        """Get trait value from profile."""
        return self.trait_profile.get(trait_id, default)

    def has_capability(self, capability_id: str) -> bool:
        """Check if blueprint has capability."""
        return any(cap.id == capability_id for cap in self.capabilities)


class BlueprintLibrary:
    """
    Registry of available blueprints.

    Manages built-in and custom blueprint definitions.
    """

    def __init__(self):
        self.blueprints: Dict[str, AgentBlueprint] = {}

    def register(self, blueprint: AgentBlueprint):
        """
        Register blueprint.

        Args:
            blueprint: Blueprint to register
        """
        self.blueprints[blueprint.id] = blueprint

    def get(self, blueprint_id: str) -> Optional[AgentBlueprint]:
        """
        Get blueprint by ID.

        Args:
            blueprint_id: Blueprint identifier

        Returns:
            Blueprint or None if not found
        """
        return self.blueprints.get(blueprint_id)

    def list_all(self) -> List[AgentBlueprint]:
        """Get all registered blueprints."""
        return list(self.blueprints.values())

    def list_by_tag(self, tag: str) -> List[AgentBlueprint]:
        """Get blueprints with specific tag."""
        return [bp for bp in self.blueprints.values() if tag in bp.tags]

    def remove(self, blueprint_id: str) -> bool:
        """
        Remove blueprint.

        Args:
            blueprint_id: Blueprint to remove

        Returns:
            True if removed, False if not found
        """
        if blueprint_id in self.blueprints:
            del self.blueprints[blueprint_id]
            return True
        return False

    def count(self) -> int:
        """Get number of registered blueprints."""
        return len(self.blueprints)
