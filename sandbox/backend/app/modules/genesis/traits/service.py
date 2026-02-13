"""
Trait Service

Manages trait definitions, validation, and mutation logic.
"""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from .definitions import ALL_TRAIT_DEFINITIONS, TRAIT_DEFINITIONS_BY_ID
from .schemas import (
    AgentTrait,
    TraitDefinition,
    TraitMutation,
    TraitSet,
    TraitType,
    TraitValidationResult,
)


class TraitService:
    """
    Service for managing agent traits.

    Provides:
    - Trait definition registry
    - Trait value validation
    - Mutation algorithms
    - Inheritance logic
    """

    def __init__(self):
        self.definitions: Dict[str, TraitDefinition] = {}
        self._load_builtin_traits()

    def _load_builtin_traits(self):
        """Load built-in trait definitions."""
        for trait in ALL_TRAIT_DEFINITIONS:
            self.definitions[trait.id] = trait

        logger.info(f"Loaded {len(self.definitions)} trait definitions")

    def get_definition(self, trait_id: str) -> Optional[TraitDefinition]:
        """Get trait definition by ID."""
        return self.definitions.get(trait_id)

    def get_all_definitions(self) -> List[TraitDefinition]:
        """Get all trait definitions."""
        return list(self.definitions.values())

    def register_custom_trait(self, definition: TraitDefinition):
        """
        Register custom trait definition.

        Args:
            definition: Trait definition to register
        """
        if definition.id in self.definitions:
            logger.warning(f"Overwriting existing trait definition: {definition.id}")

        self.definitions[definition.id] = definition
        logger.info(f"Registered custom trait: {definition.id}")

    def validate_trait_value(
        self, trait_id: str, value: Any
    ) -> TraitValidationResult:
        """
        Validate trait value against definition.

        Args:
            trait_id: Trait identifier
            value: Value to validate

        Returns:
            Validation result with errors/warnings
        """
        definition = self.get_definition(trait_id)

        if not definition:
            return TraitValidationResult(
                valid=False,
                trait_id=trait_id,
                value=value,
                errors=[f"Unknown trait: {trait_id}"],
            )

        errors = []
        warnings = []

        # Type validation
        if definition.type == TraitType.FLOAT:
            if not isinstance(value, (float, int)):
                errors.append(f"Expected float, got {type(value).__name__}")
            else:
                value = float(value)

                if definition.min_value is not None and value < definition.min_value:
                    errors.append(
                        f"Value {value} below minimum {definition.min_value}"
                    )

                if definition.max_value is not None and value > definition.max_value:
                    errors.append(
                        f"Value {value} above maximum {definition.max_value}"
                    )

        elif definition.type == TraitType.INT:
            if not isinstance(value, int):
                errors.append(f"Expected int, got {type(value).__name__}")
            else:
                if definition.min_value is not None and value < definition.min_value:
                    errors.append(
                        f"Value {value} below minimum {definition.min_value}"
                    )

                if definition.max_value is not None and value > definition.max_value:
                    errors.append(
                        f"Value {value} above maximum {definition.max_value}"
                    )

        elif definition.type == TraitType.ENUM:
            if (
                definition.allowed_values
                and value not in definition.allowed_values
            ):
                errors.append(
                    f"Value {value} not in allowed values {definition.allowed_values}"
                )

        elif definition.type == TraitType.BOOL:
            if not isinstance(value, bool):
                errors.append(f"Expected bool, got {type(value).__name__}")

        # Ethics check
        if definition.ethics_critical and errors:
            errors.append(
                "ETHICS VIOLATION: Ethics-critical trait has invalid value"
            )

        return TraitValidationResult(
            valid=len(errors) == 0,
            trait_id=trait_id,
            value=value,
            errors=errors,
            warnings=warnings,
        )

    def mutate_trait(
        self, trait: AgentTrait, mutation_strength: float = 0.1
    ) -> AgentTrait:
        """
        Apply controlled mutation to trait.

        Args:
            trait: Trait to mutate
            mutation_strength: Mutation intensity (0.0-1.0)

        Returns:
            Mutated trait (or original if immutable)
        """
        definition = self.get_definition(trait.trait_id)

        if not definition:
            logger.warning(f"Cannot mutate unknown trait: {trait.trait_id}")
            return trait

        if not definition.mutable:
            logger.debug(f"Trait {trait.trait_id} is immutable, skipping mutation")
            return trait

        # Apply mutation based on type
        if definition.type == TraitType.FLOAT:
            return self._mutate_float_trait(trait, definition, mutation_strength)

        elif definition.type == TraitType.INT:
            return self._mutate_int_trait(trait, definition, mutation_strength)

        elif definition.type == TraitType.ENUM:
            return self._mutate_enum_trait(trait, definition)

        elif definition.type == TraitType.BOOL:
            return self._mutate_bool_trait(trait, mutation_strength)

        return trait

    def _mutate_float_trait(
        self, trait: AgentTrait, definition: TraitDefinition, strength: float
    ) -> AgentTrait:
        """Mutate float trait using Gaussian noise."""
        current_value = float(trait.value)

        # Gaussian mutation
        delta = random.gauss(0, strength)
        new_value = current_value + delta

        # Clamp to bounds
        if definition.min_value is not None:
            new_value = max(new_value, definition.min_value)
        if definition.max_value is not None:
            new_value = min(new_value, definition.max_value)

        return trait.model_copy_with_value(new_value, source="mutation")

    def _mutate_int_trait(
        self, trait: AgentTrait, definition: TraitDefinition, strength: float
    ) -> AgentTrait:
        """Mutate int trait using discrete steps."""
        current_value = int(trait.value)

        # Random walk
        max_step = max(1, int(strength * 10))
        delta = random.randint(-max_step, max_step)
        new_value = current_value + delta

        # Clamp to bounds
        if definition.min_value is not None:
            new_value = max(new_value, int(definition.min_value))
        if definition.max_value is not None:
            new_value = min(new_value, int(definition.max_value))

        return trait.model_copy_with_value(new_value, source="mutation")

    def _mutate_enum_trait(
        self, trait: AgentTrait, definition: TraitDefinition
    ) -> AgentTrait:
        """Mutate enum trait by random selection."""
        if not definition.allowed_values:
            return trait

        # Random choice from allowed values
        new_value = random.choice(definition.allowed_values)

        return trait.model_copy_with_value(new_value, source="mutation")

    def _mutate_bool_trait(
        self, trait: AgentTrait, strength: float
    ) -> AgentTrait:
        """Mutate bool trait with flip probability."""
        # Flip with probability proportional to strength
        if random.random() < strength:
            new_value = not trait.value
            return trait.model_copy_with_value(new_value, source="mutation")

        return trait

    def inherit_traits(
        self, parent_traits: TraitSet, mutation_rate: float = 0.1
    ) -> TraitSet:
        """
        Create child trait set from parent with mutations.

        Args:
            parent_traits: Parent's trait set
            mutation_rate: Probability of mutation per trait (0.0-1.0)

        Returns:
            Child trait set with inherited and possibly mutated traits
        """
        child_traits = TraitSet(traits={})

        for trait_id, parent_trait in parent_traits.traits.items():
            definition = self.get_definition(trait_id)

            if not definition:
                logger.warning(f"Unknown trait in parent: {trait_id}, skipping")
                continue

            if not definition.inheritable:
                logger.debug(f"Trait {trait_id} not inheritable, skipping")
                continue

            # Inherit with possible mutation
            if random.random() < mutation_rate:
                child_trait = self.mutate_trait(parent_trait)
                logger.debug(
                    f"Mutated trait {trait_id}: {parent_trait.value} -> {child_trait.value}"
                )
            else:
                child_trait = AgentTrait(
                    trait_id=parent_trait.trait_id,
                    value=parent_trait.value,
                    source="inheritance",
                    confidence=parent_trait.confidence,
                    last_updated=datetime.utcnow(),
                )

            child_traits.traits[trait_id] = child_trait

        logger.info(
            f"Inherited {len(child_traits.traits)} traits with {mutation_rate:.1%} mutation rate"
        )
        return child_traits

    def crossover_traits(
        self, parent1_traits: TraitSet, parent2_traits: TraitSet, mutation_rate: float = 0.1
    ) -> TraitSet:
        """
        Create child trait set from two parents (genetic crossover).

        Args:
            parent1_traits: First parent's traits
            parent2_traits: Second parent's traits
            mutation_rate: Probability of mutation per trait

        Returns:
            Child trait set with mixed and mutated traits
        """
        child_traits = TraitSet(traits={})

        all_trait_ids = set(parent1_traits.traits.keys()) | set(
            parent2_traits.traits.keys()
        )

        for trait_id in all_trait_ids:
            # Randomly select from parents
            if trait_id in parent1_traits.traits and random.random() < 0.5:
                parent_trait = parent1_traits.traits[trait_id]
            elif trait_id in parent2_traits.traits:
                parent_trait = parent2_traits.traits[trait_id]
            elif trait_id in parent1_traits.traits:
                parent_trait = parent1_traits.traits[trait_id]
            else:
                continue

            # Check if inheritable
            definition = self.get_definition(trait_id)
            if not definition or not definition.inheritable:
                continue

            # Apply mutation
            if random.random() < mutation_rate:
                child_trait = self.mutate_trait(parent_trait)
            else:
                child_trait = AgentTrait(
                    trait_id=parent_trait.trait_id,
                    value=parent_trait.value,
                    source="crossover",
                    confidence=parent_trait.confidence,
                    last_updated=datetime.utcnow(),
                )

            child_traits.traits[trait_id] = child_trait

        logger.info(
            f"Crossover created {len(child_traits.traits)} traits from {len(parent1_traits.traits)} + {len(parent2_traits.traits)} parent traits"
        )
        return child_traits

    def create_default_trait_set(
        self, trait_ids: Optional[List[str]] = None
    ) -> TraitSet:
        """
        Create trait set with default values.

        Args:
            trait_ids: Specific traits to include (all if None)

        Returns:
            Trait set with default values
        """
        traits = TraitSet(traits={})

        definitions_to_use = (
            [self.get_definition(tid) for tid in trait_ids]
            if trait_ids
            else self.get_all_definitions()
        )

        for definition in definitions_to_use:
            if definition:
                traits.traits[definition.id] = AgentTrait(
                    trait_id=definition.id,
                    value=definition.default_value,
                    source="default",
                    confidence=1.0,
                )

        return traits


# Singleton instance
_trait_service: Optional[TraitService] = None


def get_trait_service() -> TraitService:
    """Get singleton TraitService instance."""
    global _trait_service
    if _trait_service is None:
        _trait_service = TraitService()
    return _trait_service
