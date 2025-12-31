# BRAIN Genesis Agent System

**Version:** 1.0.0
**Status:** Production Ready

---

## Overview

The **Genesis Agent System** provides autonomous agent generation with DNA-driven evolution, ethical constraints, and deterministic spawning for the BRAiN framework.

### Key Features

- ✨ **Deterministic Spawning** - Reproducible agent creation with seeds
- 🧬 **DNA-Driven Evolution** - Version-controlled agent mutations
- 🔄 **Genetic Crossover** - Multi-parent reproduction
- 🛡️ **Ethics Validation** - Foundation layer safety checks
- 📋 **Blueprint Templates** - 5 built-in agent archetypes
- 🎯 **Trait-Based System** - 26 inheritable characteristics

---

## Architecture

```
Genesis System
├── Traits (26 definitions across 6 categories)
│   ├── Cognitive (reasoning, creativity, learning)
│   ├── Ethical (safety, compliance, harm avoidance)
│   ├── Performance (speed, accuracy, efficiency)
│   ├── Behavioral (risk, adaptability, decisiveness)
│   ├── Social (coordination, communication, empathy)
│   └── Technical (code, fleet, navigation, data, ops)
│
├── Foundation Layer (Ethics & Safety)
│   ├── Core ethics rules (5 built-in)
│   ├── Policy engine integration
│   └── Immune system monitoring
│
├── Blueprints (Agent Templates)
│   ├── Fleet Coordinator v1
│   ├── Safety Monitor v1
│   ├── Navigation Planner v1
│   ├── Code Specialist v1
│   └── Ops Specialist v1
│
└── Core Service
    ├── spawn_agent()
    ├── evolve_agent()
    └── reproduce_agents()
```

---

## Quick Start

### 1. Spawn an Agent

```python
from backend.app.modules.genesis.core import get_genesis_service, SpawnAgentRequest

genesis = get_genesis_service()

# Spawn fleet coordinator with custom traits
result = await genesis.spawn_agent(
    SpawnAgentRequest(
        blueprint_id="fleet_coordinator_v1",
        agent_id="fleet_alpha",
        trait_overrides={
            "performance.speed_priority": 0.8,
            "social.coordination_skill": 0.95,
        },
        seed=42  # Deterministic
    )
)

print(f"Spawned agent: {result.agent_id}")
print(f"DNA snapshot: {result.dna_snapshot_id}")
```

### 2. Evolve an Agent

```python
from backend.app.modules.genesis.core import EvolveAgentRequest

# Evolve based on performance metrics
result = await genesis.evolve_agent(
    EvolveAgentRequest(
        agent_id="fleet_alpha",
        fitness_scores={
            "task_completion_rate": 0.85,
            "average_task_time": 0.75,
            "safety_incidents": 1.0,  # 1.0 = no incidents
            "robot_utilization": 0.9,
        },
        auto_mutate=True
    )
)

print(f"Fitness: {result.fitness_score:.3f}")
print(f"Mutations: {len(result.mutations_applied)}")
```

### 3. Reproduce Agents

```python
from backend.app.modules.genesis.core import ReproduceAgentsRequest

# Create child from two parents
result = await genesis.reproduce_agents(
    ReproduceAgentsRequest(
        parent1_id="fleet_alpha",
        parent2_id="fleet_beta",
        child_id="fleet_gamma"
    )
)

print(f"Child agent: {result.child_id}")
print(f"Inherited {len(result.inherited_traits)} traits")
```

---

## API Endpoints

### Agent Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/genesis/spawn` | Spawn new agent from blueprint |
| POST | `/api/genesis/evolve` | Evolve agent based on fitness |
| POST | `/api/genesis/reproduce` | Create child from two parents |
| POST | `/api/genesis/validate` | Validate agent config (dry-run) |

### Blueprints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/genesis/blueprints` | List all blueprints |
| GET | `/api/genesis/blueprints/{id}` | Get blueprint by ID |
| GET | `/api/genesis/blueprints/summary` | Library statistics |

### Traits

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/genesis/traits` | List all trait definitions |
| GET | `/api/genesis/traits/{id}` | Get trait by ID |

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/genesis/info` | Genesis system info |

---

## Built-in Blueprints

