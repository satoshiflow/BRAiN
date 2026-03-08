# SkillRun Specification (v1)

Status: Draft for Epic 1  
Scope: Runtime execution object for Skill Engine.

## Purpose

`SkillRun` captures one concrete execution of a specific skill version, including planning, provider resolution, execution state, policy decisions, and terminal outcome.

## Fields

| Field | Type | Required | Notes |
|---|---|---:|---|
| `id` | UUID | yes | Skill run id |
| `tenant_id` | string(64) | yes | Tenant/scope ownership |
| `skill_key` | string(120) | yes | Functional key |
| `skill_version` | integer | yes | Frozen version at run start |
| `state` | enum | yes | `queued`,`planning`,`waiting_approval`,`running`,`succeeded`,`failed`,`cancelled`,`timed_out` |
| `input_payload` | jsonb | yes | Validated against `input_schema` |
| `plan_snapshot` | jsonb | no | Planned execution graph/steps |
| `provider_selection_snapshot` | jsonb | no | Resolver decisions |
| `requested_by` | string(120) | yes | Principal id |
| `requested_by_type` | enum | yes | `user`,`agent`,`system` |
| `trigger_type` | enum | yes | `api`,`schedule`,`mission`,`retry` |
| `policy_decision_id` | UUID | yes | Link to policy evaluation record |
| `policy_snapshot` | jsonb | no | Denormalized decision evidence |
| `risk_tier` | enum | yes | `low`,`medium`,`high`,`critical` |
| `correlation_id` | string(120) | yes | Event/audit trace continuity |
| `causation_id` | string(120) | no | Parent event/request id |
| `idempotency_key` | string(120) | yes | Deduplicate submit requests |
| `mission_id` | string(120) | no | Optional mission linkage |
| `created_at`,`started_at`,`finished_at` | timestamptz | yes/no/no | UTC timestamps |
| `deadline_at` | timestamptz | no | Hard timeout boundary |
| `retry_count` | integer | yes | Attempt count |
| `cost_estimate`,`cost_actual` | decimal(12,4) | no | Budget tracking |
| `failure_code` | string(40) | no | Contracted error code |
| `failure_reason_sanitized` | text | no | External-safe reason |

Ephemeral runtime state (Redis):
- step progress, heartbeats, worker lease, live logs, cancellation signal.

## Lifecycle

`queued -> planning -> waiting_approval? -> running -> succeeded|failed|cancelled|timed_out`

Rules:
- Terminal states are immutable.
- Retry occurs only through explicit retry action and policy acceptance.
- `high`/`critical` risk may require `waiting_approval`.

Transition matrix (allowed):
- `queued -> planning|cancelled`
- `planning -> waiting_approval|running|failed|cancelled`
- `waiting_approval -> running|failed|cancelled`
- `running -> succeeded|failed|timed_out|cancelled`
- terminal states have no outgoing transition.

## Validation Rules

- `skill_key`+`skill_version` must reference an active/allowed definition.
- `input_payload` must validate against frozen `input_schema`.
- State transitions must be atomic and legal from previous state.
- Duplicate `idempotency_key` for same principal/tenant returns prior run.
- `deadline_at` (if set) must be in future at submission.

## Error Codes

- `SR-001 SKILL_NOT_ACTIVE`
- `SR-002 INVALID_INPUT`
- `SR-003 POLICY_DENIED`
- `SR-004 APPROVAL_REQUIRED`
- `SR-005 PROVIDER_UNAVAILABLE`
- `SR-006 STATE_CONFLICT`
- `SR-007 DEADLINE_EXCEEDED`
- `SR-008 CANCELLED`

## Minimal API Structure

- `POST /api/v1/skill-runs`
- `GET /api/v1/skill-runs/{id}`
- `GET /api/v1/skill-runs?state={state}&skill_key={skill_key}`
- `POST /api/v1/skill-runs/{id}/cancel`
- `POST /api/v1/skill-runs/{id}/retry`
- `POST /api/v1/skill-runs/{id}/approve`
- `POST /api/v1/skill-runs/{id}/reject`

All writes require auth, policy gate, and audit emission.

Role/Scope baseline:
- Create/cancel/retry: `operator` or `admin` role + `skill_runs:write`.
- Approve/reject: `admin` role + `skill_runs:approve`.
- Read: authenticated principal + `skill_runs:read`.
- `tenant_id` is token-derived; cross-tenant access forbidden unless explicit admin cross-tenant scope exists.

## Event Types

- `skill.run.created.v1`
- `skill.run.planning.started.v1`
- `skill.run.approval.required.v1`
- `skill.run.started.v1`
- `skill.run.progress.v1`
- `skill.run.completed.v1`
- `skill.run.failed.v1`
- `skill.run.cancelled.v1`
- `skill.run.timed_out.v1`

## Storage and Runtime Placement

- PostgreSQL (durable): full run record and state transitions.
- Redis (ephemeral): runtime orchestration details and quick status stream.
- EventStream: all state transitions for observability and downstream workflows.

Durability note:
- For mutating transitions, persist state in PostgreSQL first, then publish event via outbox-compatible path to avoid silent event loss.
