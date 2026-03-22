# Epic 2 Memory Contract

Status: Active
Date: 2026-03-22

## Purpose

Define a strict split between short-term operational memory and durable long-term memory while preserving a canonical learning provenance chain.

## Memory split

- Short-term memory (ephemeral)
  - owner: runtime/session operations
  - storage: Redis/read models where possible
  - lifecycle: TTL/retention driven
  - truth level: non-canonical

- Long-term memory (durable)
  - owner: evaluation/experience/knowledge pipeline
  - storage: PostgreSQL
  - lifecycle: governed persistence, archival, supersession
  - truth level: canonical

## Canonical chain

- `SkillRun.id` -> `EvaluationResult.skill_run_id`
- `ExperienceRecord.skill_run_id` + `ExperienceRecord.evaluation_result_id`
- `KnowledgeItem.skill_run_id` + `KnowledgeItem.experience_record_id` + `KnowledgeItem.evaluation_result_id`

This chain is mandatory for durable run lessons and governed self-learning inputs.

## Runtime rules

- `SkillRun.evaluation_summary` remains projection only.
- Durable learning artifacts must resolve back to canonical run/evaluation identifiers.
- AXE session/chat context remains a frontdoor operational context and does not become durable truth by itself.

## Retention and pruning

- Ephemeral operational context: TTL-based pruning.
- Durable records: no implicit deletion; use governance-led archival/supersession.
- Operational session TTL is configurable through `MEMORY_SESSION_TTL_HOURS` and enforced by memory maintenance.

## Phase 2 implementation notes

- Added durable link fields:
  - `experience_records.evaluation_result_id`
  - `knowledge_items.skill_run_id`
  - `knowledge_items.experience_record_id`
  - `knowledge_items.evaluation_result_id`
- Migration: `backend/alembic/versions/041_epic2_memory_contract_links.py`
