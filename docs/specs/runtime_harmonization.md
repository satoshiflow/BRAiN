# Runtime Harmonization Specification (v1)

Status: Baseline implemented and stabilized (2026-03-08)  
Scope: Aligns Mission, SkillRun, Task Queue, and legacy mission runtime into one canonical execution model.

## Purpose

BRAiN currently contains multiple overlapping execution paths.

This spec defines the harmonized model:

`Mission -> SkillRun -> TaskLease`

Where:
- `Mission` is an optional demand/envelope object
- `SkillRun` is the canonical execution record
- `TaskLease` is an optional worker dispatch/claim mechanism

## Repo Alignment

- Legacy runtime: `backend/modules/missions/`
- App missions: `backend/app/modules/missions/`
- Queue substrate: `backend/app/modules/task_queue/`
- Existing compat boundary: `backend/app/compat/legacy_missions.py`

## Canonical Ownership

- `Mission` owns intent packaging and higher-level business request context
- `SkillRun` owns exact governed execution
- `TaskLease` owns ephemeral worker claim/dispatch only

`TaskLease` must never become the canonical business execution record.

## Harmonized Model

### Mission
- optional wrapper
- may fan out into one or more `SkillRun`s
- remains useful for business workflows and external tracking

### SkillRun
- exact skill version
- exact capability/provider snapshots
- exact policy/approval evidence
- canonical status transitions

### TaskLease
- queue/claim/heartbeat/cancel substrate
- ephemeral worker scheduling concept
- reconstructible from `SkillRun` state

## Migration Rules

- No new feature should target legacy mission worker paths directly.
- Legacy mission runtime may remain behind compatibility adapters during migration.
- App `missions` template CRUD remains distinct from canonical execution ownership.
- Task queue integration must be subordinate to `SkillRun` source of truth.

## Cutover Principles

- freeze legacy path expansion
- introduce adapter-backed coexistence
- move writes to canonical runtime first
- move reads/projections second
- retire legacy writers last

## Read/Write Path Rules

### Canonical writes
- `SkillRun`
- Constitution Gate artifacts
- evaluation artifacts

Required bridge fields for compatibility paths:
- `skill_run_id`
- `mission_id` when present
- `correlation_id`
- `tenant_id`

### Compatibility writes
- `Mission` may create `SkillRun`
- `TaskQueue` may create/refresh `TaskLease` only

### Deprecated writes
- direct legacy mission execution writes outside canonical runtime

## API Shape

- `POST /api/v1/missions` may remain as an envelope entrypoint
- `POST /api/v1/skill-runs` remains canonical execution entrypoint
- task queue APIs become worker-facing scheduling surfaces, not primary business execution APIs

## Audit and Event Requirements

- every Mission->SkillRun conversion must preserve `correlation_id`
- every TaskLease must reference `skill_run_id`
- legacy adapter invocations must emit compatibility events marking bridged execution

Events:
- `mission.skillrun.created.v1`
- `tasklease.created.v1`
- `tasklease.claimed.v1`
- `tasklease.completed.v1`
- `runtime.legacy_bridge.used.v1`

## PostgreSQL vs Redis vs EventStream

### PostgreSQL
- canonical `Mission` and `SkillRun`
- compatibility bridge records

### Redis
- queue ordering
- leases
- heartbeats

### EventStream
- harmonization and bridge lifecycle events

## Legacy Compatibility

- `backend/modules/missions/` remains legacy-only.
- `backend/app/modules/missions/` remains template/envelope-oriented unless explicitly migrated.
- `backend/app/compat/legacy_missions.py` is the required boundary until legacy removal.

Route precedence and cutover rule:
- canonical write ownership belongs to `SkillRun` APIs once enabled
- legacy or compatibility routes may remain read-only or adapter-backed
- autodiscovery must not be allowed to create competing write owners for the same runtime object

## Done Criteria

- one canonical execution record exists (`SkillRun`)
- Mission/Task roles are explicitly narrowed
- legacy and queue paths are documented as subordinate/adapter-based
- cutover direction is explicit and non-duplicative

## Implementation Status

- `task_queue` now carries bridge ownership fields: `tenant_id`, `mission_id`, `skill_run_id`, `correlation_id`
- `POST /api/tasks/skill-runs/{run_id}/lease` now creates subordinate task leases from canonical `SkillRun` state
- supervisor and agent-management orchestration paths now read canonical `SkillRun` state rather than mission-only placeholders
- targeted orchestration tests and the RC staging gate passed after stabilization
- memory and learning ingest routes are now covered with targeted tests that verify canonical `skill_run_id` propagation into downstream runtime stores
- cleanup reduced some test-only compatibility logic in the runtime entrypoint by moving `TestClient` URL/delete normalization into test configuration
