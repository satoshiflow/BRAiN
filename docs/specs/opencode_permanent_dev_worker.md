# OpenCode as Permanent Dev Worker in BRAiN

Version: 1.0
Status: Proposed MVP-to-Production Specification
Owner: BRAiN Control Plane / OpenCode Execution Integration
Reviewers: `brain-review-critic`, Mecker Agent, strict governance review
Related:
- `docs/specs/opencode_permanent_dev_worker_backlog.md`
- `docs/specs/opencode_permanent_dev_worker_interfaces.md`
- `docs/specs/opencode_permanent_dev_worker_review_briefing.md`
- `docs/specs/opencode_execution_consolidation_plan.md`
- `docs/specs/self_healing_control_loop.md`
- `docs/specs/approval_gate.md`
- `docs/specs/runtime_deployment_contract.md`
- `docs/core/agent_operating_matrix.md`
- `docs/core/brain_skill_execution_standard.md`

---

## 1 Purpose

This specification defines how OpenCode operates as a permanent Dev-Worker inside BRAiN without becoming a second control plane.

The target outcome is:

- BRAiN remains the canonical Control Plane for governance, policy, audit, risk, verification, and approval
- OpenCode becomes the canonical Execution Plane for `plan`, `build`, `heal`, and `evolve`
- AXE remains an external intent ingress and never receives direct mutation authority over OpenCode
- the system is deployable in the near term on `docker-compose` and Coolify with fail-closed guardrails

Why: BRAiN needs production-usable execution autonomy, but governance-sensitive decisions must stay centralized and auditable.

---

## 2 Executive Summary

- OpenCode is a permanently running worker service and only accepts signed `JobContract` payloads issued by BRAiN. Why: This prevents shadow control-plane behavior.
- BRAiN owns policy, risk classification, approvals, audit durability, verification policy, and kill-switch authority. Why: Decision rights must not move into the executor.
- OpenCode owns plan/build/heal/evolve execution within an allowlisted action surface. Why: Execution autonomy is useful only if it is bounded and deterministic.
- `plan` is read-only, `build` is repo-mutating, `heal` is incident-oriented, and `evolve` is proposal-oriented with the strictest validation. Why: Mode-based constraints are easier to operate than per-prompt trust.
- Every mutating action must pass `gate -> execute -> verify -> finalize/rollback`. Why: Unverified mutation is not production-safe.
- Risk class `R0-R4` determines auto-run, approval, or block. Why: A single unified risk language reduces governance ambiguity.
- `R4` actions are hard-blocked in the MVP, even if a policy bug exists. Why: Critical fail-safe behavior must be technical, not just procedural.
- Audit uses a durable PostgreSQL outbox before EventStream publish. Why: Event delivery failure must not create audit loss.
- Self-healing starts with safe reversible actions only: diagnosis, restarts, config restore, and rollback to last-known-good. Why: Early autonomy must minimize blast radius.
- BRAiN Core evolution happens through `EvolutionProposal -> ValidationRun -> PromotionDecision`, never by direct worker self-modification on `main`. Why: Learning and promotion require different governance levels.
- Deployment is a separate OpenCode container with private networking, scoped secrets, and no public ingress. Why: Isolation is mandatory for near-term production use.
- The coding agent should implement the MVP in two controlled sprints and expect an aggressive second-pass review by the Mecker Agent and `brain-review-critic`. Why: Execution speed must be paired with adversarial review.

---

## 3 Scope

### In Scope

- permanent OpenCode worker service
- Control Plane / Execution Plane split
- job contract, lifecycle, audit, eventing, approvals, kill-switches
- self-healing operating model
- constrained BRAiN Core evolution path
- deployment on local `docker-compose` and remote Coolify
- MVP delivery plan for 4-6 weeks and 90-day expansion path

### Out of Scope for MVP

- direct autonomous production schema migrations
- direct secret rotation by OpenCode
- unrestricted host shell access
- direct merge to `main` by OpenCode
- cross-tenant knowledge promotion without explicit governance extension

Why: The MVP should create immediate operational value without introducing irreversible or high-blast-radius automation.

---

## 4 Architectural Principles

1. Control Plane stays canonical. Why: Governance and execution must never become ambiguous.
2. Execution is contract-bound. Why: The worker must never improvise outside the signed job scope.
3. Every critical path is fail-closed. Why: Missing policy, audit, approval, or verification must stop mutation.
4. One writer per implementation surface. Why: The repository already uses the one-writer rule to prevent drift.
5. Evolution is stricter than execution. Why: System self-change has higher long-term risk than normal delivery work.
6. Durable audit precedes asynchronous event publication. Why: Evidence must survive message-bus failure.
7. Tenant isolation is enforced technically, not conventionally. Why: Shared context is a common hidden failure mode.
8. Short-term production value beats big-bang migration. Why: BRAiN should gain safe capability incrementally.

---

## 5 Target Architecture

### 5.1 Control Plane vs Execution Plane

```text
                         +--------------------------+
AXE / UI / API --------> | BRAiN Intent Gateway     |
                         | normalize + auth         |
                         +------------+-------------+
                                      |
                                      v
                         +--------------------------+
                         | BRAiN Control Plane      |
                         | policy/risk/approval     |
                         | audit/verify/registry    |
                         +---+-----------+----------+
                             |           |
                   signed job|           |durable outbox + EventStream
                             v           v
                     +--------------------------+
                     | Job Orchestrator         |
                     | queue/state/leases       |
                     +------------+-------------+
                                  |
                                  v
                     +--------------------------+
                     | OpenCode Worker          |
                     | plan/build/heal/evolve   |
                     | scoped adapters only     |
                     +---+-----------+----------+
                         |           |
                         |           +------------------+
                         |                              |
                         v                              v
               +------------------+          +----------------------+
               | Repo Workspace   |          | Runtime Adapters     |
               | branch/test/build|          | restart/rollback/etc |
               +------------------+          +----------------------+
```

