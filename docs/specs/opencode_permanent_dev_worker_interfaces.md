# OpenCode Permanent Dev Worker Interfaces

Version: 1.0
Status: Canonical Companion Contract for MVP Implementation
Parent Spec: `docs/specs/opencode_permanent_dev_worker.md`
Related:
- `docs/specs/opencode_permanent_dev_worker_backlog.md`
- `docs/specs/opencode_permanent_dev_worker_review_briefing.md`
- `docs/specs/approval_gate.md`

---

## 1 Purpose

This document defines the low-level interfaces, persistence objects, APIs, error codes, and invariants required to implement the permanent OpenCode Dev-Worker.

Why: The parent specification is architectural; the coding agent needs narrower implementation contracts to avoid inventing incompatible APIs.

---

## 2 Canonical Domain Objects

### 2.1 OpenCodeJob

Canonical durable object backing `JobContract` execution.

Minimum fields:

| Field | Type | Required | Notes |
|---|---|---:|---|
| `job_id` | string | yes | canonical external id |
| `contract_version` | string | yes | `v1` |
| `tenant_id` | string(64) | yes | tenant scope |
| `org_id` | string(64) | no | optional org scope |
| `intent_source` | enum | yes | `axe`,`ui`,`api`,`scheduler`,`system` |
| `intent_id` | string | no | originating intent |
| `mission_id` | string | no | optional mission link |
| `parent_job_id` | string | no | retry or derivative link |
| `requested_mode` | enum | yes | `plan`,`build`,`heal`,`evolve` |
| `risk_class` | enum | yes | `R0`-`R4` |
| `policy_snapshot_id` | string | yes | policy version ref |
| `approval_policy` | enum | yes | `auto`,`approval_required`,`blocked` |
| `requested_actions` | jsonb | yes | raw requested set |
| `allowed_actions` | jsonb | yes | policy-derived set |
| `forbidden_actions` | jsonb | yes | policy-derived set |
| `repo_ref` | jsonb | yes | repo/branch/sha |
| `workspace_ref` | jsonb | yes | path/read_only |
| `target_environment` | enum | yes | `dev`,`staging`,`prod` |
| `target_services` | jsonb | no | service refs |
| `target_paths` | jsonb | no | path refs |
| `secret_refs` | jsonb | no | secret lease refs |
| `correlation_id` | string | yes | trace continuity |
| `causation_id` | string | no | parent trace ref |
| `priority` | enum | yes | `low`,`normal`,`high`,`urgent` |
| `status` | enum | yes | lifecycle state |
| `idempotency_key` | string | yes | replay protection |
| `execution_budget` | jsonb | yes | runtime/cost/review caps |
| `verify_profile` | enum | yes | `none`,`light`,`standard`,`strict` |
| `rollback_strategy` | enum | no | rollback type |
| `rollback_ref` | string | no | version or artifact ref |
| `approval_refs` | jsonb | no | approval ids |
| `evidence_refs` | jsonb | no | evidence ids |
| `signature` | string | yes | BRAiN-issued signature |
| `lease_owner` | string | no | current worker id |
| `lease_expires_at` | timestamptz | no | lease timeout |
| `created_at` | timestamptz | yes | created time |
| `updated_at` | timestamptz | yes | latest write |
| `started_at` | timestamptz | no | execution start |
| `completed_at` | timestamptz | no | terminal state time |

Why: The job object must be rich enough to drive execution, audit, retry, and review from one durable source.

### 2.2 OpenCodeJobTransition

Immutable lifecycle history row.

| Field | Type | Required | Notes |
|---|---|---:|---|
| `transition_id` | UUID | yes | internal row id |
| `job_id` | string | yes | parent job |
| `from_status` | enum | no | null for initial entry |
| `to_status` | enum | yes | target state |
| `reason_code` | string | yes | short machine code |
| `reason_detail` | text | no | sanitized detail |
| `actor_type` | enum | yes | `user`,`system`,`worker` |
| `actor_id` | string | yes | actor ref |
| `correlation_id` | string | yes | trace continuity |
| `created_at` | timestamptz | yes | transition time |

Why: State debugging and review depend on immutable transition history.

### 2.3 OpenCodeApproval

Use the existing approval concepts but bind them directly to OpenCode jobs.

Minimum delta on top of approval gate concepts:

