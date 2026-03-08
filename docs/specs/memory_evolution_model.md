# Memory and Evolution Model Specification (v1)

Status: Draft for Epic 10  
Scope: Consolidates memory, DNA, genesis, integrity, and quarantine around canonical execution history.

## Purpose

This spec defines how BRAiN learns and evolves from `SkillRun` execution without creating multiple competing sources of truth.

## Canonical Principle

`SkillRun` and its durable artifacts are the anchor. Memory, DNA, and evolution layers project from that anchor.

## Repo Alignment

- Existing modules: `memory`, `dna`, `genesis`, `genetic_integrity`, `genetic_quarantine`
- Existing issue: DNA/genesis and some protection services still allow in-memory-oriented behavior

## Canonical History Object

The model requires one canonical execution history anchor, conceptually:
- `skill_run_id`
- `agent_id`
- `snapshot_version`
- `memory_refs`
- `evaluation_refs`
- `quarantine_state`
- `correlation_id`

This object may be implemented as a dedicated history record or a normalized cross-module projection.

## Memory Views

- `working_memory`: ephemeral and short-lived
- `episodic_memory`: run-linked execution memories
- `semantic_memory`: derived memory projection of reusable knowledge patterns, not the canonical knowledge source of truth
- `procedural_memory`: reusable execution patterns and learned strategies

The primary anchor for all durable memory views is `skill_run_id`.

Knowledge separation rule:
- Canonical durable knowledge objects belong to the Knowledge Layer.
- Semantic memory may cache, summarize, or project knowledge-relevant patterns, but must not become the authoritative knowledge record.

## Evolution Components

### DNA
- lineage
- inheritance metadata
- variant ancestry

### Genesis
- controlled creation of new skills, agents, templates, or variants

### Genetic Integrity
- stability checks before promotion

### Quarantine
- isolation of unsafe or degraded variants/behaviors

## Governance Rules

- No canonical mutation/quarantine state may exist only in memory.
- Integrity and quarantine state changes require durable audit and events.
- In-memory fallbacks are not acceptable as final source-of-truth behavior for governed evolution states.
- `tenant_id` for durable evolution writes is token-derived or system-derived, never request-body authoritative.

## API Surface

- `GET /api/v1/memory/skill-runs/{skill_run_id}`
- `GET /api/v1/evolution/lineage/{entity_id}`
- `POST /api/v1/evolution/variants`
- `POST /api/v1/quarantine/{entity_id}`
- `POST /api/v1/quarantine/{entity_id}/release`

## Audit and Event Requirements

- `memory.episodic.recorded.v1`
- `evolution.variant.created.v1`
- `genetic.integrity.checked.v1`
- `genetic.quarantine.applied.v1`
- `genetic.quarantine.released.v1`

## PostgreSQL vs Redis vs EventStream

### PostgreSQL
- durable memory records
- lineage references
- integrity outcomes
- quarantine states

### Redis
- working memory
- transient adaptive hints

### EventStream
- evolution and quarantine lifecycle events

## Legacy Compatibility

- Existing memory/session/mission anchors remain compatibility dimensions only.
- Future evolution features must anchor on canonical run history rather than free-floating in-memory service state.

## Done Criteria

- one canonical history anchor is defined
- memory views are separated clearly
- evolution and quarantine are explicitly fail-closed and durable
- in-memory fallback behavior is marked as non-target-state