Why: This split ensures all authority originates in BRAiN while OpenCode remains a bounded execution engine.

### 5.2 Component List

#### Control Plane Components

- `Intent Gateway`: receives AXE, UI, API, scheduler, or system intents and normalizes them. Why: OpenCode should never parse raw external intent directly.
- `Policy Decision Engine`: computes policy snapshot, allowed actions, denied actions, and verify profile. Why: Execution rules must be explicit and versioned.
- `Risk Classifier`: assigns `R0-R4` using action type, target environment, blast radius, and asset criticality. Why: Approval logic must be deterministic.
- `Approval Service`: issues pending approval records and consumes decisions. Why: Human intervention must be explicit and durable.
- `Job Orchestrator`: persists jobs, assigns leases, handles retries, expiry, and stuck-job recovery. Why: Queue-only semantics are insufficient for production control.
- `Audit Outbox`: stores canonical audit records before event publication. Why: Compliance requires durable evidence.
- `Verification Coordinator`: runs post-execution checks and decides `succeeded` or `rollback_pending`. Why: Mutation without verification is incomplete.
- `Kill-Switch Service`: blocks new jobs and cancels live jobs by tenant, mode, or global scope. Why: Incident containment must be fast and central.

#### Execution Plane Components

- `OpenCode Worker`: receives signed jobs, executes allowed phases, reports heartbeats and evidence. Why: The worker should be replaceable without changing governance.
- `Workspace Manager`: creates isolated workspaces and mounts them with mode-aware permissions. Why: Repo mutation must not leak across tenants or jobs.
- `Action Adapter Layer`: wraps git/test/build/restart/rollback/deploy actions behind allowlists. Why: Direct tool freedom is too dangerous for production.
- `Evidence Collector`: stores logs, diffs, test results, build artifacts, and rollback outputs. Why: Verification and audit need structured evidence.

#### Storage and Messaging

- `PostgreSQL`: canonical store for jobs, approvals, audit outbox, and status history. Why: Job control state must be durable and queryable.
- `Redis`: ephemeral queueing, leases, replay guards, and short-lived caches. Why: Fast coordination helps throughput but must not be the source of truth.
- `EventStream`: canonical event backbone for observability and downstream consumers. Why: BRAiN already treats EventStream as canonical.

---

## 6 Runtime Modes

### 6.1 Mode Semantics

| Mode | Purpose | Allowed | Forbidden | Default Verify |
|---|---|---|---|---|
| `plan` | analyze and propose | read repo, read logs, inspect health, produce plans | write code, restart service, deploy, merge, mutate config | `none` or `light` |
| `build` | implement and validate changes | branch, patch, lint, test, build, create artifact/PR | direct `main` merge, direct prod deploy, secret listing | `standard` |
| `heal` | incident diagnosis and bounded remediation | inspect logs, health checks, safe restart, config restore, rollback last-known-good | schema migration, destructive DB ops, free shell, unbounded infra changes | `standard` or `strict` |
| `evolve` | propose and validate improvements to BRAiN Core | create proposal branch, run benchmarks, validation runs, prepare promotion package | direct prod activation, direct self-promotion, cross-tenant promotion | `strict` |

Why: Modes turn abstract autonomy into an explicit security boundary.

### 6.2 Allowed Actions by Mode

#### `plan`

- `repo.read`
- `logs.read`
- `metrics.read`
- `health.check`
- `diff.analyze`
- `plan.emit`

Why: Planning should be high-trust and low-risk, so it must stay non-mutating.

#### `build`

- all `plan` actions
- `workspace.create`
- `git.branch.create`
- `repo.patch.apply`
- `lint.run`
- `test.run`
- `build.run`
- `artifact.publish_internal`
- `pr.prepare`

Why: Build mode should deliver working change candidates without bypassing review or production release control.

#### `heal`

- all `plan` actions
- `service.restart`
- `config.restore`
- `artifact.rollback`
- `queue.unstick`
- `cache.clear_scoped`
- `incident.note.append`

Why: Healing needs a narrow set of reversible operational actions, not general infrastructure power.

#### `evolve`

- all `build` actions
- `benchmark.run`
- `validation.run`
- `evolution.proposal.create`
- `promotion.package.prepare`

Why: Evolution should produce promotable evidence, not direct unsupervised change activation.

### 6.3 Mode Fail-Safe Rules

- `plan` jobs fail closed if workspace is writable. Why: Read-only guarantees must be technical.
- `build` jobs fail closed if verification cannot run. Why: Mutation without checks is unsafe.
- `heal` jobs fail closed if rollback strategy is missing for `R2+`. Why: Recovery actions need an escape path.
- `evolve` jobs fail closed if validation baseline or promotion policy is unavailable. Why: Self-improvement without comparison invites drift.

---

## 7 JobContract Design

### 7.1 Canonical Contract

`JobContract` is the only allowed execution ticket for OpenCode.

Why: A single contract surface avoids fragmented execution semantics.