- `job_id`
- `intent_hash`
- `policy_snapshot_hash`
- `gate_type`
- `status`
- `requested_by`
- `decided_by`
- `expires_at`

Why: Approval should be reusable in concept but concrete in scope for OpenCode jobs.

### 2.4 OpenCodeEvidence

| Field | Type | Required | Notes |
|---|---|---:|---|
| `evidence_id` | string | yes | canonical ref |
| `job_id` | string | yes | parent job |
| `evidence_type` | enum | yes | `log`,`test_result`,`build_result`,`diff`,`health_snapshot`,`rollback_result`,`proposal_package` |
| `storage_ref` | string | yes | durable location |
| `content_hash` | string | yes | integrity |
| `summary` | text | no | short display text |
| `created_at` | timestamptz | yes | evidence time |

Why: Verification and review need explicit evidence objects rather than ad hoc blobs.

---

## 3 API Contract

### 3.1 Create Job

- `POST /api/v1/opencode/jobs`

Request body:

- full `JobContract v1`

Response:

```json
{
  "job_id": "job_...",
  "status": "queued",
  "risk_class": "R1",
  "approval_policy": "auto",
  "correlation_id": "corr_..."
}
```

Why: Job creation must return the governed execution posture immediately.

### 3.2 Get Job

- `GET /api/v1/opencode/jobs/{job_id}`

Response minimum:

```json
{
  "job_id": "job_...",
  "status": "running",
  "requested_mode": "build",
  "risk_class": "R1",
  "approval_policy": "auto",
  "evidence_refs": [],
  "approval_refs": [],
  "updated_at": "2026-03-10T00:00:00Z"
}
```

Why: Operators and reviewers need a stable job read model.

### 3.3 List Jobs

- `GET /api/v1/opencode/jobs?status=<status>&mode=<mode>&tenant_id=<tenant_id>`

Why: Operational triage requires filtered job views.

### 3.4 Cancel Job

- `POST /api/v1/opencode/jobs/{job_id}/cancel`

Why: Controlled cancellation is part of incident handling and kill-switch propagation.

### 3.5 Approve Job

- `POST /api/v1/opencode/jobs/{job_id}/approve`

Request minimum:

```json
{
  "approver_id": "user_123",
  "reason": "approved for bounded production rollback"
}
```

Why: Approval should bind a named human to a concrete job decision.

### 3.6 Reject Job

- `POST /api/v1/opencode/jobs/{job_id}/reject`

Why: Rejection is a first-class governance outcome and should not be simulated as generic cancellation.

### 3.7 Breakglass

- `POST /api/v1/opencode/jobs/{job_id}/breakglass`

Request minimum:

```json
{
  "approver_id": "user_123",
  "incident_ref": "inc_456",
  "justification": "customer-facing outage, restart required",
  "ttl_seconds": 1800
}
```

Why: Emergency approval needs stricter data than normal approval.

### 3.8 Kill-Switch APIs

- `GET /api/v1/opencode/kill-switch`
- `POST /api/v1/opencode/kill-switch/engage`
- `POST /api/v1/opencode/kill-switch/release`

Request minimum for engage:

```json
{
  "scope": "tenant",
  "tenant_id": "tenant_a",
  "mode": null,
  "reason": "suspected isolation anomaly"
}
```

Why: Kill-switch semantics must be explicit and queryable.

---

## 4 Worker Internal Interfaces

### 4.1 Lease Acquisition

```text
acquire_lease(job_id, worker_id, lease_ttl_seconds) -> granted | denied
renew_lease(job_id, worker_id) -> granted | denied
release_lease(job_id, worker_id) -> acknowledged
```

Why: Single-owner execution is required for mutating jobs.

### 4.2 Execution Interface

```text
execute_job(job_id) -> execution_result
```

Execution result minimum:

- `job_id`
- `final_phase`
- `result`
- `evidence_refs`
- `failure_class`
- `rollback_started`

Why: The control plane needs a normalized worker result regardless of mode.

### 4.3 Verification Interface

```text
verify_job(job_id, verify_profile) -> verification_result
```

Verification result minimum:

- `job_id`
- `result`: `pass | fail | inconclusive`
- `failed_checks`
- `evidence_refs`

Why: Verify is a required phase and needs a dedicated contract.

---

## 5 Status Invariants

