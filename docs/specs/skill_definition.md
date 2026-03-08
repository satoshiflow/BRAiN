# SkillDefinition Specification (v1)

Status: Draft for Epic 1  
Scope: Contract for declarative skill metadata and governance-aware activation.

## Purpose

`SkillDefinition` describes a versioned executable intent that composes one or more capabilities.

## Fields

| Field | Type | Required | Notes |
|---|---|---:|---|
| `id` | UUID | yes | Internal primary key |
| `tenant_id` | string(64) | yes | Tenant/scope ownership |
| `skill_key` | string(120) | yes | Stable functional key, e.g. `create_course` |
| `version` | integer | yes | Monotonic version per `skill_key` |
| `status` | enum | yes | `draft`,`review`,`approved`,`active`,`deprecated`,`retired`,`rejected` |
| `purpose` | text | yes | Human-readable intent |
| `input_schema` | JSON Schema | yes | Contract for inputs |
| `output_schema` | JSON Schema | yes | Contract for outputs |
| `required_capabilities` | CapabilityRef[] | yes | Must all resolve to active/allowed capabilities |
| `optional_capabilities` | CapabilityRef[] | no | Used for fallback/quality upgrades |
| `constraints` | jsonb | no | Cost/time/data constraints |
| `quality_profile` | enum | yes | `minimal`,`standard`,`high`,`strict` |
| `fallback_policy` | enum | yes | `forbidden`,`allowed`,`required` |
| `evaluation_criteria` | jsonb | no | Dimensions and thresholds |
| `risk_tier` | enum | yes | `low`,`medium`,`high`,`critical` |
| `policy_pack_ref` | string(120) | yes | Policy package identifier |
| `trust_tier_min` | enum | yes | `public`,`internal`,`restricted`,`sensitive` |
| `created_at`,`updated_at` | timestamptz | yes | UTC |
| `created_by`,`updated_by` | string(120) | yes | Principal id |
| `approved_by`,`approved_at` | string/timestamptz | conditional | Required for high-risk activation |
| `checksum_sha256` | string(64) | yes | Integrity of normalized definition |

`CapabilityRef` shape:
- `capability_key: string(120)`
- `version_selector: enum(active,exact,min)`
- `version_value: integer|null` (required for `exact` and `min`)

## Lifecycle

`draft -> review -> approved -> active -> deprecated -> retired`  
`review -> rejected`

Rules:
- `active` can only be reached from `approved`.
- Editing immutable fields after `approved` requires a new version.
- Re-activation after `retired` requires a new version.

## Validation Rules

- Unique key: (`tenant_id`, `skill_key`, `version`).
- Exactly one `active` version per (`tenant_id`, `skill_key`).
- `required_capabilities` cannot be empty.
- Every required capability must exist as active `CapabilityDefinition`.
- `CapabilityRef` resolution must be deterministic and version-safe.
- `input_schema` and `output_schema` must be valid JSON Schema.
- `risk_tier in (high, critical)` requires approval metadata and policy confirmation.

## Error Codes

- `SD-001 INVALID_SCHEMA`
- `SD-002 DUPLICATE_VERSION`
- `SD-003 CAPABILITY_NOT_FOUND`
- `SD-004 ILLEGAL_STATE_TRANSITION`
- `SD-005 POLICY_DENIED`
- `SD-006 NOT_AUTHORIZED`

## Minimal API Structure

- `POST /api/v1/skill-definitions` (create draft)
- `POST /api/v1/skill-definitions/{skill_key}/versions/{version}/submit-review`
- `POST /api/v1/skill-definitions/{skill_key}/versions/{version}/approve`
- `POST /api/v1/skill-definitions/{skill_key}/versions/{version}/activate`
- `POST /api/v1/skill-definitions/{skill_key}/versions/{version}/reject`
- `POST /api/v1/skill-definitions/{skill_key}/versions/{version}/deprecate`
- `POST /api/v1/skill-definitions/{skill_key}/versions/{version}/retire`
- `GET /api/v1/skill-definitions/{skill_key}`
- `GET /api/v1/skill-definitions/{skill_key}/versions/{version}`

Mutating endpoints require auth + role checks and emit audit records.

Role/Scope baseline:
- Create/submit: `operator` or `admin` role + `skills:write`.
- Approve/activate/reject/deprecate/retire: `admin` role + `skills:govern`.
- Reads: authenticated principal + `skills:read`.
- `tenant_id` is derived from auth token; cross-tenant mutation is forbidden.

## Event Types

- `skill.definition.created.v1`
- `skill.definition.submitted.v1`
- `skill.definition.approved.v1`
- `skill.definition.activated.v1`
- `skill.definition.deprecated.v1`
- `skill.definition.rejected.v1`

## Storage and Runtime Placement

- PostgreSQL (durable): full object and lifecycle history.
- Redis (ephemeral): optional read cache and short-lived projection only.
- Event backbone: EventStream envelope with `event_type`, `severity`, `source`, `entity`, `correlation_id`, `occurred_at`, `data`, `schema_version`.

Event compatibility note:
- Until `schema_version` exists natively in runtime envelope, publish it inside `data.schema_version` and mirror to top-level once contract envelope is extended.
