# Economy Selection Support MVP

Status: Active
Date: 2026-03-09

## Scope

Economy influences prioritization only. It never applies or mutates skills directly.

## Core Object

- `EconomyAssessment`
  - Fields: `id`, `tenant_id`, `discovery_proposal_id`, `skill_run_id`, `status`, `confidence_score`, `frequency_score`, `impact_score`, `cost_score`, `weighted_score`, `score_breakdown`, `created_at`, `updated_at`

## Scoring Dimensions

- `confidence`
- `frequency`
- `impact`
- `cost`

Weighted score is used to rank review queues and refine discovery priority.

## APIs

- `POST /api/economy/proposals/{proposal_id}/analyze`
- `GET /api/economy/assessments/{assessment_id}`
- `POST /api/economy/assessments/{assessment_id}/queue-review`

## Auth / Role / Scope Matrix

- Analyze: `operator | admin | SYSTEM_ADMIN`
- Get: authenticated principal with tenant context
- Queue review: `admin | SYSTEM_ADMIN`

## Guardrails

- Tenant context required (`403`)
- Lifecycle write guard for mutating economy endpoints (`409`)
- Economy updates discovery/evolution metadata for ranking only
- No automatic transition to `applied`; `evolution_control` governance rules remain authoritative

## Anti-Gaming Baseline

- Scores are bounded to `[0, 1]`
- Inputs are evidence-derived and tenant-bound
- Breakdown payload persists dimension and weight components for transparency

## Storage Ownership

- PostgreSQL: `economy_assessments`
- Redis/EventStream: not required for MVP scoring path
