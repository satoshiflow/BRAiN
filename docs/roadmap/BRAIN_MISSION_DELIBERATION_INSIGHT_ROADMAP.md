# BRAiN Mission Deliberation and Insight Roadmap

Version: 1.0
Status: Active Parallel Roadmap
Purpose: Define the parallel build path for turning BRAiN from an execution-centric system into a governed deliberation and insight-forming system.

---

## 1 Intent

This roadmap runs alongside the main skill-first implementation roadmap.

It does not replace the current execution plan.

It extends it with the learning path:

`Execution -> Experience -> Insight -> Pattern -> Knowledge -> Skill Evolution`

---

## 2 Strategy

- keep `SkillRun` as canonical execution anchor
- avoid large mission rewrites too early
- introduce the smallest durable consolidation layer first
- delay full deliberation graph until runtime spine is stable
- make learning governed, auditable, and reversible

---

## Phase D1 - Execution Anchoring

### Milestone D1.1 - Runtime Evidence Baseline

Goal:
- ensure `SkillRun` and adjacent runtime artifacts can become the authoritative input for later consolidation

Tasks:
- complete canonical `SkillRun` runtime path
- preserve `correlation_id`, mission linkage, evaluation linkage, and artifact refs
- reduce parallel execution ambiguity across mission/task/runtime paths

Dependency:
- main roadmap Epic 5 and Epic 8

---

## Phase D2 - Consolidation Layer Introduction

### Milestone D2.1 - Experience Record

Goal:
- introduce `ExperienceRecord` as the minimal bridge between runtime and durable learning

Tasks:
- define schema and storage
- ingest from `SkillRun`, mission bridge, task queue, evaluation, and memory promotion hooks
- preserve provenance to audit and runtime artifacts

Expected result:
- one durable record of experience per governed execution unit

### Milestone D2.2 - Insight Candidate

Goal:
- derive bounded, evidence-backed insight candidates from experiences

Tasks:
- add distillation rules
- define confidence and scope fields
- define validation states (`proposed`, `provisional`, `validated`, `rejected`)

Expected result:
- first-class insight artifacts instead of only logs and summaries

---

## Phase D3 - Deliberation-Aware Mission Layer

### Milestone D3.1 - Deliberation Summary

Goal:
- add a bounded structured summary of mission/skill reasoning without storing raw chain-of-thought

Tasks:
- define `DeliberationSummary` shape
- capture alternatives, rationale, uncertainty, failure modes, open tensions
- connect summary to `ExperienceRecord`

### Milestone D3.2 - Tension Modeling

Goal:
- preserve productive contradictions as structured artifacts

Tasks:
- define `MissionHypothesis`, `MissionPerspective`, `MissionTension`
- support unresolved tensions as valid outputs
- avoid premature collapse into one final answer

Expected result:
- mission can evolve into a shared thinking space instead of only an execution envelope

---

## Phase D4 - Pattern Formation and Promotion

### Milestone D4.1 - Pattern Candidate

Goal:
- aggregate repeated insight candidates into reusable patterns

Tasks:
- define support thresholds
- track recurrence, failure modes, and applicability scope
- connect pattern candidates to knowledge promotion rules

### Milestone D4.2 - Knowledge Promotion

Goal:
- promote only validated, governed patterns into stable knowledge

Tasks:
- define `KnowledgePromotionRecord`
- use evaluation, governance, and provenance as gates
- support supersession and rollback

Expected result:
- Knowledge Layer receives curated artifacts instead of raw runtime output

---

## Phase D5 - Meta-Cognition and Skill Evolution

### Milestone D5.1 - Evolution Proposals

Goal:
- turn selected patterns into governed proposals for skill improvement

Tasks:
- define `EvolutionProposal`
- scope first to skill-level evolution, not capability mutation
- require validation runs before promotion

### Milestone D5.2 - Selection Signals

Goal:
- define the multi-signal promotion logic for insight and pattern selection

Tasks:
- combine evaluation, repeatability, cost, credits, karma, and human review
- keep credits as one signal, not the only signal
- add anti-gaming and tenant/domain-aware weighting

Expected result:
- BRAiN learns under control rather than mutating from raw outcomes

---

## 3 Credit-System Track

Parallel to the deliberation work, the internal credits system should be upgraded from a budget ledger into one selectable signal source.

### Credit Track Tasks
- preserve ledger/event-sourcing strengths
- add durable signal projections
- bridge credits with karma, evaluation, governance, and promotion records
- avoid overloading credits as the sole reputation mechanism

---

## 4 Delivery Guidance

- do not block main runtime implementation waiting for this strand
- capture architectural observations during implementation and feed them back here
- prioritize minimal durable objects over large speculative frameworks
- treat this roadmap as a living research-and-delivery strand

---

## 5 Success Condition

This strand succeeds when BRAiN can eventually do all of the following:

- preserve productive tension
- derive bounded insights from execution and mission context
- aggregate recurring insights into patterns
- promote validated patterns into stable knowledge
- use knowledge to improve future skills under governance
