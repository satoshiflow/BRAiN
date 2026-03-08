# Capability Adapter Interface Specification (v1)

Status: Draft for Epic 4  
Scope: Canonical adapter contract between `CapabilityRegistry`/`ProviderBinding` and concrete provider implementations.

## Purpose

`CapabilityAdapter` standardizes how BRAiN executes a resolved capability against a concrete provider.

It separates:
- capability intent and versioning
- provider binding and routing
- normalized execution/result/error semantics

## Repo Alignment

- Connector pattern reference: `backend/app/modules/connectors/`
- External client pattern reference: `backend/app/modules/integrations/`
- Provider abstraction reference: `backend/app/modules/llm_router/`
- Contract inputs: `docs/specs/capability_definition.md`, `docs/specs/provider_binding.md`

## Ownership Boundaries

`CapabilityAdapter` owns:
- provider-specific request shaping
- provider invocation
- normalized result and error mapping
- health checks and static capability metadata snapshotting

`CapabilityAdapter` does not own:
- provider selection
- policy/approval decisions
- skill planning
- canonical lifecycle state

## Canonical Operations

Required operations:
- `validate_input`
- `prepare_request`
- `execute`
- `normalize_result`
- `normalize_error`
- `health_check`
- `metadata_snapshot`

Optional operations:
- `dry_run`
- `estimate_cost`
- `estimate_latency`

## Input Contract

Every adapter invocation receives:
- `tenant_id`
- `skill_run_id`
- `capability_key`
- `capability_version`
- `provider_binding_id`
- `input_payload`
- `policy_snapshot_hash`
- `correlation_id`
- `causation_id`
- `actor_id`
- `risk_tier`
- `deadline_at`

## Result Contract

Normalized success output must include:
- `output`
- `usage`
- `latency_ms`
- `cost_actual`
- `provider_facts`
- `trace_refs`
- `adapter_version`

## Error Contract

Normalized error output must include:
- `error_code`
- `retryable`
- `provider_unavailable`
- `provider_content_blocked`
- `timeout`
- `sanitized_message`
- `provider_error_ref`

## Determinism Rules

- Input and output normalization must be deterministic for the same adapter version.
- Adapter execution is always bound to exact `capability_key + capability_version + provider_binding_id`.
- Adapter metadata snapshots must be frozen onto `SkillRun.provider_selection_snapshot`.

## Retry and Fallback Rules

- Adapter-local retry handles transport/provider-transient failures only.
- Engine-level fallback/replan is outside adapter scope.
- Adapter must not perform hidden provider switching.

## Health and Availability

- Health state is ephemeral and cacheable in Redis.
- Health is not canonical provider lifecycle state.
- Adapter health affects resolver eligibility hints, not registry truth.

## Audit and Event Requirements

Durable audit required for:
- provider invocation start for sensitive capabilities
- provider invocation failure for governed capabilities

Operational events:
- `capability.adapter.invoked.v1`
- `capability.adapter.succeeded.v1`
- `capability.adapter.failed.v1`
- `capability.adapter.health.updated.v1`

Durability rule:
- Where adapter execution contributes to governed state transitions or failure evidence, durable write and audit must complete before outbox/event publish.

## PostgreSQL vs Redis vs EventStream

### PostgreSQL
- frozen provider selection snapshot references on `SkillRun`
- durable governed failure evidence

### Redis
- health cache
- transient backoff/circuit hints

### EventStream
- operational adapter events

## Security and Tenant Rules

- Adapter must never derive tenant from request payload.
- Secret material must come via referenced secret providers only.
- Adapter logs and events must use sanitized data.
- Raw provider prompts, outputs, or credentials must not be emitted by default.

## Legacy Compatibility

- Existing direct provider calls in `llm_router`, connectors, and builder services are compatibility paths.
- New implementations must converge on this adapter contract instead of introducing parallel invocation patterns.

## Done Criteria

- one canonical adapter contract exists
- result/error normalization is defined
- provider selection is frozen and auditable
- retry vs fallback responsibility is explicit
- Redis/PostgreSQL/EventStream boundaries are explicit
