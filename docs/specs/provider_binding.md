# ProviderBinding Specification (v1)

Status: Draft for Epic 1  
Scope: Contract linking capabilities to concrete provider implementations.

## Purpose

`ProviderBinding` binds a `CapabilityDefinition` to a specific provider endpoint/model/tool with cost, SLA and policy controls.

## Fields

| Field | Type | Required | Notes |
|---|---|---:|---|
| `id` | UUID | yes | Internal primary key |
| `tenant_id` | string(64) | yes | Tenant/scope ownership |
| `capability_id` | UUID | yes | FK to capability definition |
| `capability_key` | string(120) | yes | Denormalized lookup key |
| `capability_version` | integer | yes | Bound capability version |
| `provider_key` | string(120) | yes | Stable provider identifier |
| `provider_type` | enum | yes | `llm`,`tool`,`service`,`self_hosted` |
| `endpoint_ref` | string(255) | yes | Secret reference, never raw secret |
| `model_or_tool_ref` | string(255) | no | Model name or tool id |
| `region` | string(64) | no | Residency control |
| `priority` | integer | yes | Lower value = higher priority |
| `weight` | decimal(5,2) | no | Weighted selection |
| `cost_profile` | jsonb | no | Unit cost, budget class |
| `sla_profile` | jsonb | no | p95 latency, error budget |
| `policy_constraints` | jsonb | no | Governance constraints |
| `status` | enum | yes | `draft`,`enabled`,`disabled`,`quarantined` |
| `valid_from`,`valid_to` | timestamptz | no | Time-bounded routing |
| `created_at`,`updated_at` | timestamptz | yes | UTC |
| `created_by`,`updated_by` | string(120) | yes | Principal id |

Ephemeral runtime health (Redis TTL projection):
- `health_status`, `latency_p95_ms`, `error_rate_5m`, `circuit_state`, `last_probe_at`.

## Lifecycle

`draft -> enabled -> disabled`  
`enabled -> quarantined -> enabled|disabled`

Rules:
- `quarantined` blocks resolver selection.
- Re-enable from quarantine requires health + policy pass.

## Validation Rules

- Unique key: (`tenant_id`, `capability_id`, `provider_key`).
- `capability_key`/`capability_version` must match `capability_id`.
- `enabled` requires successful health check and policy acceptance.
- Secret values are never persisted in clear text.
- `valid_to` must be greater than `valid_from` when both set.

## Error Codes

- `PB-001 DUPLICATE_BINDING`
- `PB-002 INVALID_PROVIDER_REF`
- `PB-003 HEALTHCHECK_FAILED`
- `PB-004 POLICY_REGION_DENIED`
- `PB-005 QUARANTINED`

## Minimal API Structure

- `POST /api/v1/provider-bindings`
- `POST /api/v1/provider-bindings/{id}/enable`
- `POST /api/v1/provider-bindings/{id}/disable`
- `POST /api/v1/provider-bindings/{id}/quarantine`
- `GET /api/v1/provider-bindings?capability_key={capability_key}`

All mutating operations require auth + policy + audit.

Role/Scope baseline:
- Create/enable/disable/quarantine: `admin` role + `providers:govern`.
- Read: authenticated principal + `providers:read`.
- `tenant_id` is token-derived; cross-tenant mutation is forbidden.

## Event Types

- `provider.binding.created.v1`
- `provider.binding.enabled.v1`
- `provider.binding.disabled.v1`
- `provider.binding.quarantined.v1`
- `provider.binding.health.updated.v1`

## Storage and Runtime Placement

- PostgreSQL (durable): binding metadata and lifecycle.
- Redis (ephemeral): fast health telemetry for resolver decisions.
- EventStream: lifecycle + health change events for observability and governance hooks.

Resolver contract note:
- Resolver input uses `capability_key + capability_version` and returns `provider_binding_id` to keep selection deterministic and auditable.
