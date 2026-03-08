# CapabilityDefinition Specification (v1)

Status: Draft for Epic 1  
Scope: Contract for atomic, measurable and replaceable capabilities.

## Purpose

`CapabilityDefinition` describes one atomic ability (e.g. `text.generate`, `research.web.search`) independent of any specific provider.

## Fields

| Field | Type | Required | Notes |
|---|---|---:|---|
| `id` | UUID | yes | Internal primary key |
| `tenant_id` | string(64) | yes | Tenant/scope ownership |
| `capability_key` | string(120) | yes | Dot-key identifier |
| `version` | integer | yes | Monotonic per `capability_key` |
| `status` | enum | yes | `draft`,`active`,`deprecated`,`retired`,`blocked` |
| `domain` | string(80) | yes | e.g. `generation`,`infra`,`code` |
| `description` | text | yes | Capability intent |
| `input_schema` | JSON Schema | yes | Expected input contract |
| `output_schema` | JSON Schema | yes | Produced output contract |
| `default_timeout_ms` | integer | yes | Runtime default timeout |
| `retry_policy` | jsonb | no | Retry limits/backoff |
| `qos_targets` | jsonb | no | latency, quality, availability SLOs |
| `fallback_capability_key` | string(120) | no | Optional fallback capability |
| `policy_constraints` | jsonb | no | residency/compliance/trust constraints |
| `created_at`,`updated_at` | timestamptz | yes | UTC |
| `created_by`,`updated_by` | string(120) | yes | Principal id |

## Lifecycle

`draft -> active -> deprecated -> retired`  
`active -> blocked` (incident/security path)

Rules:
- `blocked` denies new SkillRuns resolving to this capability.
- Recovery from `blocked` requires explicit governance decision and audit trail.

## Validation Rules

- Unique key: (`tenant_id`, `capability_key`, `version`).
- Exactly one `active` version per (`tenant_id`, `capability_key`).
- Fallback graph must not create cycles.
- `input_schema` and `output_schema` must be valid JSON Schema.

## Error Codes

- `CD-001 DUPLICATE_KEY`
- `CD-002 INVALID_SCHEMA`
- `CD-003 FALLBACK_CYCLE`
- `CD-004 CAPABILITY_BLOCKED`
- `CD-005 POLICY_DENIED`

## Minimal API Structure

- `POST /api/v1/capability-definitions`
- `POST /api/v1/capability-definitions/{capability_key}/activate`
- `POST /api/v1/capability-definitions/{capability_key}/block`
- `POST /api/v1/capability-definitions/{capability_key}/deprecate`
- `POST /api/v1/capability-definitions/{capability_key}/retire`
- `GET /api/v1/capability-definitions/{capability_key}`
- `GET /api/v1/capability-definitions/{capability_key}/versions/{version}`

Mutations require auth + role checks and policy gates.

Role/Scope baseline:
- Create/activate/block/deprecate/retire: `admin` role + `capabilities:govern`.
- Read: authenticated principal + `capabilities:read`.
- `tenant_id` is token-derived; cross-tenant mutation is forbidden.

## Event Types

- `capability.definition.created.v1`
- `capability.definition.activated.v1`
- `capability.definition.blocked.v1`
- `capability.definition.deprecated.v1`
- `capability.definition.retired.v1`

## Storage and Runtime Placement

- PostgreSQL (durable): canonical definitions and status transitions.
- Redis (ephemeral): health snapshots, short TTL availability projections.
- EventStream emits lifecycle and policy-relevant transitions.

Event compatibility note:
- Event types are versioned with `.v1`; runtime adapters may additionally emit legacy alias events without suffix during transition.
