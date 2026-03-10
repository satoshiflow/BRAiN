"""
Genesis API Routes

REST API for agent spawning, evolution, and reproduction.
"""

from typing import List

from fastapi import APIRouter, HTTPException, Depends
from loguru import logger

from app.core.auth_deps import (
    require_auth,
    require_role,
    SystemRole,
    Principal,
)
from app.modules.genesis.blueprints import get_blueprint_library
from app.modules.genesis.blueprints.schemas import AgentBlueprint
from app.modules.genesis.core import (
    EvolveAgentRequest,
    GenesisAgentResult,
    GenesisEvolutionResult,
    GenesisReproductionResult,
    ReproduceAgentsRequest,
    SpawnAgentRequest,
    get_genesis_service,
)
from app.modules.genesis.core.exceptions import (
    EthicsViolationError,
    GenesisError,
)
from app.modules.genesis.foundation import (
    FoundationValidationResult,
    get_foundation_layer,
)
from app.modules.genesis.foundation.schemas import AgentCreationContext
from app.modules.genesis.traits import get_trait_service
from app.modules.genesis.traits.schemas import TraitDefinition

router = APIRouter(prefix="/api/genesis", tags=["genesis"])


# ============================================================================
# AGENT SPAWNING
# ============================================================================


@router.post("/spawn", response_model=GenesisAgentResult)
async def spawn_agent(
    request: SpawnAgentRequest,
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN)),
):
    """
    Spawn new agent from blueprint.

    Creates a new agent with traits initialized from blueprint profile.
    Supports trait overrides and deterministic spawning via seed.

    **Requires:** OPERATOR or ADMIN role

    **Example:**
    ```json
    {
      "blueprint_id": "fleet_coordinator_v1",
      "agent_id": "fleet_alpha",
      "trait_overrides": {
        "performance.speed_priority": 0.8
      },
      "seed": 42
    }
    ```
    """
    try:
        genesis = get_genesis_service()
        result = await genesis.spawn_agent(request)

        logger.info(f"Spawned agent {result.agent_id} from {request.blueprint_id} by {principal.principal_id}")
        return result

    except EthicsViolationError as e:
        raise HTTPException(status_code=403, detail=f"Ethics violation: {str(e)}")
    except GenesisError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error spawning agent: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/validate", response_model=FoundationValidationResult)
async def validate_agent_config(
    context: AgentCreationContext,
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN)),
):
    """
    Validate agent configuration without creating.

    Dry-run validation to check if agent configuration passes ethics checks.

    **Requires:** OPERATOR or ADMIN role

    **Example:**
    ```json
    {
      "blueprint_id": "fleet_coordinator_v1",
      "agent_id": "test_agent",
      "traits": {
        "ethical.safety_priority": 0.5
      },
      "config": {},
      "tools": [],
      "permissions": []
    }
    ```
    """
    try:
        foundation = get_foundation_layer()
        result = await foundation.validate_agent_creation(context)
        logger.debug(f"Validated agent config by {principal.principal_id}")
        return result

    except Exception as e:
        logger.error(f"Error validating agent config: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# AGENT EVOLUTION
# ============================================================================


@router.post("/evolve", response_model=GenesisEvolutionResult)
async def evolve_agent(
    request: EvolveAgentRequest,
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN)),
):
    """
    Evolve agent based on fitness scores.

    Applies beneficial mutations to improve agent performance.
    Mutations are validated by Foundation layer before application.

    **Requires:** OPERATOR or ADMIN role

    **Example:**
    ```json
    {
      "agent_id": "fleet_alpha",
      "fitness_scores": {
        "task_completion_rate": 0.85,
        "average_task_time": 0.75,
        "safety_incidents": 1.0
      },
      "auto_mutate": true
    }
    ```
    """
    try:
        genesis = get_genesis_service()
        result = await genesis.evolve_agent(request)

        logger.info(
            f"Evolved agent {request.agent_id} by {principal.principal_id}, fitness: {result.fitness_score:.3f}"
        )
        return result

    except EthicsViolationError as e:
        raise HTTPException(status_code=403, detail=f"Ethics violation: {str(e)}")
    except GenesisError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error evolving agent: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# AGENT REPRODUCTION
# ============================================================================


