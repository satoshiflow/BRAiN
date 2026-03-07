# BRAiN Meta Agent Model

## Purpose

This document defines the **meta-agent structure of BRAiN**.

Meta-agents operate **above the normal agent layer** and are responsible for:

* protecting the system
* evolving the system
* discovering new capabilities
* guiding long-term development

These agents must remain **clearly separated**.

Mixing these roles leads to architectural instability.

---

# Meta-Agent Roles

BRAiN defines three core meta-agent roles:

```
Guardian
Explorer
Architect
```

Above them exists the **strategic oversight layer**.

```
GOTT
```

---

# Strategic Layer

## GOTT

GOTT represents the **strategic oversight function** of BRAiN.

Responsibilities:

* strategic prioritization
* architectural alignment
* long-term system direction
* approval of major system evolution

GOTT does **not execute tasks**.

GOTT decides **what should happen**, not **how it happens**.

---

# 1. Guardian

The Guardian protects the system.

Responsibilities:

```
system stability
incident detection
recovery actions
mutation containment
risk mitigation
```

BRAiN implementation:

```
Immune Orchestrator
Recovery Policy Engine
Genetic Integrity
Genetic Quarantine Manager
```

The Guardian ensures that failures **cannot cascade through the system**.

---

# 2. Explorer

The Explorer discovers new opportunities.

Responsibilities:

```
technology monitoring
open source discovery
AI model tracking
research paper analysis
trend detection
capability gap identification
```

Explorer outputs:

```
capability reports
technology proposals
tool integration suggestions
new module ideas
```

Explorer does **not modify the system directly**.

It only generates structured signals.

This agent family is often referred to as:

```
Horizon Agents
```

---

# 3. Architect

The Architect builds and improves the system.

Responsibilities:

```
implement new modules
repair system faults
refactor architecture
generate code patches
create integrations
```

BRAiN implementation:

```
OpenCode Dev Layer
```

OpenCode acts as the **system builder and repair worker**.

It executes development tasks but **does not decide strategy**.

---

# Operational Flow

The meta-agent interaction flow is:

```
Explorer
    ↓
GOTT
    ↓
Supervisor / Mission Engine
    ↓
Architect (OpenCode)
    ↓
Integration
    ↓
Guardian Monitoring
```

This ensures:

* controlled innovation
* safe evolution
* architectural stability

---

# Separation Principle

The following combinations are **forbidden**:

```
Explorer directly modifying architecture
OpenCode deciding strategic direction
Guardian implementing new features
```

Each role must remain independent.

---

# BRAiN Layer Overview

```
User
 ↓
AXE (Perception)

 ↓
GOTT (Strategic Direction)

 ↓
Supervisor (Operational Control)

 ↓
Agents (Execution)

Meta Layers:

Guardian
Explorer
Architect
```

---

# Long-Term Vision

The meta-agent structure allows BRAiN to become a system capable of:

```
self-protection
controlled evolution
technology adaptation
autonomous development
```

However:

Evolution must always remain **governed and auditable**.

BRAiN is designed to evolve **without losing architectural stability**.
