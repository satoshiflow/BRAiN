# BRAiN Skill-First Implementation Roadmap

Version: 1.0
Status: Active Delivery Roadmap
Purpose: Define the phased implementation plan from current repo state to the target BRAiN architecture.

---

## 1 Delivery Principles

- implement in `backend/app/modules/*`
- preserve compatibility through adapters where needed
- use `SkillRun` as canonical execution record
- keep EventStream canonical
- keep docs, specs, and AGENTS guidance synchronized
- apply `GROUNDING -> STRUCTURE -> CREATION -> EVALUATION -> FINALIZATION`

---

## 2 Program Structure

The work is split into 6 phases, 12 milestones, and 12 sprint groups aligned with the approved epics.

---

## Phase 1 - Control Plane Foundation

### Milestone M1 - Contract and Governance Baseline

#### Sprint S1 - Epic 1

Goal:
- finalize runtime contracts for skills and capabilities

Steps:
1. lock `SkillDefinition`, `CapabilityDefinition`, `ProviderBinding`, `SkillRun`, `EvaluationResult`
2. align naming, lifecycle, events, and error codes
3. keep docs/specs authoritative

Tasks:
- review all Epic 1 spec files
- identify implementation order for data models
- map required DB tables and API surfaces
- define compatibility notes for existing `skills` module

Expected result:
- implementation-ready contract baseline

#### Sprint S2 - Epic 2

Goal:
- define and then implement the Constitution Gate baseline for `SkillRun`

Steps:
1. map current auth/policy/audit primitives
2. implement one fail-closed gate service path
3. bind approval/breakglass to exact run intent

Tasks:
- create `PolicyDecision` persistence plan
- create `ApprovalGate` persistence plan
- define transaction boundary for state/audit/outbox
- add gate integration notes for `SkillRun`

Expected result:
- governed run authorization path ready for implementation

---

## Phase 2 - Registry and Adapter Core

### Milestone M2 - Registry Source of Truth

#### Sprint S3 - Epic 3

Goal:
- build `SkillRegistry` and `CapabilityRegistry` as canonical control plane

Steps:
1. introduce registry modules and models
2. migrate definitions away from implicit/in-memory truth
3. preserve compatibility adapters for existing skill surfaces

Tasks:
- implement `backend/app/modules/skills_registry/`
- implement `backend/app/modules/capabilities_registry/`
- define seeding/bootstrap flow from built-ins without dual-write truth
- add registry read/resolve endpoints

Expected result:
- PostgreSQL-backed registries with deterministic resolution

### Milestone M3 - Provider Standardization

#### Sprint S4 - Epic 4

Goal:
- standardize provider execution through a capability adapter layer

Steps:
1. define adapter core in `backend/app/core/capabilities/`
2. wrap two initial capability domains
3. freeze deterministic provider selection on runs

Tasks:
- create base adapter contracts
- integrate with `llm_router` and one non-LLM integration path
- normalize result/error schemas
- add provider binding resolution plumbing

Expected result:
- reusable adapter layer with at least two working capability domains

---

## Phase 3 - Runtime Spine

### Milestone M4 - Skill Engine MVP

#### Sprint S5 - Epic 5

Goal:
- create the first end-to-end Skill Engine path

Steps:
1. build `backend/app/modules/skill_engine/`
2. connect registry resolution, Constitution Gate, planning, adapters, and terminalization
3. make `SkillRun` canonical for execution

Tasks:
- implement selector/resolver runtime flow
- integrate `planning` snapshots
- integrate `task_queue` as subordinate dispatch only
- wire terminal state transitions and events

Expected result:
- first working governed SkillRun execution path

### Milestone M5 - Evaluation and Optimization Baseline

#### Sprint S6 - Epic 6

Goal:
- make executions measurable and reviewable

Steps:
1. add evaluator baseline
2. add telemetry baseline
3. add optimizer recommendation baseline

Tasks:
- implement `skill_evaluator`
- implement `skill_optimizer`
- define KPI projections
- integrate `EvaluationResult` creation and persistence

Expected result:
- measured execution quality and advisory optimization loop

---

## Phase 4 - Orchestration Consolidation

### Milestone M6 - Agents as Skill Orchestrators

#### Sprint S7 - Epic 7

Goal:
- move agents from business-logic holders to orchestration actors

Steps:
1. map current agent behavior
2. redirect agent actions to `SkillRun`
3. reduce direct feature logic in agent surfaces

Tasks:
- update `agent_management` integration points
- update `supervisor` ownership semantics
- define agent-to-skill invocation contracts

Expected result:
- agents become governed coordinators over skills

### Milestone M7 - Runtime Harmonization

#### Sprint S8 - Epic 8

Status:
- implemented baseline and stabilized on 2026-03-08

Goal:
- harmonize `Mission`, `SkillRun`, and queue execution paths