@router.post("/reproduce", response_model=GenesisReproductionResult)
async def reproduce_agents(
    request: ReproduceAgentsRequest,
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN)),
):
    """
    Create child agent from two parents.

    Genetic crossover combines traits from both parents with mutations.

    **Requires:** OPERATOR or ADMIN role

    **Example:**
    ```json
    {
      "parent1_id": "fleet_alpha",
      "parent2_id": "fleet_beta",
      "child_id": "fleet_gamma"
    }
    ```
    """
    try:
        genesis = get_genesis_service()
        result = await genesis.reproduce_agents(request)

        logger.info(
            f"Reproduced agent {result.child_id} from {request.parent1_id} + {request.parent2_id} by {principal.principal_id}"
        )
        return result

    except EthicsViolationError as e:
        raise HTTPException(status_code=403, detail=f"Ethics violation: {str(e)}")
    except GenesisError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error reproducing agents: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# BLUEPRINTS
# ============================================================================


@router.get("/blueprints", response_model=List[AgentBlueprint])
async def list_blueprints(
    tag: str = None,
    allow_mutations: bool = None,
    principal: Principal = Depends(require_auth),
):
    """
    List all available blueprints.

    Optionally filter by tag or mutation allowance.

    **Requires:** Authentication

    **Query Parameters:**
    - `tag`: Filter by tag (e.g., "fleet", "safety")
    - `allow_mutations`: Filter by mutation allowance (true/false)
    """
    try:
        library = get_blueprint_library()
        blueprints = library.search(tag=tag, allow_mutations=allow_mutations)
        logger.debug(f"Listed blueprints by {principal.principal_id}")
        return blueprints

    except Exception as e:
        logger.error(f"Error listing blueprints: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/blueprints/{blueprint_id}", response_model=AgentBlueprint)
async def get_blueprint(
    blueprint_id: str,
    principal: Principal = Depends(require_auth),
):
    """
    Get blueprint by ID.

    **Requires:** Authentication
    """
    library = get_blueprint_library()
    blueprint = library.get(blueprint_id)

    if not blueprint:
        raise HTTPException(status_code=404, detail="Blueprint not found")

    logger.debug(f"Retrieved blueprint {blueprint_id} by {principal.principal_id}")
    return blueprint


@router.get("/blueprints/summary")
async def get_blueprints_summary(
    principal: Principal = Depends(require_auth),
):
    """
    Get blueprint library summary statistics.

    **Requires:** Authentication
    """
    library = get_blueprint_library()
    logger.debug(f"Retrieved blueprints summary by {principal.principal_id}")
    return library.get_summary()


# ============================================================================
# TRAITS
# ============================================================================


@router.get("/traits", response_model=List[TraitDefinition])
async def list_traits(
    category: str = None,
    principal: Principal = Depends(require_auth),
):
    """
    List all trait definitions.

    Optionally filter by category.

    **Requires:** Authentication

    **Query Parameters:**
    - `category`: Filter by category (cognitive, ethical, performance, etc.)
    """
    try:
        trait_service = get_trait_service()
        definitions = trait_service.get_all_definitions()

        if category:
            from app.modules.genesis.traits.schemas import TraitCategory

            try:
                cat = TraitCategory(category)
                definitions = [d for d in definitions if d.category == cat]
            except ValueError:
                raise HTTPException(
                    status_code=400, detail=f"Invalid category: {category}"
                )

        logger.debug(f"Listed traits by {principal.principal_id}")
        return definitions

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing traits: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/traits/{trait_id}", response_model=TraitDefinition)
async def get_trait(
    trait_id: str,
    principal: Principal = Depends(require_auth),
):
    """
    Get trait definition by ID.

    **Requires:** Authentication
    """
    trait_service = get_trait_service()
    definition = trait_service.get_definition(trait_id)

    if not definition:
        raise HTTPException(status_code=404, detail="Trait not found")

    logger.debug(f"Retrieved trait {trait_id} by {principal.principal_id}")
    return definition


# ============================================================================
# SYSTEM INFO
# ============================================================================


@router.get("/info")
async def get_genesis_info(
    principal: Principal = Depends(require_auth),
):
    """
    Get Genesis system information.

    **Requires:** Authentication
    """
    library = get_blueprint_library()
    trait_service = get_trait_service()

    logger.debug(f"Retrieved genesis info by {principal.principal_id}")
    return {
        "name": "BRAIN Genesis Agent System",
        "version": "1.0.0",
        "description": "Autonomous agent generation with DNA-driven evolution",
        "blueprints": {
            "total": library.count(),
            "builtin": len(
                [bp for bp in library.list_all() if bp.author == "system"]
            ),
        },
        "traits": {
            "total": len(trait_service.get_all_definitions()),
            "categories": len(
                set(d.category for d in trait_service.get_all_definitions())
            ),
        },
        "features": [
            "Deterministic agent spawning",
            "DNA-driven evolution",
            "Genetic crossover",
            "Ethics validation",
            "Blueprint templates",
            "Trait-based characteristics",
        ],
    }
