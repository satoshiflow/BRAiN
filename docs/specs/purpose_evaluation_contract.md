# Purpose Evaluation Contract (v1)

Status: Draft (Phase 1 Sprint 1.2)

## Purpose

Define the canonical decision object produced after applying identity,
governance, and purpose profile constraints to a normalized decision context.

## Contract Fields

| Field | Type | Required | Notes |
|---|---|---:|---|
| `purpose_evaluation_id` | UUID | yes | Evaluation id |
| `decision_context_id` | string(160) | yes | Correlates to normalized context |
| `purpose_profile_id` | string(120) | yes | Resolved profile |
| `outcome` | enum | yes | `accept`,`reject`,`modified_accept` |
| `purpose_score` | float | yes | `0.0..1.0` |
| `sovereignty_score` | float | yes | `0.0..1.0` |
| `requires_human_review` | bool | yes | Set by policy for sensitive cases |
| `required_modifications` | string[] | no | Required when `modified_accept` |
| `reasons` | string[] | yes | Explainability notes |
| `governance_snapshot` | jsonb | yes | Policy/approval facts used |
| `tenant_id` | string(64) | yes | Auth-derived tenant |
| `mission_id` | string(120) | no | Optional mission context |
| `correlation_id` | string(160) | yes | Trace continuity |
| `created_at` | timestamptz | yes | UTC |

## Validation Rules

- `modified_accept` requires at least one `required_modifications` item.
- `reject` requires at least one reason tied to governance or purpose mismatch.
- `tenant_id` must be auth-derived and immutable within one decision chain.
- `requires_human_review` is set by policy/approval semantics, not user payload.

## Outcome Semantics

- `accept`: continue to task/domain/routing decision flow.
- `reject`: terminate routing path with governed denial artifact.
- `modified_accept`: continue only after applying declared modifications.

## Error Codes

- `PE-001 INVALID_OUTCOME`
- `PE-002 MISSING_REQUIRED_MODIFICATIONS`
- `PE-003 TENANT_MISMATCH`
- `PE-004 MISSING_GOVERNANCE_SNAPSHOT`

## Minimal API Structure

- `POST /api/v1/purpose/evaluate`
- `GET /api/v1/purpose/evaluations/{purpose_evaluation_id}`
- `GET /api/v1/purpose/evaluations?mission_id={mission_id}`

Creation requires auth and audit emission for sensitive flows.

## Event Types

- `purpose.evaluation.created.v1`
- `purpose.evaluation.rejected.v1`
- `purpose.evaluation.modified_accept.v1`
- `purpose.evaluation.human_review_required.v1`

## Storage

- PostgreSQL: durable evaluation records for traceability
- Redis: optional short-lived read projection
- EventStream: evaluation and escalation events
