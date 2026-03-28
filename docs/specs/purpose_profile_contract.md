# Purpose Profile Contract (v1)

Status: Draft (Phase 1 Sprint 1.1)

## Purpose

Define governed, reusable purpose profiles that can be selected by BRAiN before
domain/routing/execution decisions.

## Contract Fields

| Field | Type | Required | Notes |
|---|---|---:|---|
| `purpose_profile_id` | string(120) | yes | Stable key |
| `version` | integer | yes | Monotonic profile version |
| `status` | enum | yes | `draft`,`review`,`active`,`deprecated`,`retired` |
| `scope` | enum | yes | `global`,`domain_extension` |
| `domain_key` | string(100) | no | Required when `scope=domain_extension` |
| `name` | string(200) | yes | Human-readable title |
| `purpose_class` | string(80) | yes | e.g. `delivery`,`repair`,`research` |
| `core_intent` | text | yes | Canonical intent |
| `identity_alignment_rules` | string[] | yes | Must align with identity contract |
| `allowed_execution_modes` | string[] | yes | `local_worker`,`bounded_external_worker`,`hybrid` |
| `disallowed_outcomes` | string[] | yes | Forbidden outcomes |
| `default_risk_posture` | enum | yes | `low`,`medium`,`high`,`critical` |
| `governance_refs` | string[] | yes | Contract refs (`constitution_gate`, etc.) |
| `metadata` | jsonb | no | Optional extension surface |
| `updated_by` | string | yes | Principal/actor id |
| `updated_at` | timestamptz | yes | UTC |

## Validation Rules

- Global profile IDs are unique across active versions.
- Domain extension profile IDs are unique per `domain_key` and version.
- `scope=domain_extension` requires `domain_key`.
- `allowed_execution_modes` cannot allow unbounded external autonomy.
- `governance_refs` must reference active governance contracts.

## Lifecycle

`draft -> review -> active -> deprecated -> retired`

Rules:
- only one active version per `purpose_profile_id`
- activation requires governance approval for sensitive classes

## Error Codes

- `PP-001 DUPLICATE_ACTIVE_VERSION`
- `PP-002 INVALID_SCOPE_DOMAIN_COMBINATION`
- `PP-003 INVALID_EXECUTION_MODE`
- `PP-004 INVALID_GOVERNANCE_REFERENCE`
- `PP-005 ILLEGAL_STATE_TRANSITION`

## Minimal API Structure

- `GET /api/v1/purpose-profiles`
- `GET /api/v1/purpose-profiles/{purpose_profile_id}`
- `POST /api/v1/purpose-profiles` (create draft)
- `POST /api/v1/purpose-profiles/{purpose_profile_id}/versions/{version}/submit-review`
- `POST /api/v1/purpose-profiles/{purpose_profile_id}/versions/{version}/activate`
- `POST /api/v1/purpose-profiles/{purpose_profile_id}/versions/{version}/deprecate`

Mutations require auth + governance privileges + audit emission.

## Event Types

- `purpose.profile.created.v1`
- `purpose.profile.review.submitted.v1`
- `purpose.profile.activated.v1`
- `purpose.profile.deprecated.v1`

## Storage

- PostgreSQL: profile definitions and lifecycle
- Redis: optional active-profile read cache
- EventStream: lifecycle and activation events
