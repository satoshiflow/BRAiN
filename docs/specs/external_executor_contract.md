# External Executor Contract (OpenClaw + Paperclip)

Status: Draft v1  
Owner: BRAiN Runtime  
Date: 2026-04-01

## 1. Purpose

This contract defines one canonical execution surface for external executors.

Executors in scope:

- `openclaw`
- `paperclip`

Goal: both executors run through the same BRAiN runtime path without creating a second runtime truth.

Canonical path:

`Intent -> SkillRun -> TaskLease -> External Executor -> finalize_external_run`

## 2. Runtime Boundaries

1. `SkillRun` is the canonical execution record.
2. `TaskLease` is the canonical worker delegation object.
3. External executors are bounded workers and must not become runtime truth.
4. AXE is an optional interface and not execution authority.

## 3. TaskLease Payload Contract

Each external executor task payload must include:

- `skill_run_id` (string UUID, required)
- `skill_key` (string, required)
- `skill_version` (int, required)
- `executor_type` (`openclaw|paperclip`, required)
- `intent` (string, required)
- `worker_type` (`openclaw|paperclip`, required)
- `request_id` (string, required)
- `correlation_id` (string, recommended)
- `mission_id` (string, optional)
- `input` (object, optional)

Task config must include:

- `lease_only=true`
- `worker_target` (`openclaw|paperclip`)
- `required_worker` (`openclaw|paperclip`, recommended)
- `runtime_decision_id` (string, recommended)
- `approval_required` (bool, optional)

Policy-derived optional constraints:

- `allowed_actions[]`
- `allowed_connectors[]`
- `budget_limits`
- `timeout_seconds`

## 4. Worker API Contract to BRAiN

Workers interact only via TaskQueue endpoints:

- `POST /api/tasks/claim`
- `POST /api/tasks/{task_id}/start`
- `POST /api/tasks/{task_id}/complete`
- `POST /api/tasks/{task_id}/fail`

Auth must be service/agent principal scoped to task operations.

## 5. Result Contract (`complete`)

`TaskComplete.result` should contain:

- `executor_type`
- `status` (`completed`)
- `processed_at` (ISO timestamp)
- `skill_run_id`
- `output` (sanitized object)
- `external_refs` (executor-native identifiers)
- `cost` (optional)
- `artifacts` (optional)

## 6. Failure Contract (`fail`)

`TaskFail` should contain:

- `error_message` (sanitized)
- `error_details` object with:
  - `executor_type`
  - `error_code`
  - `retryable`
  - `external_refs` (optional)

Error classes:

- `EXECUTOR_UNAVAILABLE`
- `AUTH_FAILED`
- `POLICY_BLOCKED`
- `APPROVAL_REQUIRED`
- `CONNECTOR_BLOCKED`
- `TIMEOUT`
- `EXECUTION_FAILED`

## 7. SkillRun Terminal Mapping

- Task completed -> `SkillRun.succeeded`
- Task failed (no retry) -> `SkillRun.failed`
- Approval-required unresolved -> `SkillRun.waiting_approval` (or fail closed by policy)
- Cancel request honored -> `SkillRun.cancelled`

TaskQueue owns retry behavior; terminalization into `SkillRun` remains centralized.

## 8. Governance and Policy Rules

1. Executor activation controlled by runtime policy (`allowed_executors`).
2. External connector calls must respect `allowed_connectors`.
3. Sensitive actions require approval according to policy.
4. Violations fail closed and emit audit/control-plane events.

## 9. Security Requirements

1. No shared admin credentials for workers.
2. Service principal + scoped permissions required.
3. Short-lived token/lease model recommended.
4. Tenant and correlation context must be preserved end-to-end.

## 10. Observability Requirements

Each external execution must emit:

- `decision_id` / `runtime_decision_id` where available
- `skill_run_id`, `task_id`, `correlation_id`
- executor type
- status transitions
- cost and failure metadata

UI surfaces should present external activity uniformly as `skillrun_tasklease` source.
