# Skill Telemetry, Evaluator, and Optimizer Specification (v1)

Status: Draft for Epic 6  
Scope: Measurement, rule-based evaluation, and optimization recommendation layer for `SkillRun` executions.

## Purpose

This layer turns execution traces into:
- operational observability
- immutable `EvaluationResult` artifacts
- optimization recommendations

It follows the BRAiN execution standard requirement that execution results are evaluated before closure.

## Ownership Boundaries

Telemetry owns:
- low-cardinality metrics
- execution traces
- run-level operational signals

Evaluator owns:
- immutable `EvaluationResult`
- rule-based error classification
- pass/fail and policy-compliance judgement

Optimizer owns:
- recommendation generation
- ranking of future provider/skill improvements

Optimizer does not own direct side effects on live registry/runtime state.

## KPI Minimum Set

Per `SkillRun` capture at minimum:
- `success`
- `failure_code`
- `latency_ms`
- `cost_actual`
- `retry_count`
- `fallback_used`
- `evaluation_score`
- `policy_compliance`

## Evaluation Model

Evaluation consumes frozen snapshots and execution outputs.

Mandatory evaluator inputs:
- `skill_run_id`
- `skill_version`
- resolved capability versions
- `provider_binding_id`s
- `policy_snapshot_hash`
- `plan_snapshot`
- output/result summary
- metrics summary

Evaluation outputs:
- `overall_score`
- `dimension_scores`
- `issues_detected`
- `error_classification`
- `policy_compliance`
- `recommendations`
- `metrics_summary`
- `provider_selection_snapshot`
- `correlation_id`

## Error Classification Baseline

Supported classes:
- `context_error`
- `execution_error`
- `quality_error`
- `format_error`
- `test_error`

## Reviewer Model

Evaluation should use specialized reviewer dimensions instead of one generic judgement.

Examples:
- correctness reviewer
- security reviewer
- maintainability reviewer
- test reviewer

## Optimizer Contract

Optimizer input:
- aggregated `SkillRun` history
- aggregated `EvaluationResult` history
- aggregated provider performance history

Scope rule:
- Aggregation is tenant-scoped by default.
- Cross-tenant aggregation is forbidden unless explicitly published as governed `system` analytics.

Optimizer output:
- ranked recommendation set
- candidate provider strategy changes
- candidate threshold/policy tuning suggestions
- candidate skill version improvement suggestions
- `source_snapshot` linking the advisory record back to sampled runs/evaluations
- advisory `status` (`open`,`accepted`,`dismissed`) tracked separately from execution state

Restrictions:
- optimizer output is advisory
- direct mutation of registries or bindings requires separate governed action

## Telemetry Privacy Rules

- Raw prompts, secrets, full outputs, and PII must not be emitted as standard metrics.
- High-cardinality payloads belong in bounded traces or durable evidence stores, not default metrics.
- Existing anonymization/privacy patterns in current telemetry modules should be preserved.

## API Surface

- `GET /api/v1/skill-runs/{id}/telemetry`
- `GET /api/v1/skill-runs/{id}/evaluation-results`
- `GET /api/v1/optimizer/recommendations?skill_key={skill_key}`

Write-side creation of telemetry/evaluation records happens via runtime service paths, not open public mutation APIs.

## Events

- `skill.telemetry.recorded.v1`
- `evaluation.result.created.v1`
- `evaluation.result.completed.v1`
- `optimizer.recommendation.created.v1`

Durability rule:
- Durable evaluation or recommendation records must commit before lifecycle event publish.

## PostgreSQL vs Redis vs EventStream

### PostgreSQL
- immutable `EvaluationResult`
- optimization recommendation records
- durable execution trace summaries

### Redis
- transient progress metrics
- short-lived dashboard projections

### EventStream
- telemetry/evaluation/optimizer lifecycle events

## Legacy Compatibility

- Existing `telemetry` and `runtime_auditor` modules are informative predecessors, not final source-of-truth models.
- Current AXE telemetry concerns must not dictate SkillRun telemetry shape.

## Done Criteria

- KPI minimum set is explicit
- evaluator and optimizer are clearly separated
- privacy/cardinality constraints are explicit
- optimization outputs are advisory, not self-mutating
