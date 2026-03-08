# SkillRegistry Specification (v1)

Status: Draft for Epic 3  
Scope: Canonical registry service for `SkillDefinition` versioning, activation, discovery, and deterministic resolution.

## Purpose

`SkillRegistry` is the canonical control plane for `SkillDefinition` objects defined in Epic 1.

It provides:
- one durable source of truth for skill definitions
- deterministic version resolution for new `SkillRun` creation
- activation/deprecation/retirement governance
- tenant-safe search, indexing, and read models

`SkillRegistry` does not execute skills and does not own runtime state.

## Source of Truth

Canonical source of truth:
- PostgreSQL rows for `SkillDefinition`
- PostgreSQL lifecycle history
- PostgreSQL outbox rows for event publication

Non-canonical sources:
- code or built-in manifests
- YAML/bootstrap files
- in-memory registries
- Redis caches

Bootstrap rule:
- Built-in or file-backed skills may seed registry records, but after persistence PostgreSQL becomes the only canonical source of truth.

## Object Ownership

`SkillRegistry` owns:
- `SkillDefinition` persistence and lifecycle enforcement
- active-version pointer semantics
- search/index projections for skill discovery
- deterministic resolution from selector to exact `skill_key + version`

`SkillRegistry` reads but does not own:
- `CapabilityDefinition` eligibility
- auth primitives from `backend/app/core/auth_deps.py`
- audit write path from `backend/app/core/audit_bridge.py`
- event publication path from `backend/mission_control_core/core/event_stream.py`
- runtime policy and approval objects from Epic 2

`SkillRegistry` must not own:
- provider selection
- live worker state
- execution telemetry
- `ApprovalGate` or `PolicyDecision`

## Tenant Model and Ownership Scope

Every registry record is tenant-scoped.

Scopes:
- `tenant` record: mutated only within one tenant
- `system` record: platform-owned catalog entry exposed read-only unless overridden by tenant-local keys

Storage model:
- `owner_scope` is mandatory and must be one of `tenant` or `system`.
- `tenant_id` is required when `owner_scope=tenant`.
- `tenant_id` must be `NULL` when `owner_scope=system`.

Rules:
- `tenant_id` is token-derived for all mutations
- cross-tenant mutation is forbidden
- tenant-local definitions never mutate `system` definitions
- system catalog mutation requires platform-admin privilege
- runtime resolution for a tenant may read same-tenant records and allowed `system` records

## Versioning

- Unique key: (`tenant_id`, `skill_key`, `version`).
- Unique key for tenant records: (`tenant_id`, `skill_key`, `version`).
- Unique key for system records: (`owner_scope`, `skill_key`, `version`) where `owner_scope='system'`.
- `version` is monotonic per (`tenant_id`, `skill_key`).
- At most one `active` version per (`tenant_id`, `skill_key`).
- At most one `active` tenant version per (`tenant_id`, `skill_key`).
- At most one `active` system version per (`skill_key`).
- Activating a new version atomically deprecates the previous active version for that tenant/key.
- Immutable payload changes after `approved` require a new version.

Version selectors:
- `active`
- `exact`
- `min`

## Activation Rules

A `SkillDefinition` may be activated only when:
- current state is `approved`
- checksum exists and matches normalized payload
- all `required_capabilities` resolve deterministically
- resolved required capabilities are execution-eligible
- schemas are valid
- required governance preconditions are satisfied
- durable audit write succeeds
- outbox write succeeds in the same transaction

Additional rules:
- `retired` versions cannot be re-activated
- activation affects only new runs after commit
- existing `SkillRun` rows keep their frozen `skill_version`
- deprecated versions remain readable but are not default-selected

## Resolution Rules

### Inputs

- `tenant_id`
- `skill_key`
- `selector` (`active`,`exact`,`min`)
- optional `version_value`
- optional `as_of` timestamp for deterministic replay

### Output

- exact `skill_key`
- exact `version`
- normalized definition snapshot hash
- resolved required/optional capability references
- eligibility result

### Algorithm

1. Search same-tenant records, then optional `system` fallback.
2. Apply selector.
3. Filter by execution-eligible statuses (`active` by default).
4. Verify required capability references resolve deterministically.
5. Return one exact version or fail closed.

Resolution precedence:
1. exact tenant match
2. active tenant match
3. exact `system` match
4. active `system` match

Ambiguity rule:
- if more than one candidate survives at the same precedence level, resolution fails.

## API Surface

Definition lifecycle endpoints remain aligned with Epic 1:
- `POST /api/v1/skill-definitions`
- `GET /api/v1/skill-definitions`
- `GET /api/v1/skill-definitions/{skill_key}`
- `GET /api/v1/skill-definitions/{skill_key}/versions/{version}`
- `POST /api/v1/skill-definitions/{skill_key}/versions/{version}/submit-review`
- `POST /api/v1/skill-definitions/{skill_key}/versions/{version}/approve`
- `POST /api/v1/skill-definitions/{skill_key}/versions/{version}/activate`
- `POST /api/v1/skill-definitions/{skill_key}/versions/{version}/reject`
- `POST /api/v1/skill-definitions/{skill_key}/versions/{version}/deprecate`
- `POST /api/v1/skill-definitions/{skill_key}/versions/{version}/retire`

Registry-specific reads:
- `GET /api/v1/skill-registry/search?q={q}&status={status}&risk_tier={risk_tier}&capability_key={capability_key}`
- `GET /api/v1/skill-registry/resolve?skill_key={skill_key}&selector={selector}&version_value={n}`
- `GET /api/v1/skill-registry/{skill_key}/versions`
- `GET /api/v1/skill-registry/{skill_key}/active`

Mutation idempotency:
- Create and lifecycle actions must support `Idempotency-Key`.

## Indexing and Search

