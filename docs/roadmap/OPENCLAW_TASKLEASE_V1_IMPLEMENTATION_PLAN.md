# OpenClaw V1 Integration via SkillRun/TaskLease

Status: In Progress  
Owner: OpenCode Dev Agent  
Date: 2026-03-31

## Goal

Integrate OpenClaw as an external worker in a closed container environment,
without creating a second runtime path.

Canonical path:

`AXE -> BRAiN -> SkillRun -> TaskLease -> OpenClaw Worker -> finalize_external_run -> AXE`

## Architecture Decisions

1. SkillRun remains the single source of truth for runtime state.
2. TaskLease (TaskQueue) is the canonical worker delegation surface.
3. OpenClaw acts as a pure executor (claim/start/complete/fail).
4. AXE remains UX/intent ingress only, not runtime authority.
5. `axe_worker_runs` can remain as a thin facade but not as runtime truth.
6. V1 communication is REST + polling, no callback/webhook dependency.

## Scope (V1)

- Route `/openclaw` worker intent through SkillRun + TaskLease.
- Add OpenClaw task type metadata for worker selection.
- Finalize SkillRun automatically when TaskLease completes/fails.
- Add private OpenClaw service entry in local docker-compose.
- Add focused backend tests for the new path.

## Non-Goals (V1)

- No second runtime model.
- No OAuth framework rollout.
- No streaming/callback requirement.
- No bridge-first runtime design.
- No direct AXE -> OpenClaw execution authority.

## Implementation Plan

### Step 1 - AXE bridge alignment

- Update AXE worker dispatch path to create SkillRun and TaskLease for
  `worker_type=openclaw`.
- Keep response UX-compatible for AXE.

### Step 2 - TaskQueue finalization hook

- In task completion/failure, detect tasks linked to `skill_run_id`.
- Trigger `SkillEngineService.finalize_external_run(...)` with success/failure
  payload and sanitized errors.

### Step 3 - Runtime metadata and worker routing

- Use explicit `task_type` and tags for OpenClaw-targeted tasks.
- Preserve generic worker model for future workers.

### Step 4 - Container/runtime setup

- Add `openclaw` service in `docker-compose.local.yml` on private network.
- Keep service private (no required public ingress).

### Step 5 - Tests

- Add tests for:
  - OpenClaw worker dispatch creating TaskLease + linked SkillRun context.
  - Task completion finalizing SkillRun as succeeded.
  - Task failure finalizing SkillRun as failed.

## Risks and Mitigations

- Risk: Split state between Task and SkillRun.
  - Mitigation: finalize SkillRun in TaskQueue completion/failure path.
- Risk: Worker identity mismatch.
  - Mitigation: existing agent/service auth checks in task claim/start/complete/fail.
- Risk: OpenClaw unavailable.
  - Mitigation: retries/failure path in TaskQueue with explicit fail handling.

## Progress

- [x] Plan documented.
- [x] AXE dispatch path updated to SkillRun + TaskLease flow.
- [x] TaskQueue -> SkillRun finalization hook implemented.
- [x] Local OpenClaw compose service added.
- [x] Tests added and executed.
- [x] Guard added: direct `axe_worker_runs` openclaw dispatch returns conflict.
- [x] API contract guard added: `AXEWorkerRunCreateRequest` rejects `worker_type=openclaw`.