### 1. Fleet Coordinator (`fleet_coordinator_v1`)

**Purpose:** Multi-robot fleet coordination and task distribution

**Key Traits:**
- High coordination skill (0.9)
- High fleet management (0.9)
- High safety priority (0.9)
- Moderate speed priority (0.6)

**Capabilities:**
- Task assignment
- Load balancing
- Movement coordination
- Fleet monitoring

**Mutation:** Allowed (rate: 0.05)

---

### 2. Safety Monitor (`safety_monitor_v1`)

**Purpose:** Real-time safety monitoring and enforcement

**Key Traits:**
- **MAXIMUM safety priority (1.0)** - IMMUTABLE
- **MAXIMUM harm avoidance (1.0)** - IMMUTABLE
- ZERO risk tolerance (0.0)
- High decisiveness (0.9)

**Capabilities:**
- Safety monitoring
- Emergency stop
- Zone enforcement
- Incident response

**Mutation:** **NOT ALLOWED** - Safety agents are immutable

---

### 3. Navigation Planner (`navigation_planner_v1`)

**Purpose:** Path planning and navigation control

**Key Traits:**
- Very high navigation planning (0.95)
- High adaptability (0.9) for replanning
- High safety priority (0.9)
- Moderate speed (0.7)

**Capabilities:**
- Path planning (A*, RRT, etc.)
- Obstacle avoidance
- Dynamic replanning

**Mutation:** Allowed (rate: 0.08)

---

### 4. Code Specialist (`code_specialist_v1`)

**Purpose:** Code generation, review, and development

**Key Traits:**
- Very high code generation (0.95)
- High accuracy (0.95)
- Moderate creativity (0.6)
- High reasoning depth (0.8)

**Capabilities:**
- Code generation
- Code review
- Debugging

**Mutation:** Allowed (rate: 0.1)

---

### 5. Ops Specialist (`ops_specialist_v1`)

**Purpose:** System operations and infrastructure management

**Key Traits:**
- Very high system administration (0.95)
- High compliance (0.9)
- Low risk tolerance (0.2)
- High communication clarity (0.9)

**Capabilities:**
- Application deployment
- System monitoring
- Infrastructure management

**Mutation:** Allowed (rate: 0.05)

---

## Trait Categories

### Cognitive Traits (Intelligence & Learning)
- `cognitive.reasoning_depth` - Depth of logical reasoning
- `cognitive.creativity` - Novel solution generation
- `cognitive.learning_rate` - Adaptation speed
- `cognitive.pattern_recognition` - Pattern identification

### Ethical Traits (Alignment & Safety)
- `ethical.safety_priority` - **IMMUTABLE** (min: 0.7)
- `ethical.harm_avoidance` - **IMMUTABLE** (min: 0.8)
- `ethical.compliance_strictness` - Policy adherence
- `ethical.transparency` - Decision openness

### Performance Traits (Speed & Efficiency)
- `performance.speed_priority` - Speed vs. accuracy
- `performance.energy_efficiency` - Resource conservation
- `performance.accuracy_target` - Target accuracy level
- `performance.multitasking` - Concurrent task handling

### Behavioral Traits (Decision-Making)
- `behavioral.proactiveness` - Initiative level
- `behavioral.risk_tolerance` - Risk acceptance (max: 0.5)
- `behavioral.adaptability` - Change adaptation
- `behavioral.decisiveness` - Decision speed

### Social Traits (Communication & Collaboration)
- `social.coordination_skill` - Multi-agent coordination
- `social.communication_clarity` - Communication effectiveness
- `social.empathy` - User needs understanding
- `social.collaboration_preference` - Team work preference

### Technical Traits (Skills & Expertise)
- `technical.code_generation` - Code writing proficiency
- `technical.fleet_management` - Fleet coordination expertise
- `technical.navigation_planning` - Path planning skill
- `technical.data_analysis` - Data analysis capability
- `technical.system_administration` - Ops expertise

---

## Ethics & Safety

### Core Ethics Principles

1. **Safety is Immutable** - `safety_priority` cannot drop below 0.7
2. **Harm Avoidance is Absolute** - `harm_avoidance` min 0.8, immutable
3. **Risk is Capped** - `risk_tolerance` max 0.5
4. **All Mutations Validated** - Foundation layer checks every mutation
5. **Emergency Stop Overrides All** - Safety agents have absolute authority

