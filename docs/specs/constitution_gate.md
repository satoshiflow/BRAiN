# Constitution Gate Specification (v1)

Status: Draft for Epic 2  
Scope: Mandatory governance gate for every `SkillRun` create, retry, resume, approval, and breakglass path.

## Purpose

The Constitution Gate enforces a single fail-closed control path for `SkillRun` execution:

`authn -> authz -> tenant check -> policy evaluation -> optional approval/breakglass -> durable audit -> event publish -> execution`

No `SkillRun` may enter `running` without a valid gate decision.

## Repo Alignment

- AuthN/AuthZ source of truth: `backend/app/core/auth_deps.py`
- Policy source of truth: `backend/app/modules/policy/`
- Audit bridge: `backend/app/core/audit_bridge.py`
- Event backbone: `backend/mission_control_core/core/event_stream.py`
- Governance/HITL patterns: `backend/app/modules/governance/` and `backend/app/modules/ir_governance/`

Epic 2 must extend these patterns and not introduce a parallel governance path.

## Canonical Flow

1. `SkillRun` write request arrives.
2. Principal is resolved from JWT/session.
3. `tenant_id` is derived from the authenticated principal, never from request body.
4. API-level RBAC and scope checks run.
5. Policy engine evaluates the normalized run intent.
6. A durable `PolicyDecision` is written.
7. If approval is required, a durable `ApprovalGate` is created and `SkillRun.state=waiting_approval`.
8. Audit record is written durably.
9. Runtime event is emitted through an outbox-compatible path.
10. Only after a valid gate decision may the run transition to `running`.

## Core Decisions

The gate returns exactly one of:

- `allow`
- `allow_with_approval`
- `deny`
- `breakglass_required`

## AuthN/AuthZ Matrix

| Action | Principal types | Role | Scope | Additional constraints |
|---|---|---|---|---|
| `create skill run` | `user`,`agent`,`system` | `operator` or `admin` | `skill_runs:write` | same tenant only |
| `read skill run` | authenticated | any authenticated | `skill_runs:read` | same tenant only |
| `cancel skill run` | `user`,`system` | `operator` or `admin` | `skill_runs:write` | requester or tenant admin |
| `retry skill run` | `user`,`system` | `operator` or `admin` | `skill_runs:write` | re-runs full gate |
| `approve gate` | `user` only | `admin` | `skill_runs:approve` | no self-approval |
| `reject gate` | `user` only | `admin` | `skill_runs:approve` | reason required |
| `invoke breakglass` | `user` only | `admin` | `skill_runs:breakglass` | incident + justification required |
| `list pending approvals` | `user` only | `admin` | `skill_runs:approve` | same tenant only |

Rules:
- Approval, rejection, and breakglass are forbidden for agent/system tokens.
- `approved_by` must never equal `requested_by`.
- Missing auth -> `401`; missing role/scope -> `403`.

## Tenant Isolation

- `tenant_id` is token-derived for all mutating flows.
- Cross-tenant mutation is forbidden in Epic 2.
- Every database lookup on `SkillRun`, `PolicyDecision`, `ApprovalGate`, and audit records must include `tenant_id`.
- Approval tokens and breakglass grants are tenant-bound and run-bound.

## Gate Transition Rules

### Pre-execution

- `queued -> planning`
- `planning -> running` when decision is `allow`
- `planning -> waiting_approval` when decision is `allow_with_approval` or `breakglass_required`
- `planning -> failed` when decision is `deny`

### Approval-driven

- `waiting_approval -> running` after valid approval or valid breakglass grant
- `waiting_approval -> failed` when rejected
- `waiting_approval -> failed` when expired
- `waiting_approval -> cancelled` when explicitly cancelled

### Invariants

- No transition to `running` without a durable gate artifact.
- `retry` always generates a fresh `PolicyDecision` and, if needed, a fresh `ApprovalGate`.
- Terminal pre-run failures keep `started_at = null`.

## Breakglass Rules

Breakglass is a controlled emergency override, not a normal approval path.

- Allowed only for `high` or `critical` risk tiers.
- Allowed only when policy marks the run as breakglass-eligible.
- Requires:
  - `incident_ref`
  - `justification`
  - short TTL
- Always emits critical audit/event records.
- Must be run-specific, not tenant-global.

## Emergency Freeze

A runtime emergency freeze may block transitions into `running`.

- If `emergency_freeze_active=true`, then:
  - `planning -> running` is blocked
  - `waiting_approval -> running` is blocked
- Default behavior is block-all.
- Only valid breakglass may override freeze.
- Freeze is ephemeral runtime state, not source-of-truth policy state.

## Audit Requirements

Each of the following actions must produce a durable audit record:

- run submitted
- policy evaluated
- policy denied
- approval requested
- approval approved
- approval rejected
- approval expired
- breakglass requested
- breakglass approved
- breakglass denied
- emergency freeze blocked execution
- run started after gate clearance

Mandatory audit fields:

- `tenant_id`
- `skill_run_id`
- `policy_decision_id`
- `approval_gate_id` if present
- `correlation_id`
- `causation_id` if present
- `actor_id`
- `actor_type`
- `risk_tier`
- `reason_code`
- `occurred_at`

Durability rule:

- A successful gate mutation must not complete if the durable audit write fails.

## Event Requirements

Event types:

- `skill.run.policy.evaluated.v1`
- `skill.run.policy.denied.v1`
- `skill.run.approval.required.v1`
- `skill.run.approval.approved.v1`
- `skill.run.approval.rejected.v1`
- `skill.run.approval.expired.v1`
- `skill.run.breakglass.requested.v1`
- `skill.run.breakglass.approved.v1`
- `skill.run.breakglass.denied.v1`
- `skill.run.execution.blocked.v1`
- `skill.run.started.v1`

Event compatibility note:

- During transition, `.v1` event names may be mirrored to repo-compatible legacy aliases if required by consumers.
- `schema_version` must be carried in `data.schema_version` until runtime envelope is extended.
- Runtime integration must register these events in the canonical EventStream taxonomy before they are treated as first-class event types.

## Minimal API Surface

- `POST /api/v1/skill-runs`
- `GET /api/v1/skill-runs/{id}`
- `GET /api/v1/skill-runs/{id}/policy-decision`
- `GET /api/v1/skill-runs/{id}/approval-gate`
- `GET /api/v1/approval-gates?status=pending`
- `POST /api/v1/skill-runs/{id}/approve`
- `POST /api/v1/skill-runs/{id}/reject`
- `POST /api/v1/skill-runs/{id}/breakglass`
- `POST /api/v1/skill-runs/{id}/cancel`
- `POST /api/v1/skill-runs/{id}/retry`

Idempotency rules:

- `approve`, `reject`, and `breakglass` must be idempotent.
- Duplicate mutation with incompatible payload returns conflict.

## Error Codes

| Code | HTTP | Meaning |
|---|---:|---|
| `CG-001 AUTH_REQUIRED` | 401 | Principal missing/invalid |
| `CG-002 FORBIDDEN` | 403 | Role or scope missing |
| `CG-003 TENANT_MISMATCH` | 403 | Cross-tenant access attempted |
| `CG-004 POLICY_DENIED` | 403 | Policy forbids execution |
| `CG-005 APPROVAL_REQUIRED` | 202/409 | Run parked in `waiting_approval` |
| `CG-006 APPROVAL_NOT_PENDING` | 409 | Gate already decided/cancelled |
| `CG-007 APPROVAL_REJECTED` | 409 | Human rejected gate |
| `CG-008 APPROVAL_EXPIRED` | 409 | Gate expired |
| `CG-009 BREAKGLASS_SCOPE_REQUIRED` | 403 | Breakglass privilege missing |
| `CG-010 BREAKGLASS_NOT_ALLOWED` | 403 | Decision not overrideable |
| `CG-011 EMERGENCY_FREEZE_ACTIVE` | 423 | Freeze blocks start |
| `CG-012 IDEMPOTENCY_CONFLICT` | 409 | Duplicate mutate request with different payload |
| `CG-013 TOKEN_REPLAY_DETECTED` | 409 | Approval token already consumed |
| `CG-014 STATE_CONFLICT` | 409 | Illegal state transition |

## PostgreSQL vs Redis Responsibilities

### PostgreSQL

- canonical `SkillRun`
- canonical `PolicyDecision`
- canonical `ApprovalGate`
- immutable transition history
- durable audit records
- outbox rows for event publication

Integration rule:

- Gate decision, approval consumption, durable audit, and outbox write must be part of one transactional persistence boundary.

### Redis

- worker leases / locks
- pending approval counters
- websocket fanout / live status
- approval token replay cache (TTL)
- emergency freeze flags
- reminder/timer primitives

Rules:

- No canonical governance state may live only in Redis.
- PostgreSQL commit happens before event publish.
- Redis state must be reconstructible from PostgreSQL.

## Done Criteria

- One documented fail-closed gate path exists for all `SkillRun` write actions.
- Auth, scope, tenant, policy, approval, audit, and event requirements are all explicit.
- Approval and breakglass rules are tenant-safe and idempotent.
- Redis/PostgreSQL ownership is explicit.
- Spec is compatible with Epic 1 contracts and existing BRAiN auth/policy/audit modules.