Required PostgreSQL indexes:
- unique btree: (`tenant_id`, `skill_key`, `version`)
- partial unique btree: (`tenant_id`, `skill_key`) where `status = 'active'`
- btree: (`tenant_id`, `status`, `updated_at`)
- btree: (`tenant_id`, `risk_tier`, `status`)
- GIN for searchable projection of `purpose`, `constraints`, and capability refs

Supported filters:
- `tenant_id`
- `owner_scope`
- `skill_key`
- `status`
- `version`
- `risk_tier`
- `quality_profile`
- `trust_tier_min`
- `capability_key`
- `updated_since`

## Audit Requirements

Durable audit is required for:
- create draft
- update draft/review version
- submit review
- approve
- activate
- reject
- deprecate
- retire

Mandatory audit fields:
- `tenant_id`
- `skill_key`
- `version`
- `skill_definition_id`
- `actor_id`
- `actor_type`
- `previous_status`
- `new_status`
- `checksum_sha256`
- `correlation_id`
- `causation_id` if present
- `occurred_at`

Durability rule:
- lifecycle mutation must fail if durable audit write fails.

## Event Requirements

Public lifecycle events:
- `skill.definition.created.v1`
- `skill.definition.submitted.v1`
- `skill.definition.approved.v1`
- `skill.definition.activated.v1`
- `skill.definition.deprecated.v1`
- `skill.definition.rejected.v1`
- `skill.definition.retired.v1`

Optional internal operational events:
- `skill.registry.resolution.failed.v1`
- `skill.registry.cache.invalidated.v1`

Ordering rule:
- PostgreSQL state change, durable audit write, and outbox insert must commit before publish.

Event compatibility note:
- Runtime adapters may mirror `.v1` names to repo-compatible legacy aliases during transition.

## Auth, Role, and Scope

Baseline:
- create/submit-review: `operator` or `admin` + `skills:write`
- approve/activate/reject/deprecate/retire: `admin` + `skills:govern`
- read/search/resolve: authenticated principal + `skills:read`
- mutate `system` scope: `admin` + `skills:govern` + `platform:catalog:write`

Rules:
- `tenant_id` comes from auth context, never request body
- cross-tenant reads are forbidden except same-tenant + allowed `system`
- missing auth -> `401`
- missing role/scope -> `403`

## Error Codes

| Code | HTTP | Meaning |
|---|---:|---|
| `SKR-001 AUTH_REQUIRED` | 401 | Principal missing/invalid |
| `SKR-002 FORBIDDEN` | 403 | Role or scope missing |
| `SKR-003 TENANT_MISMATCH` | 403 | Cross-tenant access attempted |
| `SKR-004 DUPLICATE_VERSION` | 409 | Version already exists |
| `SKR-005 ACTIVE_VERSION_EXISTS` | 409 | Invalid activation path violates single-active rule |
| `SKR-006 INVALID_STATE_TRANSITION` | 409 | Lifecycle transition not allowed |
| `SKR-007 CAPABILITY_UNRESOLVED` | 422 | Required capability ref cannot be resolved |
| `SKR-008 CAPABILITY_NOT_ELIGIBLE` | 409 | Required capability is blocked/retired/not selectable |
| `SKR-009 RESOLUTION_NOT_FOUND` | 404 | No matching skill version found |
| `SKR-010 RESOLUTION_AMBIGUOUS` | 409 | More than one candidate survives |
| `SKR-011 INVALID_SELECTOR` | 422 | Unsupported selector/value combination |
| `SKR-012 AUDIT_WRITE_FAILED` | 500 | Durable audit persistence failed |
| `SKR-013 OUTBOX_WRITE_FAILED` | 500 | Event outbox persistence failed |

## PostgreSQL vs Redis Boundaries

### PostgreSQL

- canonical `SkillDefinition`
- lifecycle history
- active-version invariants
- search/index projection tables or materialized views
- outbox rows
- durable audit references

### Redis

- active-version pointer cache
- search result cache
- negative lookup cache
- short-lived registry read projections

Rules:
- no canonical lifecycle state may exist only in Redis
- Redis must be reconstructible from PostgreSQL
- cache invalidation happens after successful commit

## Integration with Epic 1 and Epic 2

- `SkillRegistry` is the operational owner of `SkillDefinition`.
- It validates `required_capabilities` against `CapabilityRegistry` outputs.
- It provides the exact `skill_version` frozen onto `SkillRun`.
- `SkillRun` creation resolves exact version before Constitution Gate evaluation.
- `PolicyDecision.resource_snapshot` should include `skill_key`, `skill_version`, `risk_tier`, `policy_pack_ref`, and `checksum_sha256`.

## Legacy Compatibility Notes

- The existing `backend/app/modules/skills/` module remains a compatibility surface during migration.
- Built-in seeding and in-memory handler registries must not become alternate sources of truth.
- Legacy `/api/skills` paths should be treated as deprecated adapters once registry APIs exist.
- Legacy writer paths must not remain dual-write indefinitely:
  - once registry mutation APIs are enabled, legacy writers must be switched to read-only or adapter-backed mode
  - registry state must not be mutated directly from built-in seeder/runtime caches except through explicit bootstrap flow.

## Repo Integration Constraint

- Current repo primitives do not yet provide a shared transactional audit + outbox boundary.
- This spec therefore defines the target control-plane contract; implementation must introduce an explicit integration layer rather than relying on today's best-effort audit bridge behavior.

## Done Criteria

- one PostgreSQL-backed source of truth exists for skill definitions
- activation and resolution rules are deterministic and tenant-safe
- lifecycle API remains compatible with Epic 1 contracts
- audit/event ordering is explicit and fail-closed
- Redis remains cache-only
- `SkillRun` can freeze exact skill version from registry output