### 7.2 JobContract JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "brain/job-contract.v1",
  "title": "JobContract",
  "type": "object",
  "required": [
    "job_id",
    "contract_version",
    "tenant_id",
    "intent_source",
    "requested_mode",
    "risk_class",
    "policy_snapshot_id",
    "approval_policy",
    "requested_actions",
    "repo_ref",
    "workspace_ref",
    "target_environment",
    "correlation_id",
    "priority",
    "status",
    "idempotency_key",
    "created_at",
    "created_by",
    "execution_budget",
    "verify_profile",
    "audit_required",
    "signature"
  ],
  "properties": {
    "job_id": { "type": "string", "pattern": "^job_[a-zA-Z0-9_-]{12,}$" },
    "contract_version": { "type": "string", "const": "v1" },
    "tenant_id": { "type": "string", "minLength": 3, "maxLength": 64 },
    "org_id": { "type": "string", "minLength": 1, "maxLength": 64 },
    "intent_source": { "type": "string", "enum": ["axe", "ui", "api", "scheduler", "system"] },
    "intent_id": { "type": "string" },
    "mission_id": { "type": "string" },
    "parent_job_id": { "type": "string" },
    "requested_mode": { "type": "string", "enum": ["plan", "build", "heal", "evolve"] },
    "risk_class": { "type": "string", "enum": ["R0", "R1", "R2", "R3", "R4"] },
    "policy_snapshot_id": { "type": "string" },
    "approval_policy": { "type": "string", "enum": ["auto", "approval_required", "blocked"] },
    "requested_actions": {
      "type": "array",
      "minItems": 1,
      "items": { "type": "string" }
    },
    "allowed_actions": {
      "type": "array",
      "items": { "type": "string" }
    },
    "forbidden_actions": {
      "type": "array",
      "items": { "type": "string" }
    },
    "repo_ref": {
      "type": "object",
      "required": ["repo", "branch", "commit_sha"],
      "properties": {
        "repo": { "type": "string" },
        "branch": { "type": "string" },
        "commit_sha": { "type": "string", "minLength": 7 }
      }
    },
    "workspace_ref": {
      "type": "object",
      "required": ["mount_path", "read_only"],
      "properties": {
        "mount_path": { "type": "string" },
        "read_only": { "type": "boolean" }
      }
    },
    "target_environment": { "type": "string", "enum": ["dev", "staging", "prod"] },
    "target_services": {
      "type": "array",
      "items": { "type": "string" }
    },
    "target_paths": {
      "type": "array",
      "items": { "type": "string" }
    },
    "secrets_scope": {
      "type": "array",
      "items": { "type": "string" }
    },
    "secret_refs": {
      "type": "array",
      "items": { "type": "string" }
    },
    "correlation_id": { "type": "string" },
    "causation_id": { "type": "string" },
    "priority": { "type": "string", "enum": ["low", "normal", "high", "urgent"] },
    "status": {
      "type": "string",
      "enum": [
        "draft",
        "queued",
        "gated",
        "awaiting_approval",
        "approved",
        "running",
        "verifying",
        "succeeded",
        "failed",
        "rollback_pending",
        "rolled_back",
        "blocked",
        "cancelled",
        "expired"
      ]
    },
    "idempotency_key": { "type": "string", "minLength": 12, "maxLength": 128 },
    "execution_budget": {
      "type": "object",
      "required": ["max_runtime_seconds", "max_cost_usd", "max_review_cycles"],
      "properties": {
        "max_runtime_seconds": { "type": "integer", "minimum": 30, "maximum": 7200 },
        "max_cost_usd": { "type": "number", "minimum": 0, "maximum": 250 },
        "max_review_cycles": { "type": "integer", "minimum": 0, "maximum": 3 }
      }
    },
    "verify_profile": { "type": "string", "enum": ["none", "light", "standard", "strict"] },
    "rollback_strategy": {
      "type": "string",
      "enum": ["none", "git_revert_branch", "service_restart", "config_restore", "artifact_redeploy"]
    },
    "rollback_ref": { "type": "string" },
    "approval_refs": {
      "type": "array",
      "items": { "type": "string" }
    },
    "evidence_refs": {
      "type": "array",
      "items": { "type": "string" }
    },
    "audit_required": { "type": "boolean", "const": true },
    "created_at": { "type": "string", "format": "date-time" },
    "not_before": { "type": "string", "format": "date-time" },
    "expires_at": { "type": "string", "format": "date-time" },
    "created_by": {
      "type": "object",
      "required": ["actor_type", "actor_id"],
      "properties": {
        "actor_type": { "type": "string", "enum": ["user", "system", "agent"] },
        "actor_id": { "type": "string" }
      }
    },
    "signature": { "type": "string", "minLength": 32 }
  },
  "allOf": [
    {
      "if": { "properties": { "requested_mode": { "const": "plan" } } },
      "then": {
        "properties": {
          "workspace_ref": {
            "properties": {
              "read_only": { "const": true }
            }
          }
        }
      }
    },
    {
      "if": { "properties": { "risk_class": { "enum": ["R2", "R3"] } } },
      "then": { "properties": { "approval_policy": { "const": "approval_required" } } }
    },
    {
      "if": { "properties": { "risk_class": { "const": "R4" } } },
      "then": { "properties": { "approval_policy": { "const": "blocked" } } }
    }
  ]
}
```

### 7.3 Validation Rules

- `signature`, `policy_snapshot_id`, and `idempotency_key` must validate before queueing. Why: OpenCode must reject any unauthenticated execution request.
- `expires_at` must be less than 24 hours after `created_at`, and less than 2 hours for `prod`. Why: Stale approvals and replay windows must stay narrow.
- `plan` forces `workspace_ref.read_only=true`. Why: Read-only planning must be enforced by contract.
- `build`, `heal`, and `evolve` require `verify_profile != none`. Why: Mutating work always needs verification.
- `heal` with `risk_class` in `R2-R3` requires non-`none` `rollback_strategy`. Why: Recovery without fallback is unacceptable.
- `prod` always requires non-empty `approval_refs` in the MVP. Why: Near-term production deployment should remain approval-first.
- `requested_actions` must be a subset of the mode allowlist. Why: The mode boundary must remain authoritative.
- `secret_refs` must be resolvable to job-scoped leases only. Why: Secret access must be least-privilege and short-lived.

### 7.4 Minimal APIs

- `POST /api/v1/opencode/jobs`
- `GET /api/v1/opencode/jobs/{job_id}`
- `POST /api/v1/opencode/jobs/{job_id}/cancel`
- `POST /api/v1/opencode/jobs/{job_id}/approve`
- `POST /api/v1/opencode/jobs/{job_id}/reject`
- `POST /api/v1/opencode/jobs/{job_id}/breakglass`
- `GET /api/v1/opencode/jobs?status=running`
- `GET /api/v1/opencode/kill-switch`
- `POST /api/v1/opencode/kill-switch/engage`
- `POST /api/v1/opencode/kill-switch/release`

Why: A narrow API surface is easier to secure and test.

---

## 8 Status Lifecycle

### 8.1 Canonical Lifecycle

```text
draft
  -> queued
  -> gated
  -> awaiting_approval | approved | blocked
  -> running
  -> verifying | failed | cancelled
  -> succeeded | rollback_pending
  -> rolled_back | failed
