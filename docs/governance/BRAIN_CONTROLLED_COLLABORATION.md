# BRAiN Development Guideline

## Controlled Collaboration

### Purpose

BRAiN must evolve as a **coordinated system**, not as a chaotic swarm of autonomous agents.

This guideline exists to prevent architectural drift, uncontrolled agent proliferation, and hidden coupling between system components.

Collaboration inside BRAiN is encouraged — but only through structured system layers.

---

# Core Rule

> Infrastructure is not an agent.

System capabilities must be implemented as infrastructure modules.

Examples:

| Capability    | Implementation         |
| ------------- | ---------------------- |
| Recovery      | Recovery Policy Engine |
| Protection    | Immune Orchestrator    |
| Evolution     | DNA / Genesis          |
| Development   | OpenCode Dev Layer     |
| Orchestration | BRAiN Supervisor       |

These are **system organs**, not autonomous agents.

---

# Allowed Agent Categories

Agents may only exist in three categories.

### Mission Agents

Agents executing tasks from the Mission Engine.

### Horizon Agents

Observation agents monitoring domains such as:

* AI
* robotics
* economics
* science
* politics
* markets

### Interface Agents

Agents assisting users via AXE or external interfaces.

All other system behavior must remain infrastructure.

---

# Five Core System Roles

BRAiN architecture is based on five system roles.

```
AXE
↓
GOTT
↓
BRAiN Supervisor
↓
Immune / Healthcare
↓
OpenCode Dev Layer
```

### AXE

Perception and interface layer.

### GOTT

Strategic evolution and long-term system direction.

### BRAiN Supervisor

Operational runtime orchestration.

### Immune / Healthcare

System protection and stabilization.

### OpenCode Dev Layer

System development and repair.

---

# Communication Model

Components must not communicate arbitrarily.

Allowed flow:

```
AXE → GOTT → Supervisor → Mission Engine → Agents
```

Protection signals:

```
Immune → Recovery → Supervisor
```

Evolution pipeline:

```
DNA → Governance → OpenCode Dev
```

---

# Anti-Chaos Rules

Forbidden patterns:

❌ infrastructure implemented as agents
❌ multiple orchestration centers
❌ parallel recovery systems
❌ uncontrolled self-modification
❌ hidden module coupling

Allowed patterns:

✔ event-driven communication
✔ clear service boundaries
✔ auditable decisions
✔ controlled evolution pipelines

---

# Evolution Control

System evolution must follow this sequence:

```
Signal
→ Diagnosis
→ Evaluation
→ Governance Check
→ Implementation
→ Testing
→ Integration
→ Monitoring
```

No component may bypass this pipeline.

---

# Federation Safety

Multiple BRAiN instances may cooperate across clusters.

However:

* every BRAiN instance must remain independent
* communication must occur through explicit protocols
* no hidden coupling between clusters

---

# Final Principle

BRAiN must remain:

* understandable
* auditable
* stable
* evolvable

Collaboration is allowed.

Chaos is not.
