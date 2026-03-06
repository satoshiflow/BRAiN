# BRAiN Project Analysis and Roadmap

Date: 2026-03-03
Owner: OpenCode (Project Lead)
Scope: Deep codebase analysis with core-first priority and Claude analysis cross-check.

## Executive View

BRAiN already has strong modular depth and many hardened modules, but the platform is in a convergence stage: critical infrastructure is partially duplicated (auth, rate limit, events), frontend auth paths are inconsistent, and execution orchestration is incomplete for a fully autonomous multi-agent runtime.

## What BRAiN already does well

- Core modularity is real: 60+ backend modules with clear domain segmentation in `backend/app/modules/`.
- Security posture improved significantly versus older docs: broad RBAC usage via `app.core.auth_deps` in most routers.
- AXE is operational as primary human gateway: `axe_fusion`, `axe_identity`, `axe_knowledge`, `axe_widget` are present and integrated in `backend/main.py`.
- Mission/Planning/Learning/Memory foundations exist and are non-trivial.
- Deployment architecture is compatible with your target model (Coolify + separate containers/services).

## Critical architecture findings (core-first)

### 1) Auth split-brain (must converge)

- Modern path exists and is stronger:
  - `backend/app/core/jwt_middleware.py`
  - `backend/app/core/auth_deps.py`
- Legacy path still active in parts of code:
  - `backend/app/core/security.py`
  - routers importing `from app.core.security import ...`

Decision:
- Keep modern JWT/RBAC path (`auth_deps` + `jwt_middleware`).
- Mark legacy `security.py` auth dependencies for elimination.

Reason:
- Modern path supports structured token payloads, scopes, roles, issuer/audience checks, JWKS.
- Legacy path uses local HS256 + in-memory users and anonymous fallback behavior unsuitable for unified production policy.

### 2) Event infrastructure mismatch

- `backend/app/core/event_bus.py` is a stub (non-durable, in-memory subscribers).
- Main app also uses `EventStream` (`mission_control_core`) in lifespan.

Decision:
- Standardize on `EventStream` as authoritative event backbone.
- Decommission stub event bus usage from core runtime paths.

### 3) Rate limiting inconsistency

- `backend/main.py` configures limiter with Redis storage.
- `backend/app/core/rate_limit.py` defines a separate limiter with default in-memory behavior.

Decision:
- Single policy + single limiter integration path (Redis-backed) for all critical routes.

### 4) Frontend auth inconsistency (controldeck-v2)

- Better Auth exists in `frontend/controldeck-v2/src/lib/auth.ts`.
- Deprecated/compat and stale routes exist, including endpoints referencing non-existing helpers (example: login route imports `login` from `auth-server` which does not export `login`).
- API base URL usage is mixed and can drift between public/internal routing.

Decision:
- Make `controldeck-v2` auth single-path and remove compatibility leftovers.

### 5) Connectors are strong conceptually, but policy depth still needed

- Good abstraction in `BaseConnector` and service/router structure.
- Still needs stricter role gating and sanitized operational behavior for lifecycle actions.

## AXE and frontend position

- AXE remains the only direct human/superadmin interface by design.
- `axe_ui` currently behaves as focused AXE interface.
- `controldeck-v2` should become the primary operations deck once auth/API path is cleaned.
- `brain_ui` remains out of current execution scope.

## Claude analysis cross-check

- Older `CLAUDE.md` status sections are partially outdated.
- Many previously flagged auth/security gaps are already improved in current code.
- Remaining high-impact items align with this roadmap: auth convergence, event backbone, rate-limit unification, and frontend auth consistency.

## Phased Roadmap (core-first, small tasks)

### Phase 0 - Baseline and guardrails (Sprint 0)

Goal: prevent new drift while refactoring.

- Freeze introduction of new legacy auth imports.
- Add temporary lint/check rule: block `from app.core.security import get_current_principal/require_role` in new code.
- Capture current integration map in docs.

### Phase 1 - Security and identity convergence (Sprints 1-2)

Goal: one auth system end-to-end.

Sprint 1:
- Migrate core-near routers still using legacy imports to `auth_deps` primitives.
- Keep adapter shims only where absolutely needed.

Sprint 2:
- Mark legacy security auth functions as deprecated in code comments and docs.
- Remove stale frontend auth routes and broken compatibility handlers in `controldeck-v2`.
- Stabilize login/session/logout flow with one contract.

### Phase 2 - Event and rate-limit unification (Sprints 3-4)

Goal: reliable control-plane behavior.

Sprint 3:
- Replace runtime dependency on stub event bus with `EventStream` only.
- Introduce explicit event contract for mission/planning/skills/memory interactions.

Sprint 4:
- Consolidate to one limiter strategy and one storage backend policy.
- Apply explicit per-endpoint limits for high-cost routes.

### Phase 3 - Autonomous execution completeness (Sprints 5-7)

Goal: move from skeleton to autonomous runtime.

Sprint 5:
- Mission execution state machine integration (not only templates).

Sprint 6:
- Planning to execution bridge (DAG -> skill invocation pipeline).

Sprint 7:
- Memory and learning loop closure:
  - deterministic store/recall path for outcomes
  - strategy feedback into planning/execution.

### Phase 4 - Frontend operationalization (Sprints 8-9)

Goal: production operations UX with AXE-first principles.

Sprint 8:
- `controldeck-v2` module status parity with backend core modules.
- Unified API proxy/auth behavior.

Sprint 9:
- AXE UI + controldeck-v2 role mapping and clear responsibility boundaries.

### Phase 5 - Multi-agent optimization layer (Sprints 10-12)

Goal: your Option C (OpenCode managed multi-agent execution).

Sprint 10:
- Define specialist-agent profiles (frontend/backend/devops/security/reviewer/critic).

Sprint 11:
- Model-routing policy by cost/capability (including Minimax / BigPickle/Trinity / Claude Pro usage strategy).

Sprint 12:
- Critic-agent gate for all high-impact changes (required review before merge/deploy).

## Planned model policy (for later implementation)

- Security/Critical review: Claude (high quality, not for trivial UI tasks).
- Routine implementation and refactors: low-cost models first.
- Critic pass: separate reviewer model to reduce blind spots.
- Request-per-minute governor: routing and batching policy to reduce LLM RPM.

## Constraints acknowledged

- Local environment cannot fully reproduce production (Coolify + remote DB/LLM/services).
- Therefore: stronger static checks, contract tests, and critic-agent reviews are mandatory before deploy.

## Next immediate execution block

1. Auth convergence inventory (legacy import map -> migration list).
2. Controldeck-v2 auth route cleanup plan.
3. Event and rate-limit unification design note.
4. Build critic-agent checklist for PR gating.
