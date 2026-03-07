Hier sind beide Dateien **fertig formatiert als Markdown**, genau so, dass du sie **1:1 kopieren und ins Repo legen kannst**.

Speicherpfade:

```
docs/architecture/BRAIN_RUNTIME_SERVICES.md
docs/architecture/BRAIN_DEPLOYMENT_MODEL.md
```

---

# Datei 1

```markdown
# BRAiN Runtime Services

## Purpose

This document defines the **runtime services of the BRAiN system**.

Runtime services are the operational components responsible for executing
the BRAiN architecture during system operation.

They form the **live operational layer** of BRAiN.

These services run on infrastructure nodes and interact through APIs,
queues, and event streams.

---

# Runtime Service Categories

BRAiN runtime services are grouped into five categories:

```

Core Runtime Services
Memory Services
Protection Services
Execution Services
Development Services

```

Each category fulfills a specific role in the system.

---

# 1. Core Runtime Services

Core Runtime Services represent the **central intelligence of BRAiN**.

These services coordinate system behavior.

### Components

```

BRAiN API
Supervisor
Mission Engine
Event System
Governance
Audit System

```

### Responsibilities

- interpret system signals
- coordinate missions
- orchestrate agents
- manage runtime state
- enforce governance policies

### Service Location

Typically runs on:

```

Core Runtime Node

```

---

# 2. Memory Services

Memory Services store **persistent system knowledge and state**.

### Components

```

PostgreSQL
Redis
Qdrant
Event Store
Audit Logs

```

### Responsibilities

- system state persistence
- event history storage
- vector embeddings
- knowledge storage
- audit tracking

### Storage Layers

```

PostgreSQL → structured data
Redis → fast runtime cache
Qdrant → vector search / embeddings

```

### Service Location

```

Data Node

```

---

# 3. Protection Services

Protection services maintain **system stability and resilience**.

### Components

```

Immune Orchestrator
Recovery Policy Engine
Genetic Integrity
Genetic Quarantine Manager

```

### Responsibilities

- anomaly detection
- incident classification
- recovery actions
- mutation containment
- runtime protection

### Protection Flow

```

Signal
→ Detection
→ Decision
→ Recovery
→ Audit

```

These services ensure failures cannot cascade through the system.

---

# 4. Execution Services

Execution services perform **actual system work**.

These services are typically distributed across worker nodes.

### Components

```

Agent Workers
Tool Workers
Browser Automation Workers
Background Job Workers
Queue Consumers

```

### Responsibilities

- task execution
- tool invocation
- data processing
- automation workflows
- mission execution

Workers do not make strategic decisions.

They execute tasks assigned by the Supervisor.

---

# 5. Development Services

Development services support **system evolution and repair**.

### Components

```

OpenCode Dev Layer
Code Generation Workers
Test Validation Pipelines
Patch Integration

```

### Responsibilities

- implement new modules
- repair system faults
- generate patches
- refactor system code
- implement architectural changes

Development services operate under governance control.

---

# Runtime Service Communication

Runtime services communicate through controlled channels.

### Communication Types

```

HTTP APIs
Event Streams
Message Queues
Database Access

```

### Example Flow

```

AXE
→ Supervisor
→ Mission Engine
→ Agent Worker
→ Tool API
→ Event Stream
→ Audit Store

```

This architecture ensures observability and traceability.

---

# Runtime Service Separation

Each runtime service must respect architectural boundaries.

Forbidden patterns:

```

Agents modifying architecture
Workers bypassing supervisor
Direct modification of system memory by execution workers

```

Allowed patterns:

```

Supervisor assigning missions
Workers executing tasks
Protection services monitoring system state
Development services updating architecture

```

---

# Summary

BRAiN runtime services are organized to ensure:

- stability
- observability
- modularity
- scalability

Clear service separation allows the system to grow without losing structure.
```

---

# Datei 2

