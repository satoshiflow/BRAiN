# OpenCode Agent Engagement Model

Status: Active Working Standard
Scope: BRAiN + OpenCode collaboration for coding, repair, extension, and code health
Audience: BRAiN orchestrator, OpenCode execution roles, AXE and ControlDeck operators, future integration work

---

## 1 Purpose

This document defines how OpenCode-aligned specialist roles are engaged inside BRAiN without prematurely turning them into hard runtime objects.

The goal is to preserve the current architecture and reduce integration risk while still making OpenCode operationally useful for development work.

This standard exists to ensure:

- BRAiN remains the canonical control and governance plane
- OpenCode remains a bounded execution and development plane
- specialist coding roles can be engaged consistently
- real delivery behavior is observed before deeper runtime coupling is introduced
- no parallel execution truth is created beside `SkillRun`

---

## 2 Decision

For the current phase, OpenCode specialist roles are treated as an on-demand working model, not yet as a fully enforced runtime contract.

This means:

- the roles are recognized and documented
- the roles may be invoked by BRAiN or by a human operator
- the roles guide decomposition, implementation, verification, handoff, and documentation
- the roles do not yet require new runtime ownership objects
- the system should be observed in practice before technical hard-binding is introduced

This is an intentional observation-first strategy.

---

## 3 Non-Negotiable Rules

- BRAiN is the only control plane
- `SkillRun` remains the canonical execution record
- OpenCode is a bounded execution plane, not a second sovereign brain
- AXE remains a human observation, intervention, and approval surface
- no new parallel runtime or shadow governance system may be introduced
- no agent-role convention may bypass policy, approval, audit, or tenant isolation
- documentation and usage patterns must be observed before stronger runtime integration is designed

---

## 4 OpenCode Role In BRAiN

OpenCode is the coding, repair, and code-health worker layer for BRAiN.

OpenCode is responsible for:

- code creation
- bug fixing
- repair and recovery support
- refactoring
- test-oriented implementation support
- code-health and maintainability improvements
- implementation handoff support
- documentation follow-through after engineering work

OpenCode is not responsible for:

- replacing BRAiN governance
- inventing a second orchestration layer
- owning canonical approval policy
- acting as an uncontrolled autonomous system

---

## 5 Specialist Role Set

The following roles are recognized for OpenCode-driven development work.

### 5.1 Archon

Purpose:

- planning
- scoping
- architectural ordering
- deciding implementation direction
- identifying constraints and boundaries

Use Archon when:

- the task is ambiguous
- architecture or sequencing matters
- multiple paths are possible
- the coding flow must be structured before execution

### 5.2 Pyra

Purpose:

- implementation
- feature delivery
- bug fixing
- controlled refactoring

Use Pyra when:

- stable execution is needed
- the task is implementation-heavy
- the work should follow an already chosen path

### 5.3 Nova

Purpose:

- fast implementation iteration
- tactical coding progress
- quick refinement of implementation details

Use Nova when:

- speed matters
- the implementation path is already clear
- shorter execution loops are more useful than architectural deliberation

### 5.4 Sentinel

Purpose:

- testing
- QA
- regression detection
- validation of behavioral correctness

Use Sentinel when:

- behavior must be verified
- tests need to be designed or run
- a change must be checked for regression risk
- a repair or implementation needs acceptance evidence

### 5.5 Giti

Purpose:

- git workflow handling
- commit preparation
- branch hygiene
- pull request operations

Use Giti when:

- changes are ready for git packaging
- branch state matters
- PR preparation or adjustment is required

### 5.6 Coolio

Purpose:

- polish
- readability improvement
- presentation quality
- result refinement

Use Coolio when:

- the solution works but needs cleanup
- developer-facing clarity should improve
- final presentation quality matters

### 5.7 Scribe

Purpose:

- documentation
- handoff notes
- specification updates
- durable knowledge capture

Use Scribe when:

- implementation must be documented
- decisions need to be recorded
- architecture or workflow understanding should be preserved
- future agents should inherit context cleanly

