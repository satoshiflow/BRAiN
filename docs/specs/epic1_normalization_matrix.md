# Epic 1 Normalization Matrix

Status: Active implementation work document
Scope: Canonical normalization and hardening of SkillRun, EvaluationResult, SkillDefinition, CapabilityDefinition, and ProviderBinding.

## Cross-Cutting Invariants

- `SkillRun` is the only runtime truth.
- `Mission` is never runtime and never selects providers directly.
- `EvaluationResult` is the canonical evaluation object; inline summaries are read projections only.
- `ProviderBinding` separates governed binding definitions from run-time resolved selections.
- PostgreSQL stores canonical definitions, runs, transitions, evaluations, and governed bindings.
- Redis is ephemeral only: leases, heartbeats, progress, queue-near state, health TTL projections.
- Events must be emitted from a persistence-near, auditable, outbox-compatible path.
- Artifact references are introduced now using a consistent minimal schema.

## SkillRun

- Canonical fields: `skill_key`, `skill_version`, `state`, `input_payload`, `plan_snapshot`, `provider_selection_snapshot`, `policy_decision_id`, `policy_snapshot`, `risk_tier`, `correlation_id`, `causation_id`, `mission_id`, `idempotency_key`, `deadline_at`, `retry_count`, `cost_estimate`, `cost_actual`, `failure_code`, `failure_reason_sanitized`, `input_artifact_refs`, `output_artifact_refs`, `evidence_artifact_refs`
- Shadow fields: `evaluation_summary` (projection only)
- PostgreSQL: canonical run record + transition history + lifecycle event outbox
- Redis: lease, heartbeat, progress, live logs, cancellation signal
- Required events: `skill.run.created.v1`, `skill.run.planning.started.v1`, `skill.run.approval.required.v1`, `skill.run.started.v1`, `skill.run.progress.v1`, `skill.run.completed.v1`, `skill.run.failed.v1`, `skill.run.cancelled.v1`, `skill.run.timed_out.v1`
- Audit required: create, approval required, cancel requested, terminal outcome
- Lifecycle: `queued -> planning -> waiting_approval? -> running -> succeeded|failed|cancel_requested|timed_out`; `cancel_requested -> cancelled`

## EvaluationResult

- Canonical fields: `skill_run_id`, `status`, `overall_score`, `dimension_scores`, `passed`, `criteria_snapshot`, `findings`, `recommendations`, `metrics_summary`, `provider_selection_snapshot`, `policy_compliance`, `policy_violations`, `evaluation_revision`, `revision_of_id`, `evidence_artifact_refs`, `review_artifact_refs`, `comparison_artifact_refs`
- Shadow fields: `SkillRun.evaluation_summary`
- PostgreSQL: canonical evaluation records, append-only revisions, lifecycle event outbox
- Redis: optional evaluator queue/progress only
- Required events: `evaluation.result.created.v1`, `evaluation.result.completed.v1`, `evaluation.result.failed.v1`, `evaluation.result.non_compliant.v1`
- Audit required: create, failed, non-compliant, governance override
- Lifecycle: `pending -> completed|failed|skipped`

## SkillDefinition

- Canonical fields: `skill_key`, `version`, `status`, `purpose`, `input_schema`, `output_schema`, `required_capabilities`, `optional_capabilities`, `constraints`, `evaluation_criteria`, `risk_tier`, `policy_pack_ref`, `trust_tier_min`, `definition_artifact_refs`, `example_artifact_refs`, `builder_artifact_refs`
- Shadow fields: mutable post-approval edits
- PostgreSQL: canonical definition + transition/audit history
- Redis: optional read cache only
- Required events: `skill.definition.created.v1`, `skill.definition.submitted.v1`, `skill.definition.approved.v1`, `skill.definition.activated.v1`, `skill.definition.deprecated.v1`, `skill.definition.rejected.v1`
- Audit required: create, submit-review, approve, activate, reject, deprecate, retire
- Lifecycle: `draft -> review -> approved -> active -> deprecated -> retired`; `review -> rejected`

## CapabilityDefinition

- Canonical fields: `capability_key`, `version`, `status`, `domain`, `description`, `input_schema`, `output_schema`, `default_timeout_ms`, `retry_policy`, `qos_targets`, `fallback_capability_key`, `policy_constraints`, `contract_artifact_refs`, `adapter_test_artifact_refs`
- Shadow fields: provider-specific routing assumptions stored in definitions
- PostgreSQL: canonical definition + transition/audit history
- Redis: health/readiness availability projection only
- Required events: `capability.definition.created.v1`, `capability.definition.activated.v1`, `capability.definition.blocked.v1`, `capability.definition.deprecated.v1`, `capability.definition.retired.v1`
- Audit required: create, activate, block, deprecate, retire
- Lifecycle: `draft -> active -> deprecated -> retired`; `active -> blocked`; `blocked -> active`

## ProviderBinding

- Governed binding definition fields: `capability_id`, `capability_key`, `capability_version`, `provider_key`, `provider_type`, `adapter_key`, `endpoint_ref`, `model_or_tool_ref`, `region`, `priority`, `weight`, `cost_profile`, `sla_profile`, `policy_constraints`, `status`, `valid_from`, `valid_to`, `config`, `definition_artifact_refs`, `evidence_artifact_refs`
- Run-time resolved selection fields: `provider_binding_id`, `selection_strategy`, `policy_context`, `selection_reason`, `resolved_at`, `selection_artifact_refs`; stored as frozen snapshot in `SkillRun.provider_selection_snapshot`
- Shadow fields: `InMemoryProviderBindingRegistry`, AXE-only provider selector heuristics
- PostgreSQL: governed binding definitions + event outbox
- Redis: health TTL projection (`health_status`, `latency_p95_ms`, `error_rate_5m`, `circuit_state`, `last_probe_at`)
- Required events: `provider.binding.created.v1`, `provider.binding.enabled.v1`, `provider.binding.disabled.v1`, `provider.binding.quarantined.v1`, `provider.binding.health.updated.v1`
- Audit required: create, enable, disable, quarantine
- Lifecycle: `draft -> enabled -> disabled`; `enabled -> quarantined -> enabled|disabled`

## Shadow-Model Handling

1. Degrade `SkillRun.evaluation_summary` to a read projection.
2. Route binding resolution through persistent `ProviderBinding` lookup before any fallback.
3. Keep `InMemoryProviderBindingRegistry` as compatibility fallback only and mark it deprecated.
4. Keep AXE provider selection as UI/runtime convenience only until it is fully backed by governed bindings.
5. Keep external finalization paths under the same `SkillRun` state machine rules.
