"""
Genesis Core Schemas

Request/response models for Genesis agent operations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.app.modules.genesis.traits import TraitSet


class SpawnAgentRequest(BaseModel):
    """Request to spawn new agent from blueprint."""

    blueprint_id: str  # Blueprint to use
    agent_id: Optional[str] = None  # Explicit ID (generated if None)
    trait_overrides: Optional[Dict[str, Any]] = None  # Override default traits
    seed: Optional[int] = None  # Random seed for determinism


class EvolveAgentRequest(BaseModel):
    """Request to evolve agent based on fitness."""

    agent_id: str  # Agent to evolve
    fitness_scores: Dict[str, float]  # Performance metrics (0-1)
    auto_mutate: bool = True  # Automatically apply mutations


class ReproduceAgentsRequest(BaseModel):
    """Request to create child agent from two parents."""

    parent1_id: str  # First parent
    parent2_id: str  # Second parent
    child_id: Optional[str] = None  # Explicit child ID


class GenesisAgentResult(BaseModel):
    """Result of agent creation."""

    agent_id: str  # Created agent ID
    blueprint_id: str  # Blueprint used
    dna_snapshot_id: int  # DNA snapshot ID
    traits: Dict[str, Any]  # Trait values
    validation_warnings: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GenesisEvolutionResult(BaseModel):
    """Result of agent evolution."""

    agent_id: str  # Evolved agent
    fitness_score: float  # Overall fitness (0-1)
    mutations_applied: List[Dict[str, Any]] = Field(default_factory=list)
    new_snapshot_id: Optional[int] = None  # New DNA snapshot (if mutated)
    validation_warnings: List[str] = Field(default_factory=list)


class GenesisReproductionResult(BaseModel):
    """Result of agent reproduction."""

    child_id: str  # New child agent
    parent1_id: str  # First parent
    parent2_id: str  # Second parent
    inherited_traits: Dict[str, Any]  # Inherited trait values
    dna_snapshot_id: int  # Child's DNA snapshot
    validation_warnings: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
