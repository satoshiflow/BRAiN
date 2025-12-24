"""
Trait System Schemas

Defines inheritable agent characteristics with validation and mutation support.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TraitCategory(str, Enum):
    """Categories of agent traits."""

    COGNITIVE = "cognitive"  # Intelligence, reasoning, learning
    BEHAVIORAL = "behavioral"  # Response patterns, decision-making
    PERFORMANCE = "performance"  # Speed, accuracy, efficiency
    ETHICAL = "ethical"  # Alignment, safety, compliance
    SOCIAL = "social"  # Communication, collaboration, empathy
    TECHNICAL = "technical"  # Skills, capabilities, expertise


class TraitType(str, Enum):
    """Data types for trait values."""

    FLOAT = "float"  # 0.0 - 1.0 normalized continuous value
    INT = "int"  # Discrete integer value
    ENUM = "enum"  # Categorical value from allowed set
    BOOL = "bool"  # Binary true/false


class TraitDefinition(BaseModel):
    """
    Defines a trait that agents can have.

    Traits are inheritable characteristics that define agent behavior,
    capabilities, and ethical alignment.
    """

    id: str  # Unique identifier (e.g., "cognitive.reasoning_depth")
    name: str  # Human-readable name
    category: TraitCategory
    type: TraitType
    default_value: Any  # Default value for new agents
    min_value: Optional[float] = None  # Minimum allowed (for FLOAT/INT)
    max_value: Optional[float] = None  # Maximum allowed (for FLOAT/INT)
    allowed_values: Optional[List[Any]] = None  # Allowed values (for ENUM)
    inheritable: bool = True  # Can be passed to offspring
    mutable: bool = True  # Can evolve through mutations
    ethics_critical: bool = False  # Requires Foundation layer validation
    description: str  # Detailed description

    class Config:
        frozen = True  # Trait definitions are immutable


class AgentTrait(BaseModel):
    """
    An agent's specific trait value.

    Represents a single trait instance for an agent,
    including value, source, and metadata.
    """

    trait_id: str  # References TraitDefinition.id
    value: Any  # Current trait value
    source: str = "genesis"  # Origin: genesis|mutation|inheritance|manual
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)  # Strength of trait
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    def model_copy_with_value(self, new_value: Any, source: str = "mutation") -> AgentTrait:
        """Create copy with new value."""
        return AgentTrait(
            trait_id=self.trait_id,
            value=new_value,
            source=source,
            confidence=self.confidence * 0.95,  # Slight decay on mutation
            last_updated=datetime.utcnow(),
        )


class TraitSet(BaseModel):
    """
    Collection of traits for an agent.

    Provides methods for accessing, updating, and inheriting traits.
    """

    traits: Dict[str, AgentTrait] = Field(default_factory=dict)

    def get(self, trait_id: str) -> Optional[AgentTrait]:
        """Get trait by ID."""
        return self.traits.get(trait_id)

    def set(self, trait_id: str, value: Any, source: str = "mutation") -> None:
        """
        Update or add trait.

        Args:
            trait_id: Trait identifier
            value: New trait value
            source: Source of change (mutation, inheritance, etc.)
        """
        existing = self.traits.get(trait_id)

        if existing:
            self.traits[trait_id] = existing.model_copy_with_value(value, source)
        else:
            self.traits[trait_id] = AgentTrait(
                trait_id=trait_id, value=value, source=source
            )

    def has_trait(self, trait_id: str) -> bool:
        """Check if trait exists."""
        return trait_id in self.traits

    def get_value(self, trait_id: str, default: Any = None) -> Any:
        """Get trait value with fallback."""
        trait = self.get(trait_id)
        return trait.value if trait else default

    def to_dict(self) -> Dict[str, Any]:
        """Convert to simple dict of trait_id -> value."""
        return {trait_id: trait.value for trait_id, trait in self.traits.items()}

    def model_copy(self, deep: bool = True) -> TraitSet:
        """Create deep copy of trait set."""
        if deep:
            return TraitSet(
                traits={
                    trait_id: AgentTrait(**trait.model_dump())
                    for trait_id, trait in self.traits.items()
                }
            )
        return TraitSet(traits=self.traits.copy())


class TraitMutation(BaseModel):
    """
    Proposed mutation to a trait.

    Used during evolution to track changes.
    """

    trait_id: str
    old_value: Any
    new_value: Any
    reason: str
    delta: Optional[float] = None  # Magnitude of change (for numeric traits)


class TraitValidationResult(BaseModel):
    """Result of trait validation."""

    valid: bool
    trait_id: str
    value: Any
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
