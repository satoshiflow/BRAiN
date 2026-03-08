# Skill Engine MVP Specification (v1)

Status: Draft for Epic 5  
Scope: Minimal end-to-end runtime for executing `SkillRun` through the BRAiN Skill Engine.

## Purpose

`SkillEngine` is the runtime core that turns resolved skill definitions into governed executions.

It must map the BRAiN execution standard to runtime phases:
- Grounding
- Execution
- Evaluation
- Finalization

## Repo Alignment

- Standard: `docs/core/brain_skill_execution_standard.md`
- Planning references: `backend/app/modules/planning/`
- Queue references: `backend/app/modules/task_queue/`
- Runtime contracts: `docs/specs/skill_run.md`, `docs/specs/constitution_gate.md`

## Ownership Boundaries

`SkillEngine` owns:
- orchestrating phase flow for one `SkillRun`
- freezing resolved inputs before execution
- coordinating capability adapter calls
- handing off to evaluator/finalization

`SkillEngine` does not own:
- registry lifecycle
- provider binding governance
- approval policy source of truth
- long-term optimization decisions

## Canonical Phase Mapping

| Standard phase | SkillRun phase | Engine responsibility |
|---|---|---|
| `GROUNDING` | `queued -> planning` | validate inputs, resolve skill/capabilities/providers, freeze snapshots |
| `EXECUTION` | `running` | execute plan via capability adapters |
| `EVALUATION` | post-run evaluation | create `EvaluationResult` |
| `FINALIZATION` | terminalization | persist outputs, audit, publish events, update projections |

## Required Frozen Snapshots

Before `running`, the engine must freeze:
- exact `skill_key + skill_version`
- exact resolved capability versions
- selected `provider_binding_id`s
- `policy_decision_id`
- `policy_snapshot_hash`
- `plan_snapshot`

## State Model

The engine uses `SkillRun` as canonical execution object.

Core states:
- `queued`
- `planning`
- `waiting_approval`
- `running`
- `succeeded`
- `failed`
- `cancelled`
- `timed_out`

## Execution Rules

- No execution begins without a valid Constitution Gate decision.
- Planning output must be frozen before first capability invocation.
- Every capability step must be attributable to one `skill_run_id` and one `correlation_id`.
- Existing `task_queue` may be used as dispatch substrate, but must not become a second source of truth.
- Intermediate `draft_result` exists only as a transient execution artifact until evaluation/finalization completes.

## Retry and Fallback Rules

- Adapter-local retry occurs first.
- Engine-level fallback occurs second.
- Engine-level replan is optional and bounded.
- `max_review_cycles = 3` remains the default upper bound for correction/evaluation loops.

## API Surface

- `POST /api/v1/skill-runs`
- `GET /api/v1/skill-runs/{id}`
- `POST /api/v1/skill-runs/{id}/cancel`
- `POST /api/v1/skill-runs/{id}/retry`
- Approval, rejection, and breakglass remain on the canonical Constitution Gate API surface:
  - `POST /api/v1/skill-runs/{id}/approve`
  - `POST /api/v1/skill-runs/{id}/reject`
  - `POST /api/v1/skill-runs/{id}/breakglass`

No separate public "execute skill engine" endpoint is required beyond `SkillRun` APIs.

## Audit and Event Requirements

Required events:
- internal engine/tracing events may use:
  - `skill.engine.planning.started.v1`
  - `skill.engine.execution.started.v1`
  - `skill.engine.execution.completed.v1`
  - `skill.engine.execution.failed.v1`
  - `skill.engine.finalized.v1`

Canonical external runtime events remain the `skill.run.*` and Constitution Gate events defined in Epic 1/2.

Required durable audit for:
- transition into `running`
- transition into terminal state
- fallback activation
- bounded replan activation

Durability rule:
- durable state change, durable audit, and outbox insert must complete before publish of canonical runtime events.

## PostgreSQL vs Redis vs EventStream

### PostgreSQL
- canonical `SkillRun`
- frozen snapshots
- terminal outputs metadata
- durable phase transitions

### Redis
- worker lease
- progress stream
- cancellation flag
- transient queue hints

### EventStream
- phase transitions
- operational execution notifications

## Determinism and Replay

- Replay must be able to reconstruct the exact execution inputs from frozen snapshots.
- `as_of` resolution and exact version references must make historical re-run auditable.
- In-flight runs never change their definition/provider version after `running` begins.

## Evaluation and Finalization Rule

- `succeeded` must only be set after execution output has passed required evaluation and finalization steps.
- Failed evaluation may trigger bounded correction/review cycles or end in terminal `failed`, but must not silently produce `succeeded`.

## Legacy Compatibility

- Existing mission/task runtimes are migration substrates only.
- The Skill Engine must not become another parallel runtime beside legacy missions and task queue.

## Done Criteria

- one end-to-end SkillRun runtime path is documented
- standard phases map to runtime phases
- frozen snapshots are mandatory before execution
- retry/fallback/replan responsibilities are explicit
- queue usage is subordinate to SkillRun source of truth
