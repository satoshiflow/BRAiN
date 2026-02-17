# BRAIN Genesis Agent System - Design Document

**Version:** 1.0.0
**Date:** 2025-12-24
**Status:** Implementation Ready

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Core Components](#core-components)
4. [Integration with Existing Systems](#integration-with-existing-systems)
5. [Implementation Plan](#implementation-plan)
6. [Security & Ethics](#security--ethics)
7. [API Specification](#api-specification)

---

## Executive Summary

The **Genesis Agent System** provides autonomous agent generation with DNA-driven evolution, ethical constraints, and deterministic spawning. It builds on BRAiN's existing infrastructure:

- **DNA Module** - Version-controlled snapshots and mutations
- **Policy Engine** - Rule-based governance
- **Immune System** - Threat detection and health monitoring
- **BaseAgent** - Type-safe agent foundation

### Key Innovations

1. **Trait-Based Evolution** - Agents have inheritable characteristics
2. **Blueprint Templates** - Predefined agent archetypes
3. **Foundation Layer** - Ethics validation at creation and mutation
4. **KARMA Scoring** - Performance and ethics metrics
5. **Deterministic Spawning** - Reproducible agent generation from seed
6. **Auto-Evolution** - Performance-triggered mutations

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    GENESIS SYSTEM (New)                          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ GenesisCore  │  │ TraitSystem  │  │ Foundation   │          │
│  │              │  │              │  │ Layer        │          │
│  │ - spawn()    │  │ - inherit()  │  │ - validate() │          │
│  │ - evolve()   │  │ - mutate()   │  │ - enforce()  │          │
│  │ - reproduce()│  │ - score()    │  │ - audit()    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                  │                   │
└─────────┼─────────────────┼──────────────────┼───────────────────┘
          │                 │                  │
          ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                 EXISTING BRAIN SYSTEMS                           │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   DNA    │  │  Policy  │  │  Immune  │  │  KARMA   │       │
│  │  Module  │  │  Engine  │  │  System  │  │ (Phase2) │       │
│  │          │  │          │  │          │  │          │       │
│  │ Snapshots│  │  Rules   │  │  Events  │  │ Scoring  │       │
│  │ Mutations│  │  Effects │  │ Threats  │  │ Reason   │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │             │              │             │              │
└───────┼─────────────┼──────────────┼─────────────┼──────────────┘
        │             │              │             │
        ▼             ▼              ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT LAYER                                   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ BaseAgent (LLM + Tools + Permissions + Traits)           │  │
│  └──┬───────────────────────────────────────────────────┬───┘  │
│     │                                                     │      │
│  ┌──▼──────┐  ┌──────────┐  ┌──────────┐  ┌────────────▼───┐  │
│  │ Fleet   │  │ Safety   │  │Navigation│  │ Custom Genesis │  │
│  │ Agent   │  │ Agent    │  │ Agent    │  │ Agents         │  │
│  └─────────┘  └──────────┘  └──────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Trait System

**Purpose:** Define inheritable agent characteristics

**Location:** `backend/app/modules/genesis/traits/`

#### Data Models

```python
class TraitCategory(str, Enum):
    COGNITIVE = "cognitive"       # Intelligence, reasoning
    BEHAVIORAL = "behavioral"     # Response patterns, decision-making
    PERFORMANCE = "performance"   # Speed, accuracy, efficiency
    ETHICAL = "ethical"           # Alignment, safety, compliance
    SOCIAL = "social"             # Communication, collaboration
    TECHNICAL = "technical"       # Skills, capabilities

class TraitType(str, Enum):
    FLOAT = "float"    # 0.0 - 1.0 normalized
    INT = "int"        # Discrete values
    ENUM = "enum"      # Categorical
    BOOL = "bool"      # Binary

class TraitDefinition(BaseModel):
    """Defines a trait that agents can have."""
    id: str                          # e.g., "cognitive.reasoning_depth"
    name: str                        # Human-readable
    category: TraitCategory
    type: TraitType
    default_value: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[Any]] = None  # For ENUM
    inheritable: bool = True         # Can be passed to offspring
    mutable: bool = True             # Can evolve
    ethics_critical: bool = False    # Requires Foundation validation
    description: str

class AgentTrait(BaseModel):
    """An agent's specific trait value."""
    trait_id: str                    # References TraitDefinition.id
    value: Any
    source: str = "genesis"          # genesis|mutation|inheritance
    confidence: float = 1.0          # 0.0-1.0 strength of trait
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class TraitSet(BaseModel):
    """Collection of traits for an agent."""
    traits: Dict[str, AgentTrait]    # trait_id -> AgentTrait

    def get(self, trait_id: str) -> Optional[AgentTrait]:
        return self.traits.get(trait_id)

    def set(self, trait_id: str, value: Any, source: str = "mutation"):
        """Update or add trait."""
        pass

    def inherit(self, parent_traits: "TraitSet", mutation_rate: float = 0.1):
        """Inherit traits from parent with optional mutation."""
        pass
```

#### Built-in Trait Definitions

```python
# backend/app/modules/genesis/traits/definitions.py

COGNITIVE_TRAITS = [
    TraitDefinition(
        id="cognitive.reasoning_depth",
        name="Reasoning Depth",
        category=TraitCategory.COGNITIVE,
        type=TraitType.FLOAT,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Depth of logical reasoning (0=shallow, 1=deep)"
    ),
    TraitDefinition(
        id="cognitive.creativity",
        name="Creativity",
        category=TraitCategory.COGNITIVE,
        type=TraitType.FLOAT,
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        description="Novel solution generation ability"
    ),
]

ETHICAL_TRAITS = [
    TraitDefinition(
        id="ethical.safety_priority",
        name="Safety Priority",
        category=TraitCategory.ETHICAL,
        type=TraitType.FLOAT,
        default_value=0.9,
        min_value=0.7,  # Minimum safety threshold
        max_value=1.0,
        inheritable=True,
        mutable=False,  # Safety is immutable
        ethics_critical=True,
        description="Priority given to safety constraints"
    ),
    TraitDefinition(
        id="ethical.compliance_strictness",
        name="Compliance Strictness",
        category=TraitCategory.ETHICAL,
        type=TraitType.FLOAT,
        default_value=0.8,
        min_value=0.5,
        max_value=1.0,
        ethics_critical=True,
        description="Adherence to policy rules"
    ),
]

PERFORMANCE_TRAITS = [
    TraitDefinition(
        id="performance.speed_priority",
        name="Speed Priority",
        category=TraitCategory.PERFORMANCE,
        type=TraitType.FLOAT,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Preference for speed over accuracy (0=accuracy, 1=speed)"
    ),
    TraitDefinition(
        id="performance.energy_efficiency",
        name="Energy Efficiency",
        category=TraitCategory.PERFORMANCE,
        type=TraitType.FLOAT,
        default_value=0.7,
        min_value=0.0,
        max_value=1.0,
        description="Conservation of computational resources"
    ),
]

# ... more trait categories
```

#### Trait Service

```python
# backend/app/modules/genesis/traits/service.py

class TraitService:
    """Manages trait definitions and validation."""

    def __init__(self):
        self.definitions: Dict[str, TraitDefinition] = {}
        self._load_builtin_traits()

    def _load_builtin_traits(self):
        """Load built-in trait definitions."""
        for trait in COGNITIVE_TRAITS + ETHICAL_TRAITS + PERFORMANCE_TRAITS:
            self.definitions[trait.id] = trait

    def get_definition(self, trait_id: str) -> Optional[TraitDefinition]:
        """Get trait definition by ID."""
        return self.definitions.get(trait_id)

    def validate_trait_value(self, trait_id: str, value: Any) -> bool:
        """Validate trait value against definition."""
        definition = self.get_definition(trait_id)
        if not definition:
            return False

        # Type check
        if definition.type == TraitType.FLOAT:
            if not isinstance(value, (float, int)):
                return False
            if definition.min_value is not None and value < definition.min_value:
                return False
            if definition.max_value is not None and value > definition.max_value:
                return False

        # ... other type validations
        return True

    def mutate_trait(
        self,
        trait: AgentTrait,
        mutation_strength: float = 0.1
    ) -> AgentTrait:
        """Apply controlled mutation to trait."""
        definition = self.get_definition(trait.trait_id)

        if not definition or not definition.mutable:
            return trait  # Immutable trait

        if definition.type == TraitType.FLOAT:
            # Gaussian mutation
            import random
            delta = random.gauss(0, mutation_strength)
            new_value = trait.value + delta

            # Clamp to bounds
            if definition.min_value is not None:
                new_value = max(new_value, definition.min_value)
            if definition.max_value is not None:
                new_value = min(new_value, definition.max_value)

            return AgentTrait(
                trait_id=trait.trait_id,
                value=new_value,
                source="mutation",
                confidence=trait.confidence * 0.95  # Slight confidence decay
            )

        # ... other mutation strategies
        return trait

    def inherit_traits(
        self,
        parent_traits: TraitSet,
        mutation_rate: float = 0.1
    ) -> TraitSet:
        """Create child trait set from parent with mutations."""
        child_traits = TraitSet(traits={})

        for trait_id, parent_trait in parent_traits.traits.items():
            definition = self.get_definition(trait_id)

            if not definition or not definition.inheritable:
                continue

            # Inherit with possible mutation
            if random.random() < mutation_rate:
                child_trait = self.mutate_trait(parent_trait)
            else:
                child_trait = parent_trait.model_copy()
                child_trait.source = "inheritance"

            child_traits.traits[trait_id] = child_trait

        return child_traits
```

---

### 2. Blueprint System

**Purpose:** Predefined agent templates with trait profiles

**Location:** `backend/app/modules/genesis/blueprints/`

#### Blueprint Model

```python
# backend/app/modules/genesis/blueprints/schemas.py

class BlueprintCapability(BaseModel):
    """A capability that a blueprint provides."""
    id: str
    name: str
    description: str
    required_tools: List[str] = []
    required_permissions: List[str] = []

class AgentBlueprint(BaseModel):
    """Complete agent template definition."""

    # Identity
    id: str                              # e.g., "fleet_coordinator_v1"
    name: str                            # Human-readable
    version: str = "1.0.0"
    description: str

    # Configuration
    base_config: Dict[str, Any]          # AgentConfig fields
    trait_profile: Dict[str, Any]        # Default trait values

    # Capabilities
    capabilities: List[BlueprintCapability] = []
    tools: List[str] = []
    permissions: List[str] = []

    # Evolution
    allow_mutations: bool = True
    mutation_rate: float = 0.1
    fitness_criteria: Dict[str, float] = {}  # metric -> weight

    # Ethics
    ethics_constraints: Dict[str, Any] = {}
    required_policy_compliance: List[str] = []  # Policy IDs

    # Metadata
    author: str = "system"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = []

class BlueprintLibrary:
    """Registry of available blueprints."""

    def __init__(self):
        self.blueprints: Dict[str, AgentBlueprint] = {}
        self._load_builtin_blueprints()

    def _load_builtin_blueprints(self):
        """Load built-in blueprint definitions."""
        # Import from blueprint files
        from .builtin import (
            FLEET_COORDINATOR_BLUEPRINT,
            SAFETY_MONITOR_BLUEPRINT,
            NAVIGATION_PLANNER_BLUEPRINT,
            CODE_SPECIALIST_BLUEPRINT,
            OPS_SPECIALIST_BLUEPRINT
        )

        for blueprint in [
            FLEET_COORDINATOR_BLUEPRINT,
            SAFETY_MONITOR_BLUEPRINT,
            NAVIGATION_PLANNER_BLUEPRINT,
            CODE_SPECIALIST_BLUEPRINT,
            OPS_SPECIALIST_BLUEPRINT
        ]:
            self.blueprints[blueprint.id] = blueprint

    def get(self, blueprint_id: str) -> Optional[AgentBlueprint]:
        return self.blueprints.get(blueprint_id)

    def register(self, blueprint: AgentBlueprint):
        """Register custom blueprint."""
        self.blueprints[blueprint.id] = blueprint

    def list_all(self) -> List[AgentBlueprint]:
        return list(self.blueprints.values())
```

#### Built-in Blueprints

```python
# backend/app/modules/genesis/blueprints/builtin/fleet_coordinator.py

FLEET_COORDINATOR_BLUEPRINT = AgentBlueprint(
    id="fleet_coordinator_v1",
    name="Fleet Coordinator",
    version="1.0.0",
    description="Multi-robot fleet coordination and task distribution",

    base_config={
        "role": "FLEET_COORDINATOR",
        "model": "phi3",
        "temperature": 0.3,  # Low for consistent decisions
        "max_tokens": 2048,
        "system_prompt": "You are a fleet coordinator...",
    },

    trait_profile={
        "cognitive.reasoning_depth": 0.7,
        "performance.speed_priority": 0.6,
        "ethical.safety_priority": 0.9,
        "social.coordination_skill": 0.8,
        "technical.fleet_management": 0.9,
    },

    capabilities=[
        BlueprintCapability(
            id="task_assignment",
            name="Task Assignment",
            description="Assign tasks to optimal robots",
            required_tools=["assign_task"],
            required_permissions=["FLEET_ASSIGN_TASK"]
        ),
        BlueprintCapability(
            id="load_balancing",
            name="Load Balancing",
            description="Balance workload across fleet",
            required_tools=["balance_load"],
            required_permissions=["FLEET_REBALANCE"]
        ),
    ],

    tools=["assign_task", "balance_load", "coordinate_movement", "get_fleet_status"],
    permissions=["FLEET_ASSIGN_TASK", "FLEET_REBALANCE", "FLEET_STATUS"],

    allow_mutations=True,
    mutation_rate=0.05,  # Conservative
    fitness_criteria={
        "task_completion_rate": 0.4,
        "average_task_time": 0.3,
        "robot_utilization": 0.2,
        "safety_incidents": 0.1,  # Minimize
    },

    ethics_constraints={
        "max_robot_load": 10,
        "min_safety_margin": 0.8,
    },
    required_policy_compliance=["fleet_safety_v1"],

    author="system",
    tags=["fleet", "coordination", "ryr"]
)
```

---

### 3. Foundation Layer

**Purpose:** Ethics validation and safety enforcement

**Location:** `backend/app/modules/genesis/foundation/`

#### Foundation Service

```python
# backend/app/modules/genesis/foundation/service.py

class FoundationLayer:
    """Ethics and safety validation layer for Genesis."""

    def __init__(self, policy_engine, immune_service):
        self.policy_engine = policy_engine
        self.immune_service = immune_service
        self.ethics_rules: List[EthicsRule] = []
        self._load_ethics_rules()

    def _load_ethics_rules(self):
        """Load core ethics rules."""
        self.ethics_rules = [
            EthicsRule(
                id="safety_minimum",
                description="Agents must have minimum safety priority",
                validator=lambda traits: traits.get("ethical.safety_priority").value >= 0.7,
                severity="CRITICAL",
                action="BLOCK"
            ),
            EthicsRule(
                id="no_harmful_capabilities",
                description="Agents cannot have harmful tool combinations",
                validator=self._validate_tool_safety,
                severity="CRITICAL",
                action="BLOCK"
            ),
            # ... more rules
        ]

    async def validate_agent_creation(
        self,
        blueprint: AgentBlueprint,
        traits: TraitSet,
        config: Dict[str, Any]
    ) -> FoundationValidationResult:
        """Validate agent before creation."""

        violations = []
        warnings = []

        # Check ethics rules
        for rule in self.ethics_rules:
            try:
                if not rule.validator(traits):
                    if rule.action == "BLOCK":
                        violations.append(f"Ethics violation: {rule.description}")
                    else:
                        warnings.append(f"Ethics warning: {rule.description}")
            except Exception as e:
                violations.append(f"Rule validation error: {str(e)}")

        # Check policy compliance
        for policy_id in blueprint.required_policy_compliance:
            # Validate against policy engine
            pass

        # Check immune system for threats
        if self.immune_service:
            health = await self.immune_service.health_summary(minutes=60)
            if health.critical_issues > 0:
                warnings.append("System under threat - careful agent creation advised")

        return FoundationValidationResult(
            allowed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            timestamp=datetime.utcnow()
        )

    async def validate_mutation(
        self,
        agent_id: str,
        current_traits: TraitSet,
        proposed_traits: TraitSet
    ) -> FoundationValidationResult:
        """Validate mutation before application."""

        violations = []

        # Check for ethics-critical trait violations
        for trait_id, new_trait in proposed_traits.traits.items():
            current_trait = current_traits.get(trait_id)

            if current_trait and current_trait.ethics_critical:
                # Ethics-critical traits have strict bounds
                definition = trait_service.get_definition(trait_id)
                if not trait_service.validate_trait_value(trait_id, new_trait.value):
                    violations.append(
                        f"Ethics violation: {trait_id} outside allowed range"
                    )

        return FoundationValidationResult(
            allowed=len(violations) == 0,
            violations=violations,
            warnings=[],
            timestamp=datetime.utcnow()
        )

    def _validate_tool_safety(self, traits: TraitSet) -> bool:
        """Check for dangerous tool combinations."""
        # Example: High-power tools + low safety priority = dangerous
        # Implement tool safety matrix
        return True

class EthicsRule(BaseModel):
    id: str
    description: str
    validator: callable  # (TraitSet) -> bool
    severity: str = "WARNING"  # WARNING|CRITICAL
    action: str = "WARN"  # WARN|BLOCK

class FoundationValidationResult(BaseModel):
    allowed: bool
    violations: List[str]
    warnings: List[str]
    timestamp: datetime
```

---

### 4. Genesis Core Service

**Purpose:** Agent spawning, evolution, and lifecycle management

**Location:** `backend/app/modules/genesis/core/`

#### Genesis Service

```python
# backend/app/modules/genesis/core/service.py

class GenesisService:
    """Core Genesis agent creation and evolution service."""

    def __init__(
        self,
        dna_service,
        trait_service,
        blueprint_library,
        foundation_layer,
        agent_manager
    ):
        self.dna = dna_service
        self.traits = trait_service
        self.blueprints = blueprint_library
        self.foundation = foundation_layer
        self.agent_manager = agent_manager

    async def spawn_agent(
        self,
        blueprint_id: str,
        agent_id: Optional[str] = None,
        trait_overrides: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None
    ) -> GenesisAgentResult:
        """
        Spawn new agent from blueprint.

        Args:
            blueprint_id: Blueprint to use
            agent_id: Optional explicit agent ID
            trait_overrides: Override default traits
            seed: Random seed for deterministic spawning

        Returns:
            GenesisAgentResult with agent details
        """

        # Set seed for determinism
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        # Get blueprint
        blueprint = self.blueprints.get(blueprint_id)
        if not blueprint:
            raise ValueError(f"Blueprint not found: {blueprint_id}")

        # Generate agent ID
        if not agent_id:
            agent_id = f"{blueprint.id}_{uuid.uuid4().hex[:8]}"

        # Initialize traits from blueprint
        traits = TraitSet(traits={})
        for trait_id, default_value in blueprint.trait_profile.items():
            value = trait_overrides.get(trait_id, default_value) if trait_overrides else default_value
            traits.set(trait_id, value, source="genesis")

        # Validate with Foundation layer
        validation = await self.foundation.validate_agent_creation(
            blueprint=blueprint,
            traits=traits,
            config=blueprint.base_config
        )

        if not validation.allowed:
            raise EthicsViolationError(
                f"Agent creation blocked: {validation.violations}"
            )

        # Create agent config
        agent_config = {
            **blueprint.base_config,
            "name": agent_id,
            "tools": blueprint.tools,
            "permissions": blueprint.permissions,
        }

        # Create DNA snapshot
        dna_snapshot = self.dna.create_snapshot(
            CreateDNASnapshotRequest(
                agent_id=agent_id,
                dna=agent_config,
                traits=traits.dict(),
                reason=f"Genesis spawn from {blueprint_id}"
            )
        )

        # Register agent
        agent_definition = AgentDefinition(
            id=agent_id,
            name=agent_config["name"],
            role=agent_config["role"],
            model=agent_config["model"],
            system_prompt=agent_config["system_prompt"],
            temperature=agent_config["temperature"],
            max_tokens=agent_config["max_tokens"],
            tools=agent_config["tools"],
            permissions=agent_config["permissions"],
            metadata={
                "blueprint_id": blueprint_id,
                "genesis_version": "1.0.0",
                "spawn_time": datetime.utcnow().isoformat(),
                "seed": seed,
            }
        )

        saved_agent = self.agent_manager.repository.save_agent(agent_definition)

        # Log immune event
        await self.foundation.immune_service.publish_event(
            ImmuneEvent(
                agent_id=agent_id,
                module="genesis",
                severity=ImmuneSeverity.INFO,
                type=ImmuneEventType.SELF_HEALING_ACTION,
                message=f"New agent spawned from {blueprint_id}",
                meta={"blueprint_id": blueprint_id, "seed": seed}
            )
        )

        return GenesisAgentResult(
            agent_id=agent_id,
            blueprint_id=blueprint_id,
            dna_snapshot_id=dna_snapshot.id,
            traits=traits,
            validation_warnings=validation.warnings,
            created_at=datetime.utcnow()
        )

    async def evolve_agent(
        self,
        agent_id: str,
        fitness_scores: Dict[str, float],
        auto_mutate: bool = True
    ) -> GenesisEvolutionResult:
        """
        Evolve agent based on fitness scores.

        Args:
            agent_id: Agent to evolve
            fitness_scores: Performance metrics (name -> score 0-1)
            auto_mutate: Automatically apply beneficial mutations

        Returns:
            Evolution result with new DNA snapshot
        """

        # Get current DNA and traits
        history = self.dna.history(agent_id)
        if not history.snapshots:
            raise ValueError(f"Agent has no DNA history: {agent_id}")

        current_snapshot = history.snapshots[-1]
        current_traits = TraitSet(**current_snapshot.traits)

        # Calculate overall fitness
        blueprint_id = current_snapshot.dna.get("metadata", {}).get("blueprint_id")
        blueprint = self.blueprints.get(blueprint_id) if blueprint_id else None

        overall_fitness = self._calculate_fitness(fitness_scores, blueprint)

        if not auto_mutate:
            return GenesisEvolutionResult(
                agent_id=agent_id,
                fitness_score=overall_fitness,
                mutations_applied=[],
                new_snapshot_id=None
            )

        # Determine mutations based on fitness
        proposed_mutations = self._suggest_mutations(
            current_traits=current_traits,
            fitness_scores=fitness_scores,
            blueprint=blueprint
        )

        if not proposed_mutations:
            return GenesisEvolutionResult(
                agent_id=agent_id,
                fitness_score=overall_fitness,
                mutations_applied=[],
                new_snapshot_id=current_snapshot.id
            )

        # Apply mutations
        new_traits = current_traits.model_copy()
        for mutation in proposed_mutations:
            new_traits.set(
                mutation.trait_id,
                mutation.new_value,
                source="evolution"
            )

        # Validate mutations
        validation = await self.foundation.validate_mutation(
            agent_id=agent_id,
            current_traits=current_traits,
            proposed_traits=new_traits
        )

        if not validation.allowed:
            raise EthicsViolationError(
                f"Mutation blocked: {validation.violations}"
            )

        # Create new DNA snapshot
        new_snapshot = self.dna.mutate(
            agent_id,
            MutateDNARequest(
                mutation={},  # No config changes
                traits_delta=new_traits.dict(),
                reason=f"Evolution based on fitness={overall_fitness:.2f}"
            )
        )

        # Update KARMA score
        await self.dna.update_karma(agent_id, overall_fitness)

        return GenesisEvolutionResult(
            agent_id=agent_id,
            fitness_score=overall_fitness,
            mutations_applied=[m.dict() for m in proposed_mutations],
            new_snapshot_id=new_snapshot.id,
            validation_warnings=validation.warnings
        )

    async def reproduce_agents(
        self,
        parent1_id: str,
        parent2_id: str,
        child_id: Optional[str] = None
    ) -> GenesisAgentResult:
        """
        Create child agent from two parents (genetic crossover).

        Args:
            parent1_id: First parent agent
            parent2_id: Second parent agent
            child_id: Optional explicit child ID

        Returns:
            New agent with inherited traits
        """

        # Get parent DNA
        parent1_history = self.dna.history(parent1_id)
        parent2_history = self.dna.history(parent2_id)

        parent1_traits = TraitSet(**parent1_history.snapshots[-1].traits)
        parent2_traits = TraitSet(**parent2_history.snapshots[-1].traits)

        # Crossover traits (50/50 mix with mutations)
        child_traits = self._crossover_traits(parent1_traits, parent2_traits)

        # Inherit from parent1's blueprint
        parent1_blueprint_id = parent1_history.snapshots[-1].dna.get("metadata", {}).get("blueprint_id")
        blueprint = self.blueprints.get(parent1_blueprint_id)

        if not blueprint:
            raise ValueError(f"Parent blueprint not found: {parent1_blueprint_id}")

        # Spawn child with inherited traits
        return await self.spawn_agent(
            blueprint_id=parent1_blueprint_id,
            agent_id=child_id,
            trait_overrides=child_traits.dict()
        )

    def _calculate_fitness(
        self,
        scores: Dict[str, float],
        blueprint: Optional[AgentBlueprint]
    ) -> float:
        """Calculate weighted fitness score."""
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
        blueprint: Optional[AgentBlueprint]
    ) -> List[TraitMutation]:
        """Suggest beneficial mutations based on fitness."""
        mutations = []

        # Example: If speed is low and speed_priority trait exists
        if fitness_scores.get("speed", 0) < 0.5:
            speed_trait = current_traits.get("performance.speed_priority")
            if speed_trait and speed_trait.value < 0.8:
                mutations.append(
                    TraitMutation(
                        trait_id="performance.speed_priority",
                        old_value=speed_trait.value,
                        new_value=min(speed_trait.value + 0.1, 1.0),
                        reason="Low speed performance"
                    )
                )

        # More sophisticated mutation logic...
        return mutations

    def _crossover_traits(
        self,
        parent1: TraitSet,
        parent2: TraitSet
    ) -> TraitSet:
        """Crossover traits from two parents."""
        child_traits = TraitSet(traits={})

        all_trait_ids = set(parent1.traits.keys()) | set(parent2.traits.keys())

        for trait_id in all_trait_ids:
            # Random selection from parents
            if random.random() < 0.5 and trait_id in parent1.traits:
                child_traits.traits[trait_id] = parent1.traits[trait_id].model_copy()
            elif trait_id in parent2.traits:
                child_traits.traits[trait_id] = parent2.traits[trait_id].model_copy()

            # Apply mutation
            if random.random() < 0.1:  # 10% mutation rate
                child_traits.traits[trait_id] = self.traits.mutate_trait(
                    child_traits.traits[trait_id]
                )

        return child_traits

class TraitMutation(BaseModel):
    trait_id: str
    old_value: Any
    new_value: Any
    reason: str

class GenesisAgentResult(BaseModel):
    agent_id: str
    blueprint_id: str
    dna_snapshot_id: int
    traits: TraitSet
    validation_warnings: List[str]
    created_at: datetime

class GenesisEvolutionResult(BaseModel):
    agent_id: str
    fitness_score: float
    mutations_applied: List[Dict[str, Any]]
    new_snapshot_id: Optional[int]
    validation_warnings: List[str] = []
```

---

### 5. KARMA Integration

**Location:** `backend/app/modules/karma/` (existing, enhance for Genesis)

#### Enhanced KARMA Service

```python
# backend/app/modules/karma/service.py

class KarmaService:
    """Enhanced KARMA with Genesis integration."""

    async def evaluate_agent_fitness(
        self,
        agent_id: str,
        time_window_hours: int = 24
    ) -> Dict[str, float]:
        """
        Evaluate agent fitness across multiple dimensions.

        Returns:
            Dictionary of fitness scores (0-1 normalized)
        """

        # Collect metrics
        mission_metrics = await self._get_mission_metrics(agent_id, time_window_hours)
        safety_metrics = await self._get_safety_metrics(agent_id, time_window_hours)
        ethics_metrics = await self._get_ethics_metrics(agent_id, time_window_hours)

        return {
            "task_completion_rate": mission_metrics.get("completion_rate", 0.0),
            "average_task_time": 1.0 - mission_metrics.get("avg_time_normalized", 0.0),
            "safety_incidents": 1.0 - safety_metrics.get("incident_rate", 0.0),
            "policy_compliance": ethics_metrics.get("compliance_rate", 1.0),
            "efficiency": mission_metrics.get("efficiency", 0.5),
        }
```

---

## Integration with Existing Systems

### Integration Points

1. **DNA Module**
   - Genesis creates DNA snapshots on spawn
   - Mutations tracked in DNA history
   - KARMA scores stored in DNA

2. **Policy Engine**
   - Foundation layer validates against policies
   - Blueprint compliance requirements enforced
   - Runtime policy checks during evolution

3. **Immune System**
   - Genesis events logged to immune system
   - Health status checked before spawning
   - Threats can block agent creation

4. **KARMA Framework**
   - Fitness evaluation triggers evolution
   - Performance metrics guide mutations
   - Ethics scoring influences KARMA

5. **BaseAgent**
   - Traits integrated into agent metadata
   - Tools and permissions from blueprints
   - LLM config from blueprint defaults

---

## Implementation Plan

### Phase 1: Foundation (Week 1)
- [x] Design document
- [ ] Trait system implementation
- [ ] Foundation layer ethics validation
- [ ] Unit tests for traits and foundation

### Phase 2: Blueprints (Week 2)
- [ ] Blueprint schema and library
- [ ] Built-in blueprints (5 total)
- [ ] Blueprint validation
- [ ] Blueprint API endpoints

### Phase 3: Genesis Core (Week 3)
- [ ] GenesisService implementation
- [ ] Spawn agent functionality
- [ ] Deterministic spawning with seeds
- [ ] Integration with DNA module

### Phase 4: Evolution (Week 4)
- [ ] Mutation algorithms
- [ ] Fitness calculation
- [ ] Auto-evolution triggers
- [ ] Crossover/reproduction

### Phase 5: Integration & Testing (Week 5)
- [ ] KARMA integration
- [ ] Policy engine integration
- [ ] End-to-end tests
- [ ] Documentation

### Phase 6: API & UI (Week 6)
- [ ] REST API endpoints
- [ ] Frontend Genesis dashboard
- [ ] Agent genealogy visualization
- [ ] Deployment

---

## Security & Ethics

### Security Measures

1. **Ethics Validation**
   - All agents validated by Foundation layer
   - Critical traits immutable
   - Policy compliance mandatory

2. **Audit Trail**
   - All spawns logged to immune system
   - DNA snapshots immutable
   - Mutation history tracked

3. **Fail-Closed**
   - Ethics violations block creation
   - Invalid mutations rejected
   - Unknown blueprints denied

4. **Resource Limits**
   - Max agents per user/system
   - Mutation rate limits
   - Spawn throttling

### Ethics Framework

```python
CORE_ETHICS_PRINCIPLES = [
    "Safety is immutable - agents cannot reduce safety_priority below 0.7",
    "Harmful capabilities require explicit human approval",
    "All mutations must pass Foundation validation",
    "Agents cannot self-modify ethics-critical traits",
    "Emergency stop overrides all agent actions",
]
```

---

## API Specification

### Endpoints

```
POST   /api/genesis/spawn            - Spawn new agent from blueprint
POST   /api/genesis/evolve           - Evolve agent based on fitness
POST   /api/genesis/reproduce        - Create child from two parents
GET    /api/genesis/blueprints       - List available blueprints
GET    /api/genesis/blueprints/{id}  - Get blueprint details
POST   /api/genesis/blueprints       - Register custom blueprint
GET    /api/genesis/agents/{id}/traits - Get agent traits
GET    /api/genesis/agents/{id}/lineage - Get agent ancestry
GET    /api/genesis/agents/{id}/fitness - Get fitness scores
POST   /api/genesis/validate         - Validate agent config without creating
```

### Example Requests

#### Spawn Agent
```json
POST /api/genesis/spawn
{
  "blueprint_id": "fleet_coordinator_v1",
  "agent_id": "fleet_alpha",
  "trait_overrides": {
    "performance.speed_priority": 0.8
  },
  "seed": 42
}
```

#### Evolve Agent
```json
POST /api/genesis/evolve
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

---

## Appendix

### Glossary

- **Blueprint:** Template for creating agents with predefined traits
- **Trait:** Inheritable characteristic (cognitive, behavioral, ethical, etc.)
- **DNA Snapshot:** Immutable version of agent configuration
- **Mutation:** Controlled modification of agent traits
- **Fitness:** Performance score across multiple metrics
- **Foundation Layer:** Ethics validation and safety enforcement
- **Genesis:** Agent creation and evolution system

### References

- DNA Module: `backend/app/modules/dna/`
- Policy Engine: `backend/app/modules/policy/`
- Immune System: `backend/app/modules/immune/`
- BaseAgent: `backend/brain/agents/base_agent.py`
- CLAUDE.md: Project documentation

---

**End of Design Document**
