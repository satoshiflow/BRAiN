# Paperclip + OpenClaw Unified Executor Implementation Plan

Status: Draft (ready for execution)  
Owner: BRAiN Core Team  
Date: 2026-04-01

## 1) Goal

Integrate Paperclip as an external executor using the exact same canonical runtime path and governance model as OpenClaw.

Canonical path:

`Intent (AXE optional) -> BRAiN -> SkillRun -> TaskLease -> External Executor (OpenClaw/Paperclip) -> finalize_external_run`

## 2) Non-Negotiable Principles

1. `SkillRun` remains canonical runtime truth.
2. `TaskLease` remains subordinate dispatch/claim substrate.
3. AXE remains UI/intent ingress, not runtime authority.
4. OpenClaw and Paperclip must use identical security/governance classes.
5. External connector access is allowed only under BRAiN policy/approval.
6. Fail closed on policy uncertainty.

## 3) Current Baseline (already in repo)

- OpenClaw already integrated via SkillRun/TaskLease.
- Direct `axe_worker_runs` OpenClaw dispatch blocked by contract guard.
- Runtime-control already supports worker selection and connector allowlist checks.
- Odoo connector already demonstrates policy-gated connector invocation pattern.

## 4) Target Architecture

### 4.1 Executor classes

- `openclaw` -> external executor (existing)
- `paperclip` -> external executor (new)

Both run under same contract:

- task claim/start/complete/fail via TaskQueue API
- linked `skill_run_id` required
- finalization through Skill Engine terminalization path

### 4.2 Governance controls

- `workers.selection.allowed_executors`
- `security.allowed_connectors`
- `governance.approval_required` (action/risk dependent)
- runtime override hierarchy remains authoritative

### 4.3 External connector model

Paperclip may call external apps/containers only with BRAiN-approved execution permit:

- allowed actions
- allowed connectors
- TTL
- budget bounds
- correlation/audit bindings

## 5) Workstreams and Deliverables

## WS-A: External Executor Contract (P0)

Deliverables:

1. New spec: `docs/specs/external_executor_contract.md`
2. Standard payload/result/error schema for OpenClaw and Paperclip
3. Status mapping table to SkillRun terminal states

Required fields:

- `tenant_id`, `skill_run_id`, `correlation_id`
- `executor_type`
- `intent`
- `allowed_actions[]`
- `allowed_connectors[]`
- `approval_required`
- `budget_limits`
- `timeout_seconds`

Success criteria:

- Both executors can run through the same backend dispatch and finalization semantics.

## WS-B: Runtime-Control / Policy symmetry (P0)

Deliverables:

1. Runtime control keys for per-executor enable/disable
2. Shared policy enforcement for OpenClaw and Paperclip
3. Governance matrix for sensitive actions

Implementation targets:

- `backend/app/modules/runtime_control/service.py`
- `backend/app/modules/runtime_control/schemas.py`
- `backend/app/modules/policy/*` (only if needed for action-level evaluation)

Success criteria:

- Runtime decision can allow/deny either executor without code branching per surface.

## WS-C: Generic external dispatch path (P0)

Deliverables:

1. Refactor AXE fusion worker bridge from OpenClaw special-case to generic external executor dispatch.
2. Unified task type metadata for external workers.

Implementation targets:

- `backend/app/modules/axe_fusion/router.py`
- optional helper module: `backend/app/modules/external_workers/*`

Success criteria:

- OpenClaw behavior remains unchanged.
- Paperclip uses same dispatch flow with executor selector.

## WS-D: Paperclip worker adapter service (P0)

Deliverables:

1. New `paperclip_worker/` runtime service
2. TaskQueue polling loop (`claim/start/complete/fail`)
3. Mapping layer between TaskLease payload and Paperclip API calls
4. Compose integration in local stack

Implementation targets:

- `paperclip_worker/main.py`
- `paperclip_worker/Dockerfile`
- `docker-compose.local.yml`

Env vars:

- `PAPERCLIP_BASE_URL`
- `PAPERCLIP_API_KEY`
- `PAPERCLIP_WORKER_TASK_TYPES`
- `PAPERCLIP_AGENT_ID`
- `PAPERCLIP_POLL_INTERVAL_SECONDS`

Success criteria:

- Paperclip worker completes linked task and finalizes SkillRun reliably.

## WS-E: Auth and secret hardening (P0/P1)

Deliverables:

1. Service-principal auth for external workers (no shared admin login)
2. Scoped token permissions for task operations
3. Short-lived token/lease model for executor sessions

Implementation targets:

- `backend/app/core/auth_deps.py`
- auth/session issuance surfaces
- optional control-deck secret integration paths

Success criteria:

- OpenClaw and Paperclip both run least-privilege identities.

## WS-F: Connector permit enforcement (P1)

Deliverables:

1. Signed execution permit object
2. Permit validation in external executor actions
3. Deny + audit on out-of-permit action attempts

Implementation targets:

- runtime/policy integration points
- external executor adapter layer

Success criteria:

- Paperclip external actions cannot bypass BRAiN-approved connector/action scope.

## WS-G: UX and observability parity (P1)

Deliverables:

1. Unified AXE activity cards for both external executors
2. Runtime source, task id, skill_run id visibility
3. Approval/policy trace display

Implementation targets:

- `frontend/axe_ui/*`
- `frontend/controldeck-v3/*` (effective decision surfaces)

Success criteria:

- Operator sees OpenClaw/Paperclip with same status semantics and provenance.

## WS-H: Testing and release gating (P0)

Deliverables:

1. Backend unit/integration tests for dispatch/finalization/policy symmetry
2. Worker integration tests for Paperclip adapter loop
3. UI regression tests for worker cards/filters/status mapping

Verification commands:

- `cd backend && PYTHONPATH=. pytest tests/test_axe_worker_runs_service.py tests/test_axe_worker_runs_routes.py tests/test_task_queue_skill_run_lease.py -q`
- `cd backend && PYTHONPATH=. pytest -k "paperclip or external_executor" -q`
- `./scripts/run_rc_staging_gate.sh`
- `cd frontend/axe_ui && npm run lint && npm run test && npm run build`

Success criteria:

- All targeted tests pass.
- RC gate passes.

## 6) Step-by-step Execution Sequence

### Phase 0 - Contracts first

1. Create `external_executor_contract.md`.
2. Add status mapping + error taxonomy.
3. Review against existing OpenClaw flow and runtime harmonization contract.

### Phase 1 - Backend path unification

1. Introduce generic external executor dispatch helper.
2. Refactor OpenClaw branch to use helper.
3. Add Paperclip selector support without enabling runtime by default.
4. Add tests for no-regression OpenClaw path.

### Phase 2 - Paperclip runtime adapter

1. Add `paperclip_worker` service skeleton.
2. Implement claim/start/complete/fail loop.
3. Implement task payload -> Paperclip API mapping.
4. Add compose service + healthcheck.

### Phase 3 - Governance hardening

1. Add per-executor runtime-control toggles.
2. Enforce connector allowlist checks for executor actions.
3. Introduce permit validation for sensitive external actions.

### Phase 4 - UX parity + rollout

1. Surface Paperclip as `skillrun_tasklease` activity source in AXE.
2. Add policy/approval trace surfaces.
3. Shadow mode rollout, then canary tenant, then broader activation.

## 7) Acceptance Criteria (Definition of Done)

1. Paperclip and OpenClaw run through one canonical runtime pattern.
2. No direct runtime bypass path from AXE to either external executor.
3. Policy management can enable/disable both executors symmetrically.
4. External connector actions are policy-governed and auditable.
5. SkillRun remains canonical terminal truth for external executions.
6. Tests and RC gate are green.

## 8) Risks and Mitigations

1. Split state between task and skillrun.
   - Mitigation: central terminalization hook + reconciliation checks.
2. Credential overreach.
   - Mitigation: service principal + scoped short-lived tokens.
3. Policy drift between executors.
   - Mitigation: shared runtime-control keys and common enforcement middleware.
4. Paperclip API drift.
   - Mitigation: adapter isolation + retry/backoff + strict error taxonomy.

## 9) Rollback Strategy

1. Feature flag Paperclip executor off in runtime-control.
2. Keep OpenClaw path active and unchanged.
3. Preserve existing OpenClaw task type support for fallback.
4. Revert only adapter and dispatch selector changes if required.

## 10) Progress Tracker

- [x] WS-A contract spec committed
- [x] WS-B runtime-control symmetry
- [x] WS-C backend dispatch unification
- [x] WS-D paperclip worker adapter
- [x] WS-E auth/secret hardening
- [x] WS-F connector permit enforcement
- [x] WS-G UI/observability parity
- [x] WS-H tests + RC gate

---

Execution note:

Do not begin implementation phases until explicit user `Go` command is provided.
