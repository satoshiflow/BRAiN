# Knowledge Layer Specification (v1)

Status: Draft for Epic 9  
Scope: Durable, governed, versioned knowledge layer distinct from memory and runtime telemetry.

## Purpose

The Knowledge Layer stores long-lived, queryable, governance-safe knowledge such as:
- architecture records
- decisions
- contracts
- run lessons
- change logs
- validated documentation facts

It is not a substitute for runtime memory.

## Repo Alignment

- Existing precursor: `backend/app/modules/knowledge_graph/`
- New docs basis: `docs/knowledge/brain_knowledge_layer.md`

## Ownership Boundaries

Knowledge Layer owns:
- durable knowledge objects
- versioning and validity windows
- provenance and ownership metadata
- governance-aware ingestion and updates

Knowledge Layer does not own:
- short-lived working memory
- raw live execution state
- provider health telemetry

## Core Object Classes

- `knowledge_item`
- `decision_record`
- `contract_record`
- `run_lesson`
- `documentation_record`

## Required Metadata

Every knowledge object must include:
- `id`
- `tenant_id`
- `type`
- `title`
- `source`
- `version`
- `owner`
- `tags`
- `module`
- `created_at`
- `valid_until` (optional)
- `content`
- `provenance_refs`

## Ingestion Sources

- approved documentation updates
- skill/evaluation summaries
- approved architecture decisions
- audited runtime lessons

## Query Modes

- exact lookup
- structured filtering
- semantic retrieval
- provenance-aware history lookup

## Governance Rules

- Knowledge writes require auth and governance-compatible permissions.
- Knowledge items carrying runtime lessons must reference durable source artifacts.
- Knowledge is tenant-scoped by default.
- Cross-tenant knowledge sharing is out of scope unless explicitly published as `system` knowledge.
- `tenant_id` for writes is token-derived and must not be request-body authoritative.

## Relation to Memory

- Memory is execution-oriented and adaptive.
- Knowledge is curated, durable, versioned, and referenceable.
- Memory may project into knowledge only through governed ingestion or summarization paths.

## API Surface

- `POST /api/v1/knowledge-items`
- `GET /api/v1/knowledge-items/{id}`
- `GET /api/v1/knowledge/search`
- `POST /api/v1/knowledge-items/{id}/supersede`

## Audit and Event Requirements

- `knowledge.item.created.v1`
- `knowledge.item.updated.v1`
- `knowledge.item.superseded.v1`
- `knowledge.run_lesson.ingested.v1`

Durable audit required for all writes and supersede operations.

## PostgreSQL vs Redis vs EventStream

### PostgreSQL
- canonical knowledge records
- provenance references
- supersession links

### Redis
- query cache only

### EventStream
- knowledge lifecycle notifications

## Legacy Compatibility

- Existing `knowledge_graph` remains a precursor/query adapter.
- New knowledge contracts must not be forced into the current memory-centric graph model if that harms durability or governance.
- Until cutover, `knowledge_graph` may remain a query or ingest compatibility layer, but canonical durable write ownership belongs to the new knowledge-layer contract.

## Done Criteria

- knowledge is clearly separated from memory
- required metadata and provenance rules are explicit
- ingestion/query modes are explicit
- knowledge ownership and governance are documented