```

Why: Explicit state boundaries prevent hidden transitions and ambiguous retries.

### 8.2 Transition Table

| From | To | Condition |
|---|---|---|
| `draft` | `queued` | contract validated, signed, and persisted |
| `queued` | `gated` | policy and risk classification complete |
| `gated` | `awaiting_approval` | `approval_policy=approval_required` |
| `gated` | `approved` | `approval_policy=auto` |
| `gated` | `blocked` | `approval_policy=blocked` |
| `awaiting_approval` | `approved` | valid approval received before expiry |
| `awaiting_approval` | `expired` | TTL reached without decision |
| `approved` | `running` | worker lease granted |
| `approved` | `cancelled` | job cancelled before start |
| `running` | `verifying` | execution finished and evidence captured |
| `running` | `failed` | non-recoverable execution failure |
| `running` | `cancelled` | kill-switch or explicit cancellation |
| `verifying` | `succeeded` | all mandatory verification checks passed |
| `verifying` | `rollback_pending` | verification failed and rollback defined |
| `rollback_pending` | `rolled_back` | rollback succeeded |
| `rollback_pending` | `failed` | rollback failed |
| `failed` | `queued` | explicit retry with same idempotency family and new lease |

Why: The coding agent needs deterministic lifecycle behavior for implementation and tests.

---

## 9 Event and Audit Design

### 9.1 Event Ordering Rule

The mandatory event order is:

`job.created -> job.gated -> approval/block -> job.started -> phase/action events -> verification.completed -> job.completed|job.failed -> rollback.* if needed`

Why: A stable causal chain is required for forensics, metrics, and replay.

### 9.2 Event Types and Minimum Payload

| Event Type | Minimum Payload |
|---|---|
| `job.created` | `event_id, occurred_at, job_id, tenant_id, mode, risk_class, created_by, correlation_id` |
| `job.gated` | `job_id, policy_snapshot_id, approval_policy, allowed_actions, forbidden_actions` |
| `job.approval_requested` | `job_id, approver_role, reason, expires_at` |
| `job.approved` | `job_id, approval_id, approver_id, approved_actions` |
| `job.rejected` | `job_id, approval_id, approver_id, reason` |
| `job.blocked` | `job_id, block_reason, violated_policy_refs` |
| `job.started` | `job_id, worker_id, workspace_ref, start_sha` |
| `phase.started` | `job_id, phase, cycle_index` |
| `action.requested` | `job_id, action_id, action_type, target_ref, risk_class` |
| `action.executed` | `job_id, action_id, exit_code, artifact_refs, evidence_refs` |
| `verification.completed` | `job_id, verify_profile, result, failed_checks, evidence_refs` |
| `rollback.started` | `job_id, rollback_strategy, rollback_ref, trigger_reason` |
| `rollback.completed` | `job_id, result, restored_to_ref` |
| `job.completed` | `job_id, result, final_status, duration_ms, cost_usd` |
| `job.failed` | `job_id, failure_class, sanitized_error, failed_phase` |
| `evolution.proposed` | `job_id, proposal_id, candidate_ref, validation_plan_ref` |
| `kill_switch.engaged` | `tenant_id, scope, reason, engaged_by` |

Why: Event consumers should rely on a small canonical minimum even as payloads grow later.

### 9.3 Audit Durability Rules

- Every mutating job must write an outbox audit record before OpenCode begins execution. Why: No mutation should be possible without durable evidence.
- Audit and EventStream payloads must share `correlation_id` and `job_id`. Why: Joining execution traces later must be reliable.
- If EventStream publish fails after outbox write, the job enters degraded execution mode and no further mutating actions may start. Why: Loss of visibility must halt escalation.
- Audit payloads must contain sanitized errors and separate internal stack references. Why: External traces must not leak internals.

### 9.4 Required Evidence Artifacts

- source commit SHA
- resulting branch or artifact reference
- lint/test/build output references
- diff summary for code-mutating jobs
- health snapshots before/after healing actions
- rollback evidence if rollback executed

Why: Verification must be evidence-based, not model-assertion-based.

---

## 10 Governance Gates

### 10.1 Risk Classes

| Class | Meaning | Typical Examples |
|---|---|---|
| `R0` | read-only, no mutation, low blast radius | repo read, log inspection, planning |
| `R1` | local or isolated mutation, easy recovery | branch patch, tests, internal artifact build |
| `R2` | bounded operational impact, reversible | staging restart, staged rollback, hotfix branch creation |
| `R3` | production-affecting or elevated blast radius | prod restart, prod config restore, prod rollback |
| `R4` | irreversible or governance-critical | schema migration, secret rotation, direct merge to `main` |

Why: Risk must map to consequence, not to implementation detail.

### 10.2 Gate Outcomes

- `auto`: job can run automatically after policy validation. Why: Safe actions should not wait for human review.
- `approval_required`: job pauses until explicit approval arrives. Why: Human accountability is needed for higher-impact actions.
- `blocked`: job cannot run in current product stage. Why: Some actions are too risky for MVP and must be technically denied.

### 10.3 Governance Matrix

| Action Type | Risk | Auto/Approval/Block | Rollback Strategy |
|---|---|---|---|
| repo read / diff analyze | `R0` | Auto | none |
| test plan / build plan emit | `R0` | Auto | none |
| logs read / metrics correlate | `R0` | Auto | none |
| branch create / workspace patch | `R1` | Auto | branch delete / workspace discard |
| lint / unit tests / local build | `R1` | Auto | none |
| PR or internal patch artifact create | `R1` | Auto | artifact discard |
| staging deployment artifact build | `R1` | Auto | artifact invalidate |
| service restart in staging | `R2` | Approval | restart again / last-known-good |
| hotfix branch for production incident | `R2` | Approval | branch revert |
| staging rollback | `R2` | Approval | artifact redeploy |
| prod readiness validation | `R2` | Approval | cancel validation |
| service restart in prod | `R3` | Approval | service restart / artifact rollback |
| config restore in prod | `R3` | Approval | `config_restore` previous snapshot |
| prod rollback to last-known-good | `R3` | Approval | artifact redeploy |
| schema migration | `R4` | Block (MVP) | n/a |
| secret rotation by worker | `R4` | Block (MVP) | n/a |
| cross-tenant knowledge promotion | `R4` | Block (MVP) | n/a |
| direct merge to `main` by worker | `R4` | Block (MVP) | n/a |
| direct prod deploy without gate | `R4` | Block (always) | n/a |

Why: The coding agent can implement this matrix directly as policy tables and test fixtures.

### 10.4 Approval and Breakglass

- `approval` is for normal governed execution. Why: Most risky operations are planned and reviewable.
- `breakglass` is for urgent healing only, with incident reference, justification, and TTL <= 30 minutes. Why: Emergency rights must be narrow and visible.
- Breakglass never downgrades `R4` in the MVP. Why: Emergency access should not unlock the most dangerous operations.
- Approval and breakglass are single-use and bound to intent hash and policy snapshot hash. Why: Decisions must not be replayable on altered jobs.

---

## 11 Security Model

### 11.1 Tenant Isolation

- Each job must carry exactly one `tenant_id` and one workspace scope. Why: Mixed-tenant execution is not audit-safe.
- Workspace mounts are per-job and per-tenant; no shared writable workspace across tenants. Why: Isolation must survive worker bugs.
- Cache and lease keys are namespaced by tenant and job. Why: Shared ephemeral state can still leak behavior.

### 11.2 Secrets

- OpenCode never stores raw secrets durably. Why: The executor must not become a secret store.
- BRAiN issues short-lived secret leases for each job. Why: Secret lifetime should match execution lifetime.
- Secrets are scoped to the exact adapter action, not to the whole worker process where possible. Why: Least privilege reduces blast radius.
- Secret values are redacted in all logs, events, and evidence records. Why: Audit visibility must not leak credentials.

### 11.3 Container and Network Boundaries

- OpenCode runs in a separate container and private network. Why: Isolation should exist at the runtime boundary, not just in code.
- No public ingress to OpenCode; all calls originate from BRAiN internal network. Why: The worker must not expose a second API surface to the outside.
- No Docker socket mount for OpenCode. Why: Docker access would effectively grant host-level control.
- No unrestricted SSH agent forwarding. Why: Repository and infrastructure operations must remain scoped and auditable.

### 11.4 Kill-Switches

- Global kill-switch blocks all new jobs and requests graceful cancellation of running jobs. Why: A systemic incident needs an immediate safety stop.
- Tenant kill-switch blocks all jobs for one tenant. Why: Isolation incidents should not require global downtime.
- Mode kill-switch blocks one capability class such as `heal` or `evolve`. Why: A single unsafe mode should be independently stoppable.
- Adapter kill-switch blocks one concrete action type such as `service.restart`. Why: Fine-grained containment reduces collateral damage.

### 11.5 Fail-Closed Rules

- policy unavailable -> block mutating jobs
- approval missing or expired -> block job start
- audit outbox unavailable -> block mutating jobs
- verification unavailable -> fail job before completion
- secret broker unavailable -> block action requiring secret
- kill-switch active -> reject lease and cancel pending actions

Why: Safety must hold when dependencies are degraded, not only when they are healthy.

---

## 12 Self-Healing Operating Model

### 12.1 Goal

OpenCode supports the Self-Healing Control Loop as the execution backend for approved or auto-approved remediation jobs.

Why: The existing control-loop concept needs a bounded execution worker to become operational.

### 12.2 MVP Healing Actions

- `diagnose_only`
- `service_restart`
- `config_restore`
- `artifact_rollback`
- `queue_unstick`
- `cache_clear_scoped`

Why: These actions are common, bounded, and comparatively reversible.

### 12.3 Healing Flow

```text
signal detected
  -> BRAiN classifies incident
  -> recovery policy selected
  -> JobContract issued in mode=heal
  -> OpenCode executes approved action
  -> BRAiN verifies outcome
  -> success | rollback | escalate
