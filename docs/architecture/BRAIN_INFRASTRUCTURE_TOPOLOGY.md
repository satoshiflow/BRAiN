# BRAiN Infrastructure Topology

## Purpose

This document defines the **recommended infrastructure topology for BRAiN**.

BRAiN is designed as a **modular AI runtime system** that must remain:

* scalable
* fault tolerant
* cost efficient
* infrastructure independent

The topology is therefore **progressive**, allowing the system to grow from a single development machine into a distributed AI runtime cluster.

---

# Infrastructure Design Principles

BRAiN infrastructure follows these principles:

1. **CPU-first architecture**
2. **GPU only for model inference**
3. **runtime separation of concerns**
4. **clear node responsibilities**
5. **minimal operational complexity**

GPU resources are **not required for development**.

---

# BRAiN Node Types

BRAiN uses several logical node types.

Each node fulfills a **specific system role**.

```
Dev Node
Core Runtime Node
Data Node
Worker Node
Inference Node
Federation Node (future)
```

---

# 1. Dev Node

The Dev Node is the **local development environment**.

Example:

```
Surface Laptop
Local workstation
```

### Responsibilities

* OpenCode development
* architecture design
* code editing
* documentation
* governance definitions
* small local tests
* module experimentation

### Services typically running

```
OpenCode
local repo
mock runtime tests
optional local containers
```

The Dev Node **does not run heavy runtime infrastructure**.

It interacts with the Runtime Node remotely.

---

# 2. Core Runtime Node

The Core Runtime Node runs the **BRAiN system kernel**.

This is the most important server.

### Responsibilities

* BRAiN API
* Supervisor
* Mission Engine
* Immune Orchestrator
* Recovery Policy Engine
* DNA / Genesis logic
* Governance
* Audit system
* Event system

### Typical services

```
brain-backend
event stream
mission engine
supervisor runtime
```

### Role in system

```
Central Intelligence Layer
```

All operational decision making occurs here.

---

# 3. Data Node

The Data Node stores **persistent system memory**.

### Responsibilities

* system state
* event history
* embeddings
* mission results
* audit logs

### Typical services

```
PostgreSQL
Redis
Qdrant
Backup system
```

### Role in system

```
Memory Layer
```

---

# 4. Worker Node

Worker Nodes execute **computational tasks and tool operations**.

They provide system scalability.

### Responsibilities

```
agent execution
tool calls
background jobs
queue consumers
automation tasks
OpenCode worker execution
browser automation
```

Workers **do not control architecture decisions**.

They execute tasks assigned by the Supervisor.

### Role

```
Execution Layer
```

---

# 5. Inference Node (GPU)

The Inference Node provides **high performance model inference**.

GPU resources are only used here.

### Responsibilities

```
vLLM model serving
embedding generation
vision inference
large model execution
```

### Important rule

The GPU node **is not part of the BRAiN core runtime**.

It is only a **model service**.

```
BRAiN Core → LLM Router → GPU Node
```

---

# 6. Federation Node (Future)

In later phases BRAiN instances may communicate with other BRAiN systems.

Federation nodes manage:

```
cross-brain communication
knowledge exchange
distributed agent coordination
external service integration
```

---

# Development Topology (Phase 1)

Initial development uses a **minimal infrastructure**.

```
Surface Dev Node
│
└── Hetzner Dev Runtime Node
        ├── BRAiN Backend
        ├── PostgreSQL
        ├── Redis
        ├── Qdrant
        └── Mock LLM
```

Advantages:

* minimal cost
* simple debugging
* fast iteration
* low operational complexity

---

# Scalable Runtime Topology (Phase 2)

As load increases the system separates runtime components.

```
                Dev Node
                    │
                    ▼
            Core Runtime Node
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
     Data Node   Worker Node   Inference Node
    (Memory)     (Execution)      (GPU)
```

Responsibilities:

```
Core Runtime → decisions
Data Node → persistence
Worker Node → execution
Inference Node → model serving
```

---

# Future Distributed BRAiN Topology

Large scale BRAiN networks may look like this:

```
             Dev Node
                 │
                 ▼
           Core Runtime
                 │
        ┌────────┼─────────┐
        ▼        ▼         ▼
    Data Node  Worker   GPU Inference
                 │
                 ▼
            Federation Node
```

---

# Communication Rules

BRAiN services communicate through controlled interfaces.

### Allowed communication

```
AXE → Supervisor
Supervisor → Mission Engine
Mission Engine → Workers
Workers → Tool APIs
Core → Data Node
Core → Inference Node
```

### Forbidden patterns

```
Agents directly modifying core runtime
Workers bypassing supervisor
GPU nodes controlling system decisions
```

This ensures architectural stability.

---

# Cost Strategy

BRAiN follows a **CPU-first infrastructure strategy**.

GPU resources are added only when required.

### Phase 1

```
Surface Dev Node
+
1 Hetzner Runtime Node
```

### Phase 2

```
Core Runtime Node
+
Data Node
+
Worker Node
```

### Phase 3

```
+ GPU Inference Node
```

---

# Architectural Philosophy

BRAiN separates **intelligence, execution, memory, and inference**.

```
Intelligence → Core Runtime
Memory → Data Node
Execution → Worker Nodes
Inference → GPU Node
```

This prevents system instability and enables long term scalability.

---

# Final Principle

BRAiN should always maintain a **clear infrastructure hierarchy**.

```
Structure first
Compute second
Acceleration third
```

The system must remain understandable even as it scales.

A clear topology is the foundation of a stable AI infrastructure.
