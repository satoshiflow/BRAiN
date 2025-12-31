"""Trait system for inheritable agent characteristics."""

from .schemas import (
    TraitCategory,
    TraitType,
    TraitDefinition,
    AgentTrait,
    TraitSet,
)
from .definitions import (
    COGNITIVE_TRAITS,
    ETHICAL_TRAITS,
    PERFORMANCE_TRAITS,
    BEHAVIORAL_TRAITS,
    SOCIAL_TRAITS,
    TECHNICAL_TRAITS,
    ALL_TRAIT_DEFINITIONS,
)
from .service import TraitService, get_trait_service

__all__ = [
    "TraitCategory",
    "TraitType",
    "TraitDefinition",
    "AgentTrait",
    "TraitSet",
    "COGNITIVE_TRAITS",
    "ETHICAL_TRAITS",
    "PERFORMANCE_TRAITS",
    "BEHAVIORAL_TRAITS",
    "SOCIAL_TRAITS",
    "TECHNICAL_TRAITS",
    "ALL_TRAIT_DEFINITIONS",
    "TraitService",
    "get_trait_service",
]
