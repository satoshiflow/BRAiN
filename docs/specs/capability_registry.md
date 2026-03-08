# CapabilityRegistry Specification (v1)

Status: Draft for Epic 3  
Scope: Canonical registry service for `CapabilityDefinition` versioning, activation, blocking, discovery, and deterministic resolution.

## Purpose

`CapabilityRegistry` is the canonical control plane for `CapabilityDefinition` objects defined in Epic 1.

It provides:
- one durable source of truth for capability definitions
- deterministic capability resolution for planning and runtime eligibility checks
- governance-aware activation/block/deprecation/retirement controls
- tenant-safe discovery and search

`CapabilityRegistry` does not select concrete providers.

## Source of Truth

Canonical source of truth:
- PostgreSQL rows for `CapabilityDefinition`
- PostgreSQL lifecycle history
- PostgreSQL outbox rows for event publication

Non-canonical sources:
- code constants
- YAML/config catalogs
- in-memory maps
- Redis health or cache state

Rule:
- runtime health may influence eligibility hints, but is not the canonical definition source of truth.

## Object Ownership

`CapabilityRegistry` owns:
- `CapabilityDefinition` persistence and lifecycle rules
- active-version pointer semantics
- fallback graph validation
- deterministic resolution from selector to exact `capability_key + version`
- search/index projections for capability discovery

`CapabilityRegistry` reads but does not own:
- provider health and routing metadata from `ProviderBinding`
- auth/audit/event primitives from repo core modules
- `SkillDefinition` references that depend on capability existence

`CapabilityRegistry` must not own:
- provider credentials
- provider health telemetry as canonical state
- execution results
- skill composition logic

## Tenant Model and Ownership Scope

Every record is tenant-scoped.

Scopes:
- `tenant` capability: owned by one tenant
- `system` capability: platform-owned base catalog

Storage model:
- `owner_scope` is mandatory and must be one of `tenant` or `system`.
- `tenant_id` is required when `owner_scope=tenant`.
- `tenant_id` must be `NULL` when `owner_scope=system`.

Rules:
- `tenant_id` is auth-derived for all mutations
- tenants may read same-tenant and allowed `system` capabilities
- tenants may mutate only same-tenant capabilities
- platform admins exclusively mutate `system` capabilities
- cross-tenant mutation is forbidden

## Versioning

- Unique key: (`tenant_id`, `capability_key`, `version`).
- Unique key for tenant records: (`tenant_id`, `capability_key`, `version`).
- Unique key for system records: (`owner_scope`, `capability_key`, `version`) where `owner_scope='system'`.
- `version` is monotonic per (`tenant_id`, `capability_key`).
- At most one `active` version per (`tenant_id`, `capability_key`).
- At most one `active` tenant version per (`tenant_id`, `capability_key`).
- At most one `active` system version per (`capability_key`).
- Activating a new version atomically deprecates the previous active version.

Selectors:
- `active`
- `exact`
- `min`

## Activation and Blocking Rules

Activation requires:
- current state is `draft`
- schemas are valid
- fallback graph remains acyclic
- durable audit write succeeds
- outbox write succeeds

Blocking rules:
- `active -> blocked` only through explicit governance mutation
- `blocked` denies new plan resolution and new provider selection
- recovery from `blocked` requires explicit `unblock` governance action and audit trail
- `retired` cannot be re-activated

Eligibility for planning:
- default eligible status is `active`
- `deprecated` is readable but not selected by default
- `blocked` and `retired` are never execution-eligible

## Resolution Rules

### Inputs

- `tenant_id`
- `capability_key`
- `selector` (`active`,`exact`,`min`)
- optional `version_value`
- optional `as_of`

### Output

- exact `capability_key`
- exact `version`
- normalized definition snapshot hash
- eligibility result
- optional fallback target summary

### Algorithm

1. Search same-tenant, then optional `system`.
2. Apply selector.
3. Filter by execution-eligible status for planning.
4. Fail if candidate is blocked/retired.
5. Return one exact version or fail closed.

Fallback rules:
- fallback is metadata, not automatic execution permission
- fallback target must resolve in the same tenant/system space
- fallback chains must be acyclic
- fallback does not bypass policy, block, quarantine, or residency constraints

Resolution precedence:
1. exact tenant match
2. active tenant match
3. exact `system` match
4. active `system` match

Ambiguity rule:
- same-precedence ambiguity returns conflict.

## API Surface

Definition lifecycle endpoints remain aligned with Epic 1:
- `POST /api/v1/capability-definitions`
- `GET /api/v1/capability-definitions`
- `GET /api/v1/capability-definitions/{capability_key}`
- `GET /api/v1/capability-definitions/{capability_key}/versions/{version}`
- `POST /api/v1/capability-definitions/{capability_key}/versions/{version}/activate`
- `POST /api/v1/capability-definitions/{capability_key}/versions/{version}/block`
- `POST /api/v1/capability-definitions/{capability_key}/versions/{version}/unblock`
- `POST /api/v1/capability-definitions/{capability_key}/versions/{version}/deprecate`
- `POST /api/v1/capability-definitions/{capability_key}/versions/{version}/retire`

Compatibility note:
- Epic 1 documented non-versioned mutation shortcuts for capability definitions.
- Epic 3 standardizes canonical mutation paths on versioned endpoints.
- If non-versioned endpoints are kept temporarily, they must resolve to the active version and behave as compatibility adapters only.