- terminal states are immutable except via explicit retry creating a new runnable attempt path. Why: Historical truth must not be rewritten.
- `running` requires a live lease. Why: Execution ownership must always be attributable.
- `succeeded` requires verification pass for mutating modes. Why: Success must mean validated success.
- `approved` is invalid when `approval_policy=auto` unless approval record exists due to later escalation. Why: Status semantics should remain consistent.
- `blocked` jobs never enter `running`. Why: A block outcome must be absolute.

---

## 6 Error Codes

### 6.1 Job Contract Errors

- `OCJ-001 INVALID_SIGNATURE`
- `OCJ-002 INVALID_MODE`
- `OCJ-003 INVALID_ACTION_FOR_MODE`
- `OCJ-004 RISK_POLICY_CONFLICT`
- `OCJ-005 EXPIRED_CONTRACT`
- `OCJ-006 IDEMPOTENCY_CONFLICT`
- `OCJ-007 TENANT_SCOPE_INVALID`
- `OCJ-008 SECRET_SCOPE_INVALID`

Why: The coding agent should implement explicit machine-readable failures, not free-text only.

### 6.2 Approval Errors

- `OCA-001 APPROVAL_REQUIRED`
- `OCA-002 APPROVAL_EXPIRED`
- `OCA-003 SELF_APPROVAL_FORBIDDEN`
- `OCA-004 INTENT_HASH_MISMATCH`
- `OCA-005 BREAKGLASS_NOT_ALLOWED`
- `OCA-006 BREAKGLASS_FIELDS_REQUIRED`

Why: Governance failures need precise rejection reasons for operators and reviewers.

### 6.3 Execution Errors

- `OCE-001 LEASE_NOT_GRANTED`
- `OCE-002 KILL_SWITCH_ACTIVE`
- `OCE-003 WORKSPACE_NOT_ISOLATED`
- `OCE-004 READ_ONLY_VIOLATION`
- `OCE-005 ADAPTER_NOT_ALLOWED`
- `OCE-006 VERIFY_UNAVAILABLE`
- `OCE-007 AUDIT_UNAVAILABLE`
- `OCE-008 ROLLBACK_REQUIRED`

Why: Execution failures should map directly to operational response.

---

## 7 Event Mapping

Use these event names exactly for the MVP:

- `job.created`
- `job.gated`
- `job.approval_requested`
- `job.approved`
- `job.rejected`
- `job.blocked`
- `job.started`
- `phase.started`
- `action.requested`
- `action.executed`
- `verification.completed`
- `rollback.started`
- `rollback.completed`
- `job.completed`
- `job.failed`
- `evolution.proposed`
- `kill_switch.engaged`
- `kill_switch.released`

Why: Stable event names are required for downstream consumers and tests.

---

## 8 Suggested Module Boundaries

Suggested backend module layout:

- `backend/app/modules/opencode_jobs/`
  - `schemas.py`
  - `models.py`
  - `service.py`
  - `router.py`
  - `policy.py`
  - `risk.py`
  - `events.py`
  - `tests/`
- `backend/app/modules/opencode_worker_control/`
  - `lease_service.py`
  - `kill_switch.py`
  - `approval_service.py`
  - `verification_service.py`
- `backend/app/modules/opencode_adapters/`
  - `build_adapter.py`
  - `heal_adapter.py`
  - `workspace_manager.py`
  - `evidence_service.py`

Why: Separating contracts, control, and adapters reduces coupling and supports the one-writer rule.

---

## 9 Test Matrix Minimum

- create valid `plan` job -> `queued`
- create invalid `plan` job with writable workspace -> reject
- create `R4` job -> `blocked`
- approval required job without approval -> cannot start
- breakglass without incident ref -> reject
- running job without heartbeat -> recoverable stale state
- `plan` mode write attempt -> fail
- `build` mode verification fail -> no `succeeded`
- `heal` action without rollback on `R2+` -> reject
- kill-switch engaged -> lease denied

Why: These tests hit the most important invariants first.

---

## 10 Review Linkage

Before review, package together:

- parent spec: `docs/specs/opencode_permanent_dev_worker.md`
- backlog: `docs/specs/opencode_permanent_dev_worker_backlog.md`
- interfaces: `docs/specs/opencode_permanent_dev_worker_interfaces.md`
- review brief: `docs/specs/opencode_permanent_dev_worker_review_briefing.md`

Why: Review quality improves when architecture, tasks, and contracts are inspected as one set.

---

End of interface contract.