```

Why: Healing remains governed by BRAiN even when OpenCode performs the action.

### 12.4 Healing Restrictions

- No destructive DB maintenance in MVP. Why: Such actions are hard to rollback safely.
- No multi-step autonomous healing workflows in MVP. Why: Single-step remediation is easier to validate and audit.
- No repeated retries beyond configured budget. Why: Infinite healing loops can worsen incidents.
- No healing on one tenant based on signals from another tenant. Why: Cross-tenant coupling breaks isolation.

---

## 13 BRAiN Core Evolution Model

### 13.1 Principle

OpenCode may help BRAiN evolve, but only through governed proposal and validation flows.

Why: Self-improvement is valuable only when it remains reversible and evidence-backed.

### 13.2 Evolution Pipeline

```text
experience / recurring issue
  -> EvolutionProposal
  -> experiment branch
  -> ValidationRun
  -> Review package
  -> PromotionDecision
  -> staged activation
```

Why: The system should learn from execution without directly self-promoting unreviewed changes.

### 13.3 Evolution Artifacts

- `EvolutionProposal`
- `ValidationRun`
- `PromotionDecision`
- `RollbackDecision`
- evidence package containing benchmarks, diffs, verifier output, and risk notes

Why: Durable artifacts create a safe bridge from execution to learning and eventually to promotion.

### 13.4 Evolution Restrictions

- no direct writes to active production branch
- no silent prompt/policy mutation in place
- no activation without verification and explicit promotion decision
- no cross-tenant learning promotion in MVP

Why: Evolution must be more constrained than ordinary build execution.

---

## 14 Deployment Design

### 14.1 Local `docker-compose`

Required services:

- `backend` / BRAiN API
- `opencode-worker`
- `postgres`
- `redis`
- optional `qdrant`

Recommended characteristics:

- internal-only network between `backend` and `opencode-worker`
- bind-mount repo workspace for local development
- dedicated env vars for worker mode, secret broker endpoint, and lease heartbeat
- separate worker health endpoint for liveness/readiness

Why: Local development should mirror production topology closely enough to reduce cutover surprises.

### 14.2 Remote / Coolify

OpenCode is deployed as its own service in Coolify with:

- private service URL only
- `DATABASE_URL` and `REDIS_URL` injected from platform
- scoped secret refs for repo credentials and internal API tokens
- CPU and memory limits configured explicitly
- restart policy `unless-stopped`
- readiness check requiring policy and audit dependencies

Why: A dedicated service is easier to isolate, restart, and scale than an embedded worker.

### 14.3 Resource Baseline

MVP starting point:

- `opencode-worker`: 1-2 CPU, 1-2 GB RAM, ephemeral workspace volume + optional persistent cache
- concurrency limit: 1 mutating job per worker, 2-4 read-only jobs per worker
- queue backpressure when verification latency grows or kill-switch is active

Why: Mutating jobs are CPU- and I/O-heavy and should remain serialized per worker initially.

### 14.4 Scaling Strategy

- scale read-heavy `plan` workers horizontally first
- keep mutating `build/heal/evolve` workers low-concurrency with lease coordination
- optionally split dedicated worker pools by mode after MVP

Why: Different modes have different safety and resource profiles.

---

## 15 Operations Model

### 15.1 SLOs

| SLO | Target |
|---|---|
| Job start latency P95 (`R0-R1`) | < 30s |
| Job start latency P95 (`approval_required`) | < 5 min after approval |
| Audit completeness | 100% for mutating jobs |
| Kill-switch propagation P95 | < 30s |
| Rollback activation P95 | < 5 min |
| Verification coverage (`build/heal/evolve`) | 100% |

Why: These targets are tight enough to drive engineering decisions without being unrealistic for the MVP.

### 15.2 Alerts

Alert on:

- stuck jobs without heartbeat
- audit outbox write failures
- repeated verification failures
- rollback failures
- duplicate execution detection
- approval queue aging beyond SLA
- kill-switch engaged
- tenant isolation violation attempt

Why: These signals map directly to governance or reliability risk.

### 15.3 Incident Runbook

1. Engage relevant kill-switch scope. Why: Stop further damage first.
2. Freeze affected queue leases. Why: Prevent duplicate or parallel mutation.
3. Inspect last durable audit records and evidence refs. Why: Audit is the canonical incident timeline.
4. Roll back to last-known-good if verification failed and rollback exists. Why: Safe restoration beats continued drift.
5. Escalate to human owner if rollback fails or `R3+` impact remains. Why: Some failures exceed allowed automation.
6. Record post-incident learning as `EvolutionProposal` or policy update candidate. Why: Incidents should improve the system over time.

### 15.4 Rollback Rules

- repo changes -> revert branch or discard workspace
- staging artifact change -> redeploy previous artifact
- prod restart/config restore -> last-known-good config or artifact rollback
- no rollback strategy -> job cannot auto-execute if `R2+`

Why: Rollback must be predefined, not improvised during failure.

---

## 16 KPI Set

| KPI | Definition | Target |
|---|---|---|
| `MTTR` | mean time to recovery for incidents handled by heal flow | < 20 min by day 90 |
| `CFR` | change failure rate for worker-executed mutating jobs | < 15% MVP, < 10% by day 90 |
| `AutoResolveRate` | percent of eligible incidents resolved without human execution | 25% MVP, 45% by day 90 |
| `RollbackRate` | percent of mutating jobs ending in rollback | < 8% |
| `ApprovalLeadTimeP95` | time from approval request to decision | < 15 min business hours |
| `AuditGapRate` | percent of mutating jobs with missing mandatory event chain | 0 |
| `DuplicateExecutionRate` | percent of jobs executed more than once unintentionally | < 0.5% |
| `PolicyBlockPrecision` | percent of blocked jobs later confirmed correctly blocked | > 90% |
| `VerificationPassRate` | percent of mutating jobs passing required verify on first run | > 80% MVP |
| `TenantIsolationIncidents` | confirmed cross-tenant leakage or mutation events | 0 |

Why: These KPIs measure both operational value and governance quality.

---

## 17 Security and Compliance Go/No-Go Checklist

- [ ] OpenCode has no public ingress and only accepts BRAiN-issued signed jobs. Why: Direct access would bypass governance.
- [ ] Every mutating job has durable audit before execution begins. Why: Compliance requires evidence before action.
- [ ] `R4` actions are technically blocked in the MVP. Why: The highest-risk paths must be impossible, not merely discouraged.
- [ ] Kill-switch works globally, per tenant, and per mode within SLO. Why: Fast containment is mandatory.
- [ ] Secrets are short-lived, scoped, and redacted. Why: Least privilege reduces breach impact.
- [ ] Workspaces are isolated per tenant/job. Why: Isolation failures are unacceptable.
- [ ] Verification is mandatory for all mutating jobs. Why: Unverified success is false confidence.
- [ ] Breakglass is single-use, justified, TTL-limited, and separately audited. Why: Emergency authority must stay exceptional.
- [ ] No unrestricted shell, Docker socket, or host-level mutation is available to the worker. Why: Those permissions collapse the security boundary.
- [ ] Approval service enforces non-self-approval and intent hash matching. Why: Human review must bind to the exact action.

Why: This checklist provides a direct production-readiness gate for reviewers and operators.

---

## 18 MVP Plan (4-6 Weeks)

### Sprint 1: Control Spine

#### P1 Job Spine

- implement `JobContract v1`
- persist jobs and lifecycle history
- enforce idempotency and expiry

Done criteria:

- contract validation passes for valid jobs and rejects invalid mode/risk combinations
- job status transitions are covered by tests
- duplicate `idempotency_key` requests do not double-execute

Why: The job spine is the foundation for all governed execution.

#### P1 Policy and Risk

- implement mode allowlists
- implement `R0-R4` classifier
- implement `auto / approval_required / blocked`

Done criteria:

- policy decision is deterministic for the same input
- `R4` actions are blocked by tests and runtime guard
- risk classification includes environment and action type

Why: Governance must exist before worker autonomy is expanded.

#### P1 Audit and Eventing

- implement durable outbox
- emit canonical job events
- correlate audit and event payloads by `job_id` and `correlation_id`

Done criteria:

- every mutating job emits full mandatory event chain in integration tests
- EventStream failure halts further mutation

Why: Production needs durable evidence before scaling automation.

#### P1 Worker Intake

- implement signed job intake
- implement worker lease and heartbeat
- support `plan` and `heal:diagnose_only`

Done criteria:

- unsigned jobs are rejected
- lost heartbeat causes lease recovery
- `plan` mode cannot write to workspace

Why: Start with safe read-heavy execution before mutating capabilities.

### Sprint 2: Safe Mutation

#### P1 Build Mode

- add isolated workspace creation
- support branch/patch/lint/test/build/PR artifact
- enforce verification before completion

Done criteria:

- worker can produce a branch or patch artifact with evidence refs
- failed verification prevents `succeeded`
- branch cleanup or workspace discard works on failure

Why: This creates immediate developer value with controlled blast radius.

#### P1 Heal Mode

- add `service_restart`, `config_restore`, `artifact_rollback`
- wire approval path for `R2-R3`
- add rollback execution path

Done criteria:

- staging restart works only via allowlisted adapter
- prod healing cannot start without approval
- rollback evidence is captured and queryable

Why: Self-healing becomes useful only when safe operational actions are executable.

#### P2 Evolve Proposal Flow

- add `EvolutionProposal` event emission
- support experiment branch and validation run
- package results for review

Done criteria:

- no evolve job can promote directly to production
- validation outputs are attached to proposal package

Why: Early evolution should prepare evidence, not bypass governance.

#### P2 Deployment and Ops

- add compose and Coolify service definitions
- add health checks, resource limits, and alerts

Done criteria:

- local compose and Coolify deploy same logical topology
- worker readiness fails if policy or audit dependency is unavailable

Why: Operational consistency reduces deployment risk.

---

## 19 90-Day Roadmap

### Days 0-30

- complete MVP control spine
- deploy `plan` + safe `build` + diagnose-only `heal`
- enable approval flow and kill-switches

Why: The first month should establish safe operational trust.

### Days 31-60

- add bounded healing adapters for staging and selected prod runbooks
- add stuck-job reaper and degraded-mode handling
- add dashboards and KPI reporting

Why: Reliability and observability are the next leverage points after basic execution works.

### Days 61-90

- introduce proposal-oriented `evolve` flow
- add canary-style validation package generation
- shadow-run selected legacy execution paths against OpenCode path

Why: Evolution and consolidation should begin only after job governance and healing are stable.

---

## 20 Implementation Guidance for the Coding Agent

### 20.1 Required Sequence

Follow:

`GROUNDING -> STRUCTURE -> CREATION -> EVALUATION -> FINALIZATION`

Why: This is already the BRAiN standard for reducing LLM execution errors.

### 20.2 Recommended Implementation Order

1. job schema and persistence
2. risk/policy engine
3. approval and breakglass integration
4. audit outbox and event publication
5. worker intake and lease model
6. `plan` mode
7. `build` mode
8. `heal` mode
9. `evolve` proposal mode
10. dashboards and runbooks

Why: This order establishes safety infrastructure before execution breadth.

Primary companion documents for implementation:

- backlog and ticket breakdown: `docs/specs/opencode_permanent_dev_worker_backlog.md`
- API and data contracts: `docs/specs/opencode_permanent_dev_worker_interfaces.md`
- adversarial review handoff: `docs/specs/opencode_permanent_dev_worker_review_briefing.md`

Why: The coding agent should not have to infer task slicing, interfaces, or review expectations from one long spec alone.

### 20.3 Mandatory Test Categories

- contract validation tests
- lifecycle transition tests
- risk matrix tests
- approval and breakglass tests
- tenant isolation tests
- idempotency and replay tests
- audit completeness tests
- kill-switch tests
- rollback tests
- verification-failure tests

Why: These tests cover the most dangerous failure classes in a governed worker system.

### 20.4 Explicit Review Hand-Off

After implementation, submit the result for review to:

- Mecker Agent as strict critical reviewer
- `brain-review-critic` for architecture and contract challenge review
- security/governance reviewer for fail-closed validation

Required review prompts:

- verify missing fields, lifecycle gaps, approval bypasses, and rollback blind spots
- verify OpenCode did not become a shadow control plane
- verify `R4` remains technically blocked in the MVP

Why: This feature area is governance-sensitive and benefits from adversarial second-pass review.

---

## 21 Ten Technical Decisions (ADR Style)

1. Decision: OpenCode is a separate container service, not an embedded library. Reason: Isolation and deployability matter more than in-process convenience.
2. Decision: BRAiN is the only issuer of executable jobs. Reason: Control authority must remain centralized.
3. Decision: `JobContract v1` is the sole execution contract. Reason: One contract avoids fragmented worker semantics.
4. Decision: Audit uses PostgreSQL outbox before EventStream. Reason: Durable evidence must survive transport failure.
5. Decision: Risk is modeled as `R0-R4`. Reason: Risk classes map cleanly to approval behavior and blast radius.
6. Decision: `plan` is technically read-only. Reason: Safety guarantees should not depend on model obedience.
7. Decision: `R4` is hard-blocked in the MVP. Reason: Near-term production safety requires hard technical denial for the most dangerous actions.
8. Decision: Verify is mandatory for all mutating modes. Reason: Mutation without validation is incomplete execution.
9. Decision: Healing uses allowlisted adapters only. Reason: Free-form shell healing is too dangerous.
10. Decision: Evolution produces proposals, not direct activation. Reason: Self-improvement must be evidence-backed and reversible.

---

## 22 Risks and Countermeasures

| Risk | Countermeasure |
|---|---|
| OpenCode becomes shadow control plane | reject all unsigned/non-BRAiN jobs; remove public ingress |
| audit/event gaps on partial failures | outbox first, reconciliation worker, degraded-mode halt |
| excessive worker privileges | no Docker socket, no unrestricted SSH, scoped adapters only |
| unsafe auto-healing worsens incidents | restrict MVP to reversible runbooks and require approval for `R2-R3` |
| repeated or duplicate execution | leases, heartbeats, idempotency keys, replay guards |
| tenant leakage through shared state | per-job workspace, namespaced caches, tenant-bound secrets |
| approval bottleneck | maximize `R0-R1` auto coverage and enforce approval SLAs |
| silent evolution drift | proposal/validation/promotion pipeline with mandatory review |

Why: Explicitly naming failure modes improves implementation quality and review precision.

---

## 23 Immediate Next 7 Days Plan

### Day 1

- finalize ADR for Control Plane vs Execution Plane
- freeze `JobContract v1` field set

Why: The coding agent needs a stable contract target before implementation.

### Day 2

- finalize `R0-R4` matrix and mode allowlists
- define blocked `R4` set for MVP

Why: Governance logic should be implemented from a locked table, not from prose.

### Day 3

- define status machine, event catalog, and audit ordering
- align with EventStream contract

Why: Data model and observability depend on these definitions.

### Day 4

- design compose/Coolify service topology, secrets injection, and health checks

Why: Deployment constraints influence runtime boundaries and config design.

### Day 5

- define approval and breakglass runbook with role ownership and SLA

Why: Human governance must be operable before production cutover.

### Day 6

- break MVP into implementation tickets for contract, worker, policy, audit, and verification

Why: Delivery speed improves when work is partitioned by ownership boundaries.

### Day 7

- run Go/No-Go review against section 17 and allow only `plan`, safe `build`, and diagnose-only `heal` for first production enablement

Why: A narrow first production scope reduces risk while proving the architecture.

---

## 24 Done Criteria

This specification is considered implemented at MVP level when:

- OpenCode runs as separate service under BRAiN control
- unsigned or out-of-policy jobs cannot execute
- mutating jobs always emit durable audit and complete verification
- `R4` actions are technically blocked
- kill-switches work within target SLO
- safe `build` and bounded `heal` use cases work end-to-end
- review by Mecker Agent and `brain-review-critic` has no unresolved blocker findings

Why: These criteria capture both system utility and governance integrity.

---

End of specification.