### Foundation Layer Rules

- **safety_minimum** - Blocks creation if safety < 0.7
- **harm_avoidance_minimum** - Blocks if harm avoidance < 0.8
- **risk_tolerance_cap** - Blocks if risk > 0.5
- **no_dangerous_tool_combos** - Validates tool safety
- **compliance_minimum** - Warns if compliance < 0.5

### Fail-Closed Design

- Ethics violations **BLOCK** operations
- Invalid mutations **REJECTED**
- Unknown blueprints **DENIED**
- All events **LOGGED** to immune system

---

## Integration Points

### DNA Module
- Snapshots created on spawn
- Mutations tracked in history
- KARMA scores stored in DNA

### Policy Engine
- Foundation validates against policies
- Runtime checks during evolution
- Blueprint compliance enforced

### Immune System
- Genesis events logged
- Health checked before spawn
- Threats can block creation

### KARMA Framework
- Fitness evaluation
- Performance metrics
- Ethics scoring

---

## Configuration

Genesis uses singleton services with no configuration required:

```python
# All services auto-initialize
from backend.app.modules.genesis.core import get_genesis_service
from backend.app.modules.genesis.traits import get_trait_service
from backend.app.modules.genesis.blueprints import get_blueprint_library
from backend.app.modules.genesis.foundation import get_foundation_layer

genesis = get_genesis_service()  # Ready to use
```

---

## Testing

```bash
# Run Genesis tests
pytest backend/tests/test_genesis.py -v

# Test specific component
pytest backend/tests/test_genesis.py::test_spawn_agent -v
```

---

## Future Enhancements

### Planned Features

- [ ] Custom blueprint creation via API
- [ ] Advanced mutation algorithms (genetic programming)
- [ ] Multi-generation lineage tracking
- [ ] Fitness-based auto-evolution triggers
- [ ] Agent skill trees and progression
- [ ] Cross-blueprint trait mixing
- [ ] Performance-based blueprint optimization

### Research Directions

- Emergent behavior analysis
- Trait co-evolution patterns
- Population dynamics
- Fitness landscape visualization
- Automated blueprint generation

---

## Troubleshooting

### Common Issues

**1. EthicsViolationError on spawn**
```
Violation: Safety priority cannot be below 0.7
```
**Solution:** Check trait_overrides - safety traits are immutable and have minimums

**2. Blueprint not found**
```
Blueprint not found: fleet_coordinator_v2
```
**Solution:** Use `GET /api/genesis/blueprints` to list available blueprints

**3. Mutation blocked**
```
Mutation blocked: Cannot mutate immutable trait
```
**Solution:** Safety and harm avoidance traits are immutable by design

---

## Contributing

### Adding Custom Traits

1. Create trait definition:
```python
from backend.app.modules.genesis.traits.schemas import TraitDefinition, TraitCategory, TraitType

custom_trait = TraitDefinition(
    id="custom.my_trait",
    name="My Custom Trait",
    category=TraitCategory.TECHNICAL,
    type=TraitType.FLOAT,
    default_value=0.5,
    min_value=0.0,
    max_value=1.0,
    description="My custom trait description"
)
```

2. Register with trait service:
```python
from backend.app.modules.genesis.traits import get_trait_service

trait_service = get_trait_service()
trait_service.register_custom_trait(custom_trait)
```

### Adding Custom Blueprints

1. Create blueprint:
```python
from backend.app.modules.genesis.blueprints.schemas import AgentBlueprint

custom_blueprint = AgentBlueprint(
    id="my_agent_v1",
    name="My Custom Agent",
    description="...",
    base_config={...},
    trait_profile={...},
    # ... other fields
)
```

2. Register with library:
```python
from backend.app.modules.genesis.blueprints import get_blueprint_library

library = get_blueprint_library()
library.register(custom_blueprint)
```

---

## License

Part of the BRAiN framework. See main repository for license details.

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/satoshiflow/BRAiN/issues
- Documentation: See `DESIGN.md` for detailed architecture

---

**Genesis Version:** 1.0.0
**Last Updated:** 2025-12-24