---

## 6 Default Process Model

The standard OpenCode coding flow inside BRAiN is:

`Intent -> BRAiN Orchestration -> Archon -> Pyra/Nova -> Sentinel -> Giti -> Coolio -> Scribe`

Interpretation:

- Archon frames the work
- Pyra or Nova builds
- Sentinel verifies
- Giti packages the result into git workflow artifacts when needed
- Coolio improves finish quality when useful
- Scribe preserves understanding and handoff value

This flow is guidance, not a hard runtime state machine.

The orchestrator may shorten or skip roles when the task does not require the full chain.

---

## 7 Engagement Model

OpenCode specialist roles are engaged on demand.

Valid engagement modes:

- explicit human request
- orchestrator-directed role invocation
- context-triggered guidance based on recognized keywords
- post-implementation handoff or verification need

This engagement model is intentionally soft-governed in the current phase.

It is designed to shape behavior before technical enforcement is introduced.

---

## 8 Trigger Keywords

When the working context contains one or more of the following concepts, the orchestrator should consider loading this model and using the role flow described here.

Primary trigger keywords:

- `OpenCode-Agent`
- `coding workflow`
- `repair workflow`
- `code health`

Additional practical trigger keywords:

- `feature build`
- `bugfix workflow`
- `refactor workflow`
- `qa handoff`
- `git handoff`
- `docs handoff`
- `repair`
- `extend`
- `implement`
- `verify`

These keywords are engagement hints, not permission overrides.

---

## 9 Operating Guidance

### 9.1 Plan First, Bind Later

Do not prematurely turn every working role into a backend runtime object.

Observation comes before hard-binding.

### 9.2 Preserve Existing Runtime Truth

Do not create a new execution truth beside:

- `SkillRun`
- existing policy and governance paths
- existing audit and event paths

### 9.3 Prefer Minimal Activation

Only invoke the roles needed for the current task.

Examples:

- simple fix: `Pyra -> Sentinel`
- architecture-sensitive change: `Archon -> Pyra -> Sentinel -> Scribe`
- merge-ready delivery: `Archon -> Pyra/Nova -> Sentinel -> Giti -> Scribe`

### 9.4 Treat Roles As Specialist Working Identities

At this phase, these roles are operating identities for decomposition and execution quality.

They are not yet required to map one-to-one to durable backend runtime objects.

### 9.5 Learn From Actual Use

Observe:

- which roles are invoked most often
- which handoffs are stable
- which tasks truly need multiple specialist roles
- which role distinctions collapse in practice
- which future runtime fields would be justified by real usage

---

## 10 Explicit Non-Goals For The Current Phase

The following are intentionally deferred:

- hard-binding every OpenCode role into runtime persistence
- forcing selected specialist metadata into all current paths immediately
- replacing working AXE worker flows with a new runtime path
- introducing new durable execution objects before observation justifies them
- pretending that prompt conventions alone are equivalent to backend contracts

---

## 11 Future Evolution Gate

Stronger technical integration may be considered later only if observed usage shows stable value.

Examples of possible future evolution:

- durable selected specialist metadata in `SkillRun`
- OpenCode job persistence aligned with canonical job contracts
- stronger `agent_management` mapping for OpenCode workers
- AXE surfaces showing selected OpenCode specialist identity
- tighter routing between domain selection and OpenCode execution lanes

Such work must only proceed after observation data and a dedicated architecture decision.

---

## 12 Practical Rule For BRAiN

When the task is about implementation, repair, extension, or code health, BRAiN should treat OpenCode as the bounded coding worker surface and may engage one or more of the specialist roles defined here.

When in doubt:

- preserve current architecture
- prefer the smallest correct role set
- observe before automating
- document before hard-binding

---

## 13 Final Policy

OpenCode specialist roles are officially recognized in BRAiN as an on-demand coding workflow model.

They are active for process guidance now.

They are not yet mandatory runtime entities.

This is the canonical safe path until observed development practice justifies deeper integration.
