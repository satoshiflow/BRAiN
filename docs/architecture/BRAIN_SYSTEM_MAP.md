# BRAiN System Map

## Purpose

This document describes the high-level architecture of the BRAiN system.

It serves as a reference for:

* developers
* OpenCode dev agents
* architectural planning
* future system extensions

The goal is to ensure that BRAiN evolves in a **structured and stable architecture** instead of fragmenting into uncontrolled modules.

---

# System Overview

BRAiN is designed as a layered intelligent system.

Each layer has a clearly defined responsibility.

```
User
 ↓
AXE (Interface Layer)
 ↓
GOTT (Strategic Evolution Layer)
 ↓
BRAiN Supervisor (Runtime Orchestration)
 ↓
Mission Engine
 ↓
Agent Cluster
```

Supporting infrastructure layers operate alongside this runtime.

---

# Core System Layers

## 1. AXE — Interface Layer

Purpose:

* interaction with users
* external APIs
* external systems
* command input

Responsibilities:

* receive user requests
* translate signals into BRAiN missions
* present results

AXE does **not execute missions**.

AXE only **interprets input and forwards intent**.

---

## 2. GOTT — Strategic Evolution Layer

Purpose:

Long-term system intelligence.

Responsibilities:

* strategic planning
* system evolution decisions
* architectural direction
* long-term capability planning

Examples:

* new module proposals
* horizon analysis
* architecture evolution

GOTT operates on **strategic time scales**, not runtime.

---

## 3. BRAiN Supervisor

Purpose:

Operational runtime control.

Responsibilities:

* mission orchestration
* agent coordination
* resource allocation
* decision arbitration

The Supervisor is the **central runtime decision authority**.

---

## 4. Mission Engine

Purpose:

Transform system goals into executable tasks.

Responsibilities:

* task decomposition
* mission planning
* execution tracking
* agent assignment

Example mission:

```
Build feature X
```

Mission Engine transforms it into:

```
Task 1 → code generation
Task 2 → tests
Task 3 → integration
Task 4 → validation
```

---

## 5. Agent Cluster

Agents perform specialized execution tasks.

Examples:

* development agents
* research agents
* monitoring agents
* horizon agents

Agents must **never control system architecture**.

Agents execute tasks only.

---

# Infrastructure System Organs

BRAiN contains several infrastructure modules that act as **system organs**.

These are not agents.

## Immune System

Location:

```
backend/app/modules/immune
backend/app/modules/immune_orchestrator
```

Responsibilities:

* anomaly detection
* incident analysis
* threat mitigation
* isolation of failing components

---

## Recovery Engine

Location:

```
backend/app/modules/recovery_policy_engine
```

Responsibilities:

* retry strategies
* circuit breaking
* rollback policies
* resource recovery

---

## DNA / Genesis

Location:

```
backend/app/modules/dna
backend/app/modules/genetic_integrity
```

Responsibilities:

* agent evolution
* mutation tracking
* blueprint management
* genetic integrity validation

---

## OpenCode Dev Layer

Purpose:

Development and repair of BRAiN itself.

Responsibilities:

* code generation
* bug fixing
* module creation
* architecture improvements

OpenCode operates as **the internal development organ of BRAiN**.

---

# System Interaction Model

Runtime flow:

```
User
 ↓
AXE
 ↓
BRAiN Supervisor
 ↓
Mission Engine
 ↓
Agents
```

Protection flow:

```
Immune System
 ↓
Recovery Engine
 ↓
Supervisor
```

Evolution flow:

```
DNA / Genesis
 ↓
Governance
 ↓
OpenCode Dev Layer
```

---

# Horizon Intelligence

Horizon Agents monitor external domains.

Examples:

* AI research
* robotics
* economic trends
* open source ecosystems
* technology breakthroughs

Their responsibility is **observation and analysis**, not execution.

---

# Federation Model

Multiple BRAiN instances may cooperate.

Rules:

* each BRAiN instance must remain independent
* communication must use explicit protocols
* no hidden coupling between clusters

---

# Anti-Chaos Architecture Rules

The following patterns are forbidden:

❌ infrastructure implemented as agents
❌ multiple orchestration centers
❌ uncontrolled self-modification
❌ hidden module dependencies
❌ parallel recovery systems

Allowed patterns:

✔ event-driven communication
✔ clear service boundaries
✔ auditable decisions
✔ controlled system evolution

---

# Long-Term Vision

BRAiN evolves into a **self-maintaining intelligent system** capable of:

* developing new capabilities
* repairing its own infrastructure
* learning from environmental signals
* coordinating specialized agent clusters

This evolution must always remain **auditable, structured, and stable**.

BRAiN is not a swarm.

BRAiN is an **organized intelligence system**.
