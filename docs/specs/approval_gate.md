# ApprovalGate Specification (v1)

Status: Draft for Epic 2  
Scope: Durable human approval or breakglass gate for a `SkillRun`.

## Purpose

`ApprovalGate` binds a human decision to one specific `SkillRun` attempt and one specific policy snapshot.

## Fields

| Field | Type | Required | Notes |
|---|---|---:|---|
| `id` | UUID | yes | Approval gate id |
| `tenant_id` | string(64) | yes | Token-derived tenant |
| `skill_run_id` | UUID | yes | FK to `SkillRun` |
| `policy_decision_id` | UUID | yes | FK to `PolicyDecision` |
| `gate_type` | enum | yes | `approval`,`breakglass` |
| `status` | enum | yes | `pending`,`approved`,`rejected`,`expired`,`cancelled` |
| `requested_by` | string(120) | yes | Original requester |
| `requested_at` | timestamptz | yes | UTC |
| `expires_at` | timestamptz | yes | Hard TTL |
| `decided_by` | string(120) | no | Human approver/rejector |
| `decided_at` | timestamptz | no | UTC |
| `decision_reason` | text | no | Rejection or override reason |
| `justification` | text | conditional | Required for breakglass |
| `incident_ref` | string(120) | conditional | Required for breakglass |
| `intent_hash` | string(64) | yes | Hash of normalized run intent |
| `policy_snapshot_hash` | string(64) | yes | Must match linked decision |
| `token_hash` | string(128) | no | Optional one-time approval token hash |
| `token_used_at` | timestamptz | no | Token consumption time |
| `correlation_id` | string(120) | yes | Trace continuity |

## Lifecycle

`pending -> approved|rejected|expired|cancelled`

Rules:
- Terminal states are immutable.
- Approval artifacts are single-use.
- `retry` never reuses an older `ApprovalGate`.

## Validation Rules

- `tenant_id`, `skill_run_id`, and linked `PolicyDecision` must match.
- `decided_by` must not equal `requested_by`.
- `expires_at > requested_at`.
- Breakglass requires `gate_type=breakglass`, `incident_ref`, and `justification`.
- Raw approval tokens must never be persisted.
- `intent_hash` must match the normalized run intent being approved.

## Error Codes

- `AG-001 RUN_NOT_FOUND`
- `AG-002 TENANT_MISMATCH`
- `AG-003 SELF_APPROVAL_FORBIDDEN`
- `AG-004 GATE_NOT_PENDING`
- `AG-005 GATE_EXPIRED`
- `AG-006 TOKEN_REPLAY_DETECTED`
- `AG-007 INTENT_HASH_MISMATCH`
- `AG-008 BREAKGLASS_FIELDS_REQUIRED`

## Minimal API Structure

- `GET /api/v1/skill-runs/{id}/approval-gate`
- `GET /api/v1/approval-gates?status=pending`
- `POST /api/v1/skill-runs/{id}/approve`
- `POST /api/v1/skill-runs/{id}/reject`
- `POST /api/v1/skill-runs/{id}/breakglass`

Role/Scope baseline:
- approve/reject: human `admin` + `skill_runs:approve`
- breakglass: human `admin` + `skill_runs:breakglass`
- read: authenticated principal + `skill_runs:read` within same tenant

Endpoint/gate-type rules:
- `/approve` and `/reject` are valid only for `gate_type=approval`.
- `/breakglass` is valid only for `gate_type=breakglass`.
- `breakglass` must never be implemented as a synonym for normal approval.

## Event Types

- `skill.run.approval.required.v1`
- `skill.run.approval.approved.v1`
- `skill.run.approval.rejected.v1`
- `skill.run.approval.expired.v1`
- `skill.run.breakglass.requested.v1`
- `skill.run.breakglass.approved.v1`
- `skill.run.breakglass.denied.v1`

## Storage and Runtime Placement

- PostgreSQL (durable): canonical approval/breakglass object.
- Redis (ephemeral): token replay cache, pending count cache, reminder scheduling.
- EventStream: notification of gate lifecycle changes.

## Security Notes

- Approval must be atomic and consume the gate exactly once.
- Approval events and audit records must share the same `correlation_id`.
- Approval after expiry, cancellation, or prior consumption is forbidden.
