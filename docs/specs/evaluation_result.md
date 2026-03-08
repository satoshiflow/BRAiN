# EvaluationResult Specification (v1)

Status: Draft for Epic 1  
Scope: Quality/compliance evaluation object linked to a SkillRun.

## Purpose

`EvaluationResult` stores measurable execution quality, pass/fail decisions, and policy compliance outcomes for one `SkillRun`.

## Fields

| Field | Type | Required | Notes |
|---|---|---:|---|
| `id` | UUID | yes | Evaluation id |
| `tenant_id` | string(64) | yes | Tenant/scope ownership |
| `skill_run_id` | UUID | yes | FK to `SkillRun` |
| `skill_key` | string(120) | yes | Frozen skill identity |
| `skill_version` | integer | yes | Frozen skill version |
| `evaluator_type` | enum | yes | `rule`,`model`,`human`,`hybrid` |
| `status` | enum | yes | `pending`,`completed`,`failed`,`skipped` |
| `overall_score` | decimal(5,4) | conditional | Required for `completed` |
| `dimension_scores` | jsonb | no | Per-criterion scores |
| `pass` | boolean | conditional | Required for `completed` |
| `criteria_snapshot` | jsonb | yes | Frozen criteria used in evaluation |
| `findings` | jsonb | no | Observations and issues |
| `recommendations` | jsonb | no | Improvement suggestions |
| `metrics_summary` | jsonb | yes | KPI projection from run results |
| `provider_selection_snapshot` | jsonb | yes | Frozen provider bindings used by the run |
| `error_classification` | enum/string | no | Baseline class such as `execution_error` |
| `policy_compliance` | enum | yes | `compliant`,`non_compliant`,`unknown` |
| `policy_violations` | jsonb | no | Violation details |
| `correlation_id` | string(160) | no | Shared lifecycle correlation handle |
| `evaluation_revision` | integer | yes | Starts at `1`; later corrections append new revisions |
| `created_at`,`completed_at` | timestamptz | yes/no | UTC |
| `created_by` | string(120) | yes | Principal/system id |

## Lifecycle

`pending -> completed|failed|skipped`

Rules:
- `completed` records are immutable.
- Corrections require a new evaluation revision record.

## Validation Rules

- `skill_run_id` must reference existing `SkillRun`.
- `overall_score` must be between `0.0` and `1.0`.
- `completed` requires both `overall_score` and `pass`.
- `policy_compliance=non_compliant` requires at least one violation item.
- `dimension_scores` keys must exist in `criteria_snapshot`.
- `provider_selection_snapshot` must reflect the frozen run provider bindings, not mutable live bindings.
- `correlation_id` should match the linked `SkillRun` correlation id when present.

## Error Codes

- `ER-001 RUN_NOT_FOUND`
- `ER-002 INVALID_SCORE_RANGE`
- `ER-003 MISSING_CRITERIA_DIMENSION`
- `ER-004 IMMUTABLE_RESULT`
- `ER-005 POLICY_INCONSISTENT`

## Minimal API Structure

- `POST /api/v1/evaluation-results`
- `GET /api/v1/evaluation-results/{id}`
- `GET /api/v1/skill-runs/{skill_run_id}/evaluation-results`

Write endpoints require role checks and audit events.

Role/Scope baseline:
- Create/complete/fail evaluation: `operator` or `admin` role + `evaluation:write`.
- Mark non-compliance override: `admin` role + `evaluation:govern`.
- Read: authenticated principal + `evaluation:read`.
- `tenant_id` is token-derived; cross-tenant mutation forbidden.

## Event Types

- `evaluation.result.created.v1`
- `evaluation.result.completed.v1`
- `evaluation.result.failed.v1`
- `evaluation.result.non_compliant.v1`

## Storage and Runtime Placement

- PostgreSQL (durable): canonical evaluation records.
- Redis (ephemeral): optional evaluator work queue and short-lived progress only.
- EventStream: evaluation lifecycle and compliance alerts.

Compliance note:
- `policy_compliance=non_compliant` must emit both evaluation event and audit event with same `correlation_id`.