Registry-specific reads:
- `GET /api/v1/capability-registry/search?q={q}&domain={domain}&status={status}`
- `GET /api/v1/capability-registry/resolve?capability_key={capability_key}&selector={selector}&version_value={n}`
- `GET /api/v1/capability-registry/{capability_key}/versions`
- `GET /api/v1/capability-registry/{capability_key}/active`

## Indexing and Search

Required PostgreSQL indexes:
- unique btree: (`tenant_id`, `capability_key`, `version`)
- partial unique btree: (`tenant_id`, `capability_key`) where `status = 'active'`
- btree: (`tenant_id`, `domain`, `status`)
- btree: (`tenant_id`, `status`, `updated_at`)
- GIN on searchable projection of `description`, `policy_constraints`, and `qos_targets`

Supported filters:
- `tenant_id`
- `owner_scope`
- `capability_key`
- `domain`
- `status`
- `version`
- `updated_since`
- `fallback_capability_key`
- `provider_binding_presence` (derived read model only)

## Audit Requirements

Durable audit is required for:
- create
- activate
- block
- deprecate
- retire

Mandatory audit fields:
- `tenant_id`
- `capability_key`
- `version`
- `capability_definition_id`
- `actor_id`
- `actor_type`
- `previous_status`
- `new_status`
- `domain`
- `correlation_id`
- `causation_id` if present
- `occurred_at`

Durability rule:
- lifecycle mutation must fail if durable audit write fails.

## Event Requirements

Public lifecycle events:
- `capability.definition.created.v1`
- `capability.definition.activated.v1`
- `capability.definition.blocked.v1`
- `capability.definition.deprecated.v1`
- `capability.definition.retired.v1`

Optional internal operational events:
- `capability.registry.resolution.failed.v1`
- `capability.registry.cache.invalidated.v1`

Ordering rule:
- PostgreSQL lifecycle write, durable audit write, and outbox insert must commit before publish.

## Auth, Role, and Scope

Baseline:
- create/activate/block/deprecate/retire: `admin` + `capabilities:govern`
- read/search/resolve: authenticated principal + `capabilities:read`
- mutate `system` scope: `admin` + `capabilities:govern` + `platform:catalog:write`

Rules:
- `tenant_id` is token-derived
- cross-tenant reads are forbidden except same-tenant + allowed `system`
- missing auth -> `401`
- missing role/scope -> `403`

## Error Codes

| Code | HTTP | Meaning |
|---|---:|---|
| `CPR-001 AUTH_REQUIRED` | 401 | Principal missing/invalid |
| `CPR-002 FORBIDDEN` | 403 | Role or scope missing |
| `CPR-003 TENANT_MISMATCH` | 403 | Cross-tenant access attempted |
| `CPR-004 DUPLICATE_VERSION` | 409 | Version already exists |
| `CPR-005 ACTIVE_VERSION_EXISTS` | 409 | Invalid activation violates single-active rule |
| `CPR-006 INVALID_STATE_TRANSITION` | 409 | Lifecycle transition not allowed |
| `CPR-007 FALLBACK_CYCLE` | 422 | Fallback graph contains cycle |
| `CPR-008 BLOCKED` | 409 | Capability is blocked for execution |
| `CPR-008A UNBLOCK_NOT_ALLOWED` | 409 | Unblock request invalid for current state |
| `CPR-009 RESOLUTION_NOT_FOUND` | 404 | No matching capability version found |
| `CPR-010 RESOLUTION_AMBIGUOUS` | 409 | More than one candidate survives |
| `CPR-011 INVALID_SELECTOR` | 422 | Unsupported selector/value combination |
| `CPR-012 AUDIT_WRITE_FAILED` | 500 | Durable audit persistence failed |
| `CPR-013 OUTBOX_WRITE_FAILED` | 500 | Event outbox persistence failed |

## PostgreSQL vs Redis Boundaries

### PostgreSQL

- canonical `CapabilityDefinition`
- lifecycle history
- fallback graph validation state
- active-version invariants
- search/index projection tables or materialized views
- durable audit references
- outbox rows

### Redis

- active pointer cache
- read/search cache
- negative lookup cache
- availability hint cache derived from provider health
- cache invalidation fanout

Rules:
- no canonical capability state may live only in Redis
- Redis availability hints may accelerate planning but never override PostgreSQL lifecycle truth
- Redis is reconstructible from PostgreSQL plus live health feeds

## Integration with Epic 1 and Epic 2

- `CapabilityRegistry` is the operational owner of `CapabilityDefinition`.
- `SkillDefinition.required_capabilities` and `optional_capabilities` must resolve through this registry.
- `ProviderBinding` attaches only after exact capability version resolution.
- `SkillRun.provider_selection_snapshot` should reference exact resolved capability versions.
- Runtime governance may deny execution of an otherwise active capability, but that does not mutate canonical capability lifecycle state.

## Legacy Compatibility Notes

- Existing capability ideas embedded in older docs or runtime helpers must be treated as informational until represented in registry records.
- Capability health and provider metadata remain separate from canonical capability lifecycle state.

## Repo Integration Constraint

- Current repo primitives do not yet provide a shared transactional audit + outbox boundary.
- This spec defines the target control-plane contract and requires an explicit integration layer instead of today's best-effort audit/event behavior.

## Done Criteria

- one PostgreSQL-backed source of truth exists for capability definitions
- deterministic, tenant-safe capability resolution is documented
- block/deprecate/retire behavior is explicit
- lifecycle API remains compatible with Epic 1 contracts
- Redis remains cache-only
- downstream resolver layers can consume exact capability version outputs