Steps:
1. make `SkillRun` canonical
2. adapt mission paths to envelope/compat role
3. narrow task queue to lease/dispatch role

Tasks:
- define canonical write owner for runtime execution
- adapt legacy mission bridge
- add `skill_run_id` ownership to queue/compat layers
- freeze route shadowing and dual-write surfaces

Expected result:
- one execution spine with compatibility adapters instead of parallel runtimes

---

## Phase 5 - Knowledge and Evolution

### Milestone M8 - Knowledge Layer

#### Sprint S9 - Epic 9

Status:
- implemented baseline module and contracts on 2026-03-08; follow-on expansion remains optional

Goal:
- introduce durable knowledge as distinct from memory

Steps:
1. define knowledge objects and provenance
2. implement governed knowledge writes
3. integrate run-lesson ingestion

Tasks:
- create `backend/app/modules/knowledge_layer/`
- bridge existing `knowledge_graph`
- implement knowledge search/query baseline

Expected result:
- governed long-lived knowledge substrate

### Milestone M9 - Memory and Evolution Consolidation

#### Sprint S10 - Epic 10

Status:
- implemented baseline run anchoring for memory, learning, and DNA on 2026-03-08; deeper evolution cleanup remains incremental

Goal:
- anchor memory and evolution to canonical execution history

Steps:
1. define history anchor around `SkillRun`
2. project memory views from run history
3. constrain DNA/genesis/quarantine to durable state

Tasks:
- normalize memory anchors
- align DNA/genesis lineage references
- remove target-state dependence on in-memory-only evolution state

Expected result:
- coherent evolution substrate tied to canonical runs

---

## Phase 6 - Builders and Decommission

### Milestone M10 - Builders as Skill Consumers

#### Sprint S11 - Epic 11

Status:
- implemented baseline and stabilized on 2026-03-08

Goal:
- make builders consume skills rather than run hidden runtimes

Steps:
1. pick two initial builders
2. map domain actions to skills
3. keep builder APIs but route execution to `SkillRun`

Tasks:
- migrate `course_factory`
- migrate `webgenesis`
- standardize deployment/DNS calls through governed skill paths

Expected result:
- at least two builder flows execute through the new architecture

### Milestone M11 - Plugin and Module Lifecycle

#### Sprint S12 - Epic 12

Status:
- implemented baseline and stabilized on 2026-03-08

Goal:
- establish formal lifecycle, decommission rules, and cutover governance

Steps:
1. create module lifecycle registry or equivalent control plane
2. mark canonical write owners
3. begin retirement plan for legacy runtime surfaces

Tasks:
- implement lifecycle metadata handling
- add decommission matrix for key modules
- add kill-switch and adapter-state tracking
- lock down deprecated write paths

Expected result:
- explicit module lifecycle and controlled retirement path

### Milestone M12 - Stabilization Gate

Goal:
- verify the new architecture is internally coherent and migration-safe

Tasks:
- run targeted tests and RC gate
- verify docs/specs/roadmap consistency
- verify no new shadow runtime paths were introduced
- verify auth/audit/event guarantees remain intact

Expected result:
- release-ready architecture baseline for further rollout

---

## 3 Cross-Cutting Workstreams

These run across all phases.

### W1 - Documentation Discipline
- update `docs/specs/*`
- update `docs/roadmap/*`
- update `AGENTS.md`
- update `docs/core/*` when standards evolve

### W2 - Security and Governance
- no governed path without auth/policy/audit
- tenant isolation remains explicit
- breakglass and approval semantics remain documented and testable

### W3 - Legacy Containment
- no expansion of `backend/modules/*`
- preserve adapters while reducing direct writes
- explicitly document write-owner transitions

### W4 - Verification
- state-machine tests
- API contract tests
- migration regression tests
- RC gate alignment

---

## 4 Execution Order

Primary sequence:

`1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10 -> 11 -> 12`

Parallelizable groups:

- within Phase 2: adapter prep can start while registry implementation is stabilizing
- within Phase 3: evaluator/test planning can start before engine runtime is fully complete
- within Phase 5: knowledge design and memory consolidation prep can overlap
- within Phase 6: plugin lifecycle work can prepare while builder migrations are underway

---

## 5 Immediate Next Actions

Implementation should now continue with:

1. expand coverage for `knowledge_layer` and memory/learning run-ingest flows
2. review whether pytest-only compatibility shims should remain or be narrowed further
3. do final wording cleanup across roadmap/spec docs if desired
4. create a checkpoint commit for Epic 8-12 stabilization

---

## 6 Success Definition

The roadmap is successful when:

- `SkillRun` is the canonical execution record
- skill and capability registries are the only durable source of truth for those objects
- provider execution is standardized behind capability adapters
- agents and builders orchestrate skills instead of embedding hidden runtimes
- knowledge and memory are separated correctly
- legacy runtime paths are adapter-bound or retired
- docs and standards remain synchronized with implementation
