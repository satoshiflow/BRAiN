# PolicyDecision Specification (v1)

Status: Draft for Epic 2  
Scope: Durable result of Constitution Gate policy evaluation for a `SkillRun`.

## Purpose

`PolicyDecision` is the canonical, immutable record of a gate decision made before a `SkillRun` may execute.

## Fields

| Field | Type | Required | Notes |
|---|---|---:|---|
| `id` | UUID | yes | Decision id |
| `tenant_id` | string(64) | yes | Token-derived tenant |
| `skill_run_id` | UUID | yes | FK to `SkillRun` |
| `decision` | enum | yes | `allow`,`allow_with_approval`,`deny`,`breakglass_required` |
| `reason_code` | string(80) | yes | Stable machine-readable code |
| `reason` | text | yes | Sanitized explanation |
| `risk_tier` | enum | yes | `low`,`medium`,`high`,`critical` |
| `policy_pack_ref` | string(120) | yes | Policy package id |
| `policy_version` | string(64) | yes | Evaluated bundle version |
| `policy_snapshot_hash` | string(64) | yes | Immutable digest of evaluation snapshot |
| `matched_rules` | jsonb | no | Ordered matched rule list |
| `obligations` | jsonb | no | approval/audit/breakglass directives |
| `principal_snapshot` | jsonb | yes | Reduced claim subset |
| `resource_snapshot` | jsonb | yes | Skill/version/risk |
| `context_snapshot` | jsonb | yes | Hashes, trigger, cost, deadline |
| `correlation_id` | string(120) | yes | Trace continuity |
| `created_at` | timestamptz | yes | UTC |
| `created_by` | string(120) | yes | Principal id |

## Lifecycle

`created` only.

Rules:
- `PolicyDecision` is immutable after write.
- Re-evaluation creates a new record, never updates the old one.

## Validation Rules

- `skill_run_id` must exist and match `tenant_id`.
- `policy_snapshot_hash` must be computed from normalized evaluation inputs.
- `matched_rules` order must be deterministic.
- `decision=allow_with_approval` requires `obligations.approval_required=true`.
- `decision=breakglass_required` requires `obligations.breakglass_eligible=true`.

## Error Codes

- `PD-001 RUN_NOT_FOUND`
- `PD-002 TENANT_MISMATCH`
- `PD-003 INVALID_DECISION`
- `PD-004 SNAPSHOT_HASH_MISSING`
- `PD-005 OBLIGATION_CONFLICT`

## Minimal API Structure

- `GET /api/v1/skill-runs/{id}/policy-decision`
- `GET /api/v1/policy-decisions/{id}`

Create occurs only through Constitution Gate service path, not via direct public create endpoint.

## Event Types

- `skill.run.policy.evaluated.v1`
- `skill.run.policy.denied.v1`

## Storage and Runtime Placement

- PostgreSQL (durable): canonical immutable record.
- Redis (ephemeral): optional short-lived cache only.
- EventStream: evaluation result notification, not source of truth.

## Repo Compatibility Notes

- This object should align with existing policy schemas under `backend/app/modules/policy/` but freeze a `SkillRun`-specific snapshot for auditability.
- `reason` exposed via API must be sanitized; full evidence remains internal.