```markdown
# BRAiN Deployment Model

## Purpose

This document defines the **deployment model of the BRAiN system**.

BRAiN is designed to scale from a **single development node**
to a **distributed multi-node AI infrastructure**.

The deployment model defines how runtime services are placed across nodes.

---

# Deployment Philosophy

BRAiN follows a progressive deployment strategy:

```

CPU-first development
GPU acceleration only when needed
Clear infrastructure separation
Minimal operational complexity

```

This ensures low cost and high system stability.

---

# Node Types

BRAiN infrastructure consists of several node types.

```

Dev Node
Core Runtime Node
Data Node
Worker Node
Inference Node
Federation Node (future)

```

Each node type has specific responsibilities.

---

# 1. Dev Node

The Dev Node is the **local development environment**.

### Example

```

Surface Laptop
Developer Workstation

```

### Responsibilities

- architecture design
- code development
- OpenCode operation
- documentation
- local testing
- module prototyping

### Typical Services

```

OpenCode
local repository
mock runtime environment
lightweight containers

```

The Dev Node does not host the production runtime.

---

# 2. Core Runtime Node

The Core Runtime Node hosts the **central BRAiN services**.

### Responsibilities

```

BRAiN API
Supervisor
Mission Engine
Governance
Event System
Audit System
Protection Services

```

### Role

```

Central Intelligence Layer

```

All strategic decisions occur here.

---

# 3. Data Node

The Data Node provides **persistent storage for BRAiN**.

### Services

```

PostgreSQL
Redis
Qdrant
Backup Services

```

### Responsibilities

- system memory
- event history
- embeddings
- audit records
- system state

### Role

```

Memory Layer

```

---

# 4. Worker Node

Worker Nodes provide **execution capacity**.

### Responsibilities

```

agent execution
tool invocation
background jobs
queue processing
automation workflows
OpenCode worker tasks

```

### Role

```

Execution Layer

```

Worker nodes scale horizontally.

---

# 5. Inference Node (GPU)

Inference Nodes provide **high-performance model inference**.

### Services

```

vLLM
embedding services
vision inference
large language model execution

```

### Important Principle

Inference nodes are **model services only**.

They are not part of the core BRAiN runtime.

```

BRAiN Core → LLM Router → GPU Node

```

---

# 6. Federation Node (Future)

Federation Nodes enable communication between BRAiN instances.

### Responsibilities

```

cross-brain communication
knowledge exchange
distributed missions
external system integration

```

This allows BRAiN systems to operate in a network.

---

# Development Deployment Model

Initial development uses a **minimal topology**.

```

Dev Node
│
▼
Dev Runtime Node
├── BRAiN Backend
├── PostgreSQL
├── Redis
├── Qdrant
└── Mock LLM

```

Advantages:

- low cost
- simple debugging
- fast iteration

---

# Scalable Deployment Model

As the system grows, infrastructure separates.

```

Dev Node
│
▼
Core Runtime Node
│
├── Data Node
├── Worker Node
└── Inference Node

```

Responsibilities:

```

Core Runtime → system intelligence
Data Node → system memory
Worker Node → task execution
Inference Node → model serving

```

---

# Communication Model

Nodes communicate through controlled interfaces.

### Allowed Communication

```

AXE → Core Runtime
Core Runtime → Data Node
Core Runtime → Worker Node
Core Runtime → Inference Node
Worker Node → Tool APIs

```

### Forbidden Communication

```

Worker Nodes modifying system architecture
Inference Nodes controlling runtime decisions
Agents bypassing supervisor logic

```

This prevents uncontrolled system behavior.

---

# Cost Strategy

BRAiN infrastructure scales gradually.

### Phase 1

```

Dev Node
+
Single Runtime Node

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

* GPU Inference Node

```

---

# Final Principle

BRAiN deployment must preserve system clarity.

```

Intelligence → Core Runtime
Memory → Data Node
Execution → Worker Nodes
Inference → GPU Nodes

```
Infrastructure must remain understandable as the system grows.
```

