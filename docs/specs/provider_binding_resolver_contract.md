# ProviderBinding Resolver Contract

Status: Epic 1 implementation contract

## Purpose

Resolve a governed `ProviderBinding` definition into a deterministic, auditable run-time selection for a capability execution.

## Resolver Input

- `capability_key`
- `capability_version`
- `tenant_id`
- `owner_scope`
- `policy_context`
  - `risk_tier`
  - `trust_tier`
  - `region`
  - `mission_id`
  - `requested_by`

## Resolver Output

- `provider_binding_id`
- `selection_strategy`
- `selection_reason`
- `policy_context`
- `resolved_at`
- `binding_snapshot`

## Rules

- Only `enabled` bindings may be selected.
- `quarantined` bindings are never selected.
- `disabled` bindings are never selected.
- `valid_from` / `valid_to` must be honored.
- Selection must be deterministic for the same capability version + tenant + policy context.
- Run-time output is frozen into `SkillRun.provider_selection_snapshot`.
- Resolver may read Redis health TTL projections, but cannot derive governed truth from Redis.
- If no persistent binding is available, compatibility fallback may be used only when explicitly marked and must set `selection_reason=compat_in_memory_fallback`.
