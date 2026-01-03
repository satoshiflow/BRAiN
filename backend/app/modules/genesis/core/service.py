"""
Genesis Core Service

Main service for agent spawning, evolution, and reproduction.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger

from app.modules.dna.core.service import DNAService
from app.modules.dna.schemas import (
    CreateDNASnapshotRequest,
    MutateDNARequest,
)
from app.modules.genesis.blueprints import get_blueprint_library
from app.modules.genesis.foundation import (
    AgentCreationContext,
    FoundationLayer,
    MutationContext,
    get_foundation_layer,
)
from app.modules.genesis.traits import TraitSet, get_trait_service
from backend.brain.agents.agent_manager import AgentDefinition, AgentManager

from .exceptions import EthicsViolationError, GenesisError
from .schemas import (
    EvolveAgentRequest,
    GenesisAgentResult,
    GenesisEvolutionResult,
    GenesisReproductionResult,
    ReproduceAgentsRequest,
    SpawnAgentRequest,
)


class GenesisService:
    """
    Genesis Agent Creation and Evolution Service.

    Provides:
    - Deterministic agent spawning from blueprints
    - DNA-driven evolution with mutations
    - Genetic crossover and reproduction
    - Ethics validation at all stages
    """

    def __init__(
        self,
        dna_service: Optional[DNAService] = None,
        trait_service = None,
        blueprint_library = None,
        foundation_layer: Optional[FoundationLayer] = None,
        agent_manager: Optional[AgentManager] = None,
    ):
        self.dna = dna_service or DNAService()
        self.traits = trait_service or get_trait_service()
        self.blueprints = blueprint_library or get_blueprint_library()
        self.foundation = foundation_layer or get_foundation_layer()
        self.agent_manager = agent_manager  # Optional, for persistence

        logger.info("Genesis Service initialized")

    async def spawn_agent(self, request: SpawnAgentRequest) -> GenesisAgentResult:
        """
        Spawn new agent from blueprint.

        Args:
            request: Spawn request with blueprint ID and overrides

        Returns:
            Genesis agent result with details

        Raises:
            GenesisError: If blueprint not found
            EthicsViolationError: If ethics validation fails
        """
        logger.info(f"Spawning agent from blueprint: {request.blueprint_id}")

        # Set seed for determinism
        if request.seed is not None:
            random.seed(request.seed)
            np.random.seed(request.seed)
            logger.debug(f"Using deterministic seed: {request.seed}")

        # Get blueprint
        blueprint = self.blueprints.get(request.blueprint_id)
        if not blueprint:
            raise GenesisError(f"Blueprint not found: {request.blueprint_id}")

        # Generate agent ID
        agent_id = request.agent_id or self._generate_agent_id(blueprint.id)

        # Initialize traits from blueprint
        traits = TraitSet(traits={})
        for trait_id, default_value in blueprint.trait_profile.items():
            # Apply overrides if provided
            value = (
                request.trait_overrides.get(trait_id, default_value)
                if request.trait_overrides
                else default_value
            )
            traits.set(trait_id, value, source="genesis")

        logger.debug(f"Initialized {len(traits.traits)} traits for {agent_id}")

        # Validate with Foundation layer
        validation_context = AgentCreationContext(
            blueprint_id=request.blueprint_id,
            agent_id=agent_id,
            traits=traits.to_dict(),
            config=blueprint.base_config,
            tools=blueprint.tools,
            permissions=blueprint.permissions,
        )

        validation = await self.foundation.validate_agent_creation(validation_context)

        if not validation.allowed:
            raise EthicsViolationError(
                f"Agent creation blocked: {validation.violations}"
            )

        if validation.warnings:
            logger.warning(f"Validation warnings for {agent_id}: {validation.warnings}")

        # Create agent config
        agent_config = {
            **blueprint.base_config,
            "name": agent_id,
            "tools": blueprint.tools,
            "permissions": blueprint.permissions,
            "metadata": {
                "blueprint_id": request.blueprint_id,
                "genesis_version": "1.0.0",
                "spawn_time": datetime.utcnow().isoformat(),
                "seed": request.seed,
            },
        }

        # Create DNA snapshot
        dna_snapshot = self.dna.create_snapshot(
            CreateDNASnapshotRequest(
                agent_id=agent_id,
                dna=agent_config,
                traits=traits.to_dict(),
                reason=f"Genesis spawn from {request.blueprint_id}",
            )
        )

        logger.info(
            f"Created DNA snapshot {dna_snapshot.id} for agent {agent_id}"
        )

        # Register agent (if agent_manager available)
        if self.agent_manager:
            agent_definition = AgentDefinition(
                id=agent_id,
                name=agent_config["name"],
                role=agent_config.get("role", "GENERIC"),
                model=agent_config.get("model", "phi3"),
                system_prompt=agent_config.get("system_prompt", ""),
                temperature=agent_config.get("temperature", 0.7),
                max_tokens=agent_config.get("max_tokens", 2048),
                tools=agent_config["tools"],
                permissions=agent_config["permissions"],
                metadata=agent_config["metadata"],
            )

            self.agent_manager.repository.save_agent(agent_definition)
            logger.info(f"Registered agent {agent_id} in agent manager")

        return GenesisAgentResult(
            agent_id=agent_id,
            blueprint_id=request.blueprint_id,
            dna_snapshot_id=dna_snapshot.id,
            traits=traits.to_dict(),
            validation_warnings=validation.warnings,
            created_at=datetime.utcnow(),
        )

    async def evolve_agent(
        self, request: EvolveAgentRequest
    ) -> GenesisEvolutionResult:
        """
        Evolve agent based on fitness scores.

        Args:
            request: Evolution request with fitness metrics

        Returns:
            Evolution result with mutations and new snapshot

        Raises:
            GenesisError: If agent has no DNA history
            EthicsViolationError: If mutation validation fails
        """
        logger.info(f"Evolving agent: {request.agent_id}")

        # Get current DNA and traits
        history = self.dna.history(request.agent_id)
        if not history.snapshots:
            raise GenesisError(f"Agent has no DNA history: {request.agent_id}")

        current_snapshot = history.snapshots[-1]
        current_traits = TraitSet(
            traits={
                trait_id: self.traits.traits[trait_id]
                for trait_id in current_snapshot.traits.keys()
            }
        )

        # Calculate overall fitness
        blueprint_id = current_snapshot.dna.get("metadata", {}).get("blueprint_id")
        blueprint = self.blueprints.get(blueprint_id) if blueprint_id else None

        overall_fitness = self._calculate_fitness(request.fitness_scores, blueprint)
        logger.info(f"Calculated fitness score: {overall_fitness:.3f}")

        if not request.auto_mutate:
            logger.info("Auto-mutation disabled, returning fitness only")
            return GenesisEvolutionResult(
                agent_id=request.agent_id,
                fitness_score=overall_fitness,
                mutations_applied=[],
                new_snapshot_id=None,
            )

        # Determine mutations based on fitness
        proposed_mutations = self._suggest_mutations(
            current_traits=current_traits,
            fitness_scores=request.fitness_scores,
            blueprint=blueprint,
        )

        if not proposed_mutations:
            logger.info("No beneficial mutations identified")
            return GenesisEvolutionResult(
                agent_id=request.agent_id,
                fitness_score=overall_fitness,
                mutations_applied=[],
                new_snapshot_id=current_snapshot.id,
            )

        logger.info(f"Applying {len(proposed_mutations)} mutations")

        # Apply mutations
        new_traits = current_traits.model_copy()
        for mutation in proposed_mutations:
            new_traits.set(mutation["trait_id"], mutation["new_value"], source="evolution")

        # Validate mutations
        mutation_context = MutationContext(
            agent_id=request.agent_id,
            current_traits=current_traits.to_dict(),
            proposed_traits=new_traits.to_dict(),
            mutations=[m for m in proposed_mutations],
        )

        validation = await self.foundation.validate_mutation(mutation_context)

        if not validation.allowed:
            raise EthicsViolationError(f"Mutation blocked: {validation.violations}")

        # Create new DNA snapshot
        new_snapshot = self.dna.mutate(
            request.agent_id,
            MutateDNARequest(
                mutation={},  # No config changes in this version
                traits_delta=new_traits.to_dict(),
                reason=f"Evolution based on fitness={overall_fitness:.2f}",
            ),
        )

        # Update KARMA score
        await self.dna.update_karma(request.agent_id, overall_fitness)

        logger.info(
            f"Evolution complete: new snapshot {new_snapshot.id}, fitness {overall_fitness:.3f}"
        )

        return GenesisEvolutionResult(
            agent_id=request.agent_id,
            fitness_score=overall_fitness,
            mutations_applied=proposed_mutations,
            new_snapshot_id=new_snapshot.id,
            validation_warnings=validation.warnings,
        )

    async def reproduce_agents(
        self, request: ReproduceAgentsRequest
    ) -> GenesisReproductionResult:
        """
        Create child agent from two parents (genetic crossover).

        Args:
            request: Reproduction request with parent IDs

        Returns:
            Reproduction result with child details

        Raises:
            GenesisError: If parents not found or have no DNA
            EthicsViolationError: If validation fails
        """
        logger.info(
            f"Reproducing agents: {request.parent1_id} + {request.parent2_id}"
        )

        # Get parent DNA
        parent1_history = self.dna.history(request.parent1_id)
        parent2_history = self.dna.history(request.parent2_id)

        if not parent1_history.snapshots or not parent2_history.snapshots:
            raise GenesisError("One or both parents have no DNA history")

        parent1_snapshot = parent1_history.snapshots[-1]
        parent2_snapshot = parent2_history.snapshots[-1]

        parent1_traits = TraitSet(
            traits={
                trait_id: self.traits.traits[trait_id]
                for trait_id in parent1_snapshot.traits.keys()
            }
        )
        parent2_traits = TraitSet(
            traits={
                trait_id: self.traits.traits[trait_id]
                for trait_id in parent2_snapshot.traits.keys()
            }
        )

        # Crossover traits (50/50 mix with mutations)
        child_traits = self.traits.crossover_traits(
            parent1_traits, parent2_traits, mutation_rate=0.1
        )

        logger.info(f"Created child with {len(child_traits.traits)} traits")

        # Inherit from parent1's blueprint
        parent1_blueprint_id = parent1_snapshot.dna.get("metadata", {}).get(
            "blueprint_id"
        )
        blueprint = self.blueprints.get(parent1_blueprint_id)

        if not blueprint:
            raise GenesisError(f"Parent blueprint not found: {parent1_blueprint_id}")

        # Spawn child with inherited traits
        spawn_request = SpawnAgentRequest(
            blueprint_id=parent1_blueprint_id,
            agent_id=request.child_id,
            trait_overrides=child_traits.to_dict(),
        )

        child_result = await self.spawn_agent(spawn_request)

        return GenesisReproductionResult(
            child_id=child_result.agent_id,
            parent1_id=request.parent1_id,
            parent2_id=request.parent2_id,
            inherited_traits=child_result.traits,
            dna_snapshot_id=child_result.dna_snapshot_id,
            validation_warnings=child_result.validation_warnings,
            created_at=child_result.created_at,
        )

    # ========================================================================
    # INTERNAL HELPER METHODS
    # ========================================================================

    def _generate_agent_id(self, blueprint_id: str) -> str:
        """Generate unique agent ID."""
        short_uuid = uuid.uuid4().hex[:8]
        return f"{blueprint_id}_{short_uuid}"

    def _calculate_fitness(
        self, scores: Dict[str, float], blueprint: Optional[Any]
    ) -> float:
        """
        Calculate weighted fitness score.

        Args:
            scores: Fitness metrics (0-1)
            blueprint: Blueprint with fitness criteria

        Returns:
            Overall fitness score (0-1)
        """
        if not blueprint or not blueprint.fitness_criteria:
            # Simple average
            return sum(scores.values()) / len(scores) if scores else 0.0

        weighted_sum = 0.0
        total_weight = 0.0

        for metric, weight in blueprint.fitness_criteria.items():
            if metric in scores:
                weighted_sum += scores[metric] * weight
                total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _suggest_mutations(
        self,
        current_traits: TraitSet,
        fitness_scores: Dict[str, float],
        blueprint: Optional[Any],
    ) -> List[Dict[str, Any]]:
        """
        Suggest beneficial mutations based on fitness.

        Args:
            current_traits: Current trait set
            fitness_scores: Performance metrics
            blueprint: Blueprint with mutation settings

        Returns:
            List of suggested mutations
        """
        mutations = []

        # Example strategies (can be extended)

        # Strategy 1: If speed is low, increase speed_priority
        if fitness_scores.get("speed", 1.0) < 0.5:
            speed_trait = current_traits.get("performance.speed_priority")
            if speed_trait and speed_trait.value < 0.8:
                mutations.append(
                    {
                        "trait_id": "performance.speed_priority",
                        "old_value": speed_trait.value,
                        "new_value": min(speed_trait.value + 0.1, 1.0),
                        "reason": "Low speed performance detected",
                    }
                )

        # Strategy 2: If accuracy is low, increase accuracy_target
        if fitness_scores.get("accuracy", 1.0) < 0.7:
            accuracy_trait = current_traits.get("performance.accuracy_target")
            if accuracy_trait and accuracy_trait.value < 0.95:
                mutations.append(
                    {
                        "trait_id": "performance.accuracy_target",
                        "old_value": accuracy_trait.value,
                        "new_value": min(accuracy_trait.value + 0.05, 1.0),
                        "reason": "Low accuracy performance detected",
                    }
                )

        # Strategy 3: If task completion is low, increase proactiveness
        if fitness_scores.get("task_completion_rate", 1.0) < 0.6:
            proactive_trait = current_traits.get("behavioral.proactiveness")
            if proactive_trait and proactive_trait.value < 0.8:
                mutations.append(
                    {
                        "trait_id": "behavioral.proactiveness",
                        "old_value": proactive_trait.value,
                        "new_value": min(proactive_trait.value + 0.1, 1.0),
                        "reason": "Low task completion rate",
                    }
                )

        return mutations


# Singleton instance
_genesis_service: Optional[GenesisService] = None


def get_genesis_service() -> GenesisService:
    """Get singleton GenesisService instance."""
    global _genesis_service
    if _genesis_service is None:
        _genesis_service = GenesisService()
    return _genesis_service
