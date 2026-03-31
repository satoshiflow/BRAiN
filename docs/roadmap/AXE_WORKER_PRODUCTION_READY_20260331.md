# AXE Worker Surface Production Ready (2026-03-31)

Status: complete (local-verified), pending remote push

## Scope

This delivery finalizes AXE worker operations for:
- `miniworker`
- `opencode`
- `openclaw`

across UX, runtime consistency, and governance hardening.

## What is now production-ready

### 1) Unified worker activity surface

- Worker cards use explicit activity source tagging:
  - `worker_run`
  - `skillrun_tasklease`
- `openclaw` is visible in the same AXE surface without collapsing runtime boundaries.

### 2) OpenClaw live runtime status

- OpenClaw entries now refresh against Task Queue runtime source (`/api/tasks/{task_id}`).
- Task statuses are mapped to AXE worker statuses for consistent operator display.

### 3) Full approval lifecycle for bounded apply

- waiting state (`waiting_input`) with approval panel
- approve/reject API continuation
- history persisted with actor/time/reason
- routing/purpose references captured in approval history

### 4) Governance hardening

- role-based gate for bounded apply approvals (`operator/admin/service`)
- canonicalized path policy enforcement (prevents path normalization bypasses)
- blocked sensitive path/file classes fail closed
- task visibility checks on task read endpoint (tenant-aware, avoids cross-tenant leakage)

### 5) UX completion

- persistent filters per session (worker type + status)
- openclaw included in worker type filters
- stronger visual emphasis for `waiting_input` and `failed`
- empty filtered-state hint in chat
- runtime source block with `task_id` and `skill_run_id`
- duplicate submit protection in approval panel

## Main changed surfaces

Backend:
- `backend/app/modules/axe_worker_runs/service.py`
- `backend/app/modules/axe_worker_runs/router.py`
- `backend/app/modules/axe_worker_runs/schemas.py`
- `backend/app/modules/axe_miniworker/service.py`
- `backend/app/modules/task_queue/router.py`

Frontend:
- `frontend/axe_ui/app/chat/page.tsx`
- `frontend/axe_ui/components/chat/WorkerRunCard.tsx`
- `frontend/axe_ui/components/chat/WorkerApprovalPanel.tsx`
- `frontend/axe_ui/lib/api.ts`
- `frontend/axe_ui/lib/contracts.ts`

Tests:
- `backend/tests/test_axe_worker_runs_service.py`
- `backend/tests/test_axe_worker_runs_routes.py`
- `backend/tests/test_axe_miniworker_service.py`
- `frontend/axe_ui/app/chat/__tests__/upload-flow.test.tsx`
- `frontend/axe_ui/components/chat/__tests__/WorkerRunCard.test.tsx`

## Verification

Targeted backend tests:
- `PYTHONPATH=. pytest tests/test_axe_worker_runs_service.py tests/test_axe_worker_runs_routes.py tests/test_axe_miniworker_service.py -q`

Frontend tests/build:
- `npm run test -- --runInBand app/chat/__tests__/upload-flow.test.tsx components/chat/__tests__/WorkerRunCard.test.tsx`
- `npm run lint`
- `npm run build`

Full local gate:
- `./scripts/local_ci_gate.sh all`

Evidence files:
- `docs/roadmap/local_ci/20260331_211705_all.md`
- `docs/roadmap/local_ci/20260331_224616_all.md`
- `docs/roadmap/local_ci/20260331_230929_all.md`

## Commit chain (local)

- `5f20ec7` feat(axe): productionize unified worker activity surface
- `48cce1e` feat(axe): harden bounded-apply governance and approval UX
- `4a6cddc` fix(axe): enforce bounded-apply and task visibility guards

## Release state

- Local branch status before push: `main...origin/main [ahead 3+]`
- Code and tests are production-ready from local gate perspective.
