# Sprint 1 - Task 1: Auth Convergence Inventory

Date: 2026-03-03
Owner: OpenCode
Status: In Progress

## Objective

Create a complete inventory of legacy auth usage and produce a migration-ready plan to converge on:

- `app.core.auth_deps`
- `app.core.jwt_middleware`

Legacy path targeted for elimination:

- `app.core.security` auth dependency usage

## Progress Updates

### Update 1 - Task started

- Created sprint task log.
- Next: scan backend for all `app.core.security` imports/usages and classify them.

### Update 2 - Inventory completed

Completed full inventory of legacy auth/security imports.

Raw hits found (`from app.core.security import ...`): 16.

High-priority migration targets:

1. Full legacy dependency usage in routers/services:
   - `backend/app/modules/credits/router.py`
   - `backend/app/modules/axe_identity/router.py`
   - `backend/app/modules/axe_knowledge/router.py`
   - `backend/app/modules/cluster_system/router.py`
   - `backend/app/modules/paycore/service.py` (legacy Principal typing)

2. Legacy token primitives still in auth route:
   - `backend/app/api/routes/auth.py` imports `create_access_token`, `SECRET_KEY`, `ALGORITHM` from legacy security module while route also uses newer RS256 token flows.

3. Mixed-mode usage (low effort cleanup):
   - modules importing `UserRole` from legacy file while already using modern `auth_deps` dependencies:
     - `task_queue/router.py`
     - `skills/router.py`
     - `memory/router.py`
     - `learning/router.py`
     - `config_management/router.py`
     - `axe_widget/router.py`
     - `audit_logging/router.py`
     - `agent_management/router.py`

4. Transitional compatibility (keep temporary):
   - `backend/app/core/auth_deps.py` imports `LegacyPrincipal` adapter. Keep until router migration is complete.

### Update 3 - Classification

- P0 (critical): `app/api/routes/auth.py` legacy HS256 decode dependency.
- P1 (high): routers with full legacy principal/dependency imports.
- P2 (medium): role enum import cleanup (`UserRole` only).
- P3 (controlled): compatibility shim cleanup in `auth_deps` (final step only).

### Next actions

1. Create `SystemRole`-based replacement in mixed-mode routers (P2 quick wins).
2. Migrate P1 routers to `auth_deps` Principal + role dependencies.
3. Refactor auth route token decode path to key-manager/JWKS validation only (P0).
4. Remove remaining legacy imports and run targeted tests.

### Update 4 - Block completed (P2 quick wins)

Completed P2 cleanup block: removed legacy `UserRole` imports from modules already using modern `auth_deps`.

Files updated:

- `backend/app/modules/task_queue/router.py`
- `backend/app/modules/skills/router.py`
- `backend/app/modules/memory/router.py`
- `backend/app/modules/learning/router.py`
- `backend/app/modules/config_management/router.py`
- `backend/app/modules/axe_widget/router.py`
- `backend/app/modules/audit_logging/router.py`
- `backend/app/modules/agent_management/router.py`

Approach:

- Replaced `from app.core.security import UserRole` with
  `from app.core.auth_deps import ... SystemRole as UserRole`
- Kept endpoint semantics unchanged while removing legacy dependency coupling.

Result:

- Zero remaining `from app.core.security import UserRole` in `backend/app/modules`.
- Ready for P1 block (full legacy dependency router migrations).

### Update 5 - Block completed (P1 module migration)

Completed P1 migration block for full legacy dependency usages inside `backend/app/modules`.

Files migrated from legacy security imports to modern auth deps:

- `backend/app/modules/credits/router.py`
- `backend/app/modules/axe_identity/router.py`
- `backend/app/modules/axe_knowledge/router.py`
- `backend/app/modules/cluster_system/router.py`
- `backend/app/modules/paycore/service.py`
- `backend/app/modules/knowledge_graph/router.py` (removed legacy fallback import path)

Verification result:

- `backend/app/modules/**` now has **zero** `from app.core.security import ...` imports.

Remaining legacy auth references in app layer:

1. `backend/app/api/routes/auth.py` (P0 critical - HS256 legacy token primitives)
2. `backend/app/core/auth_deps.py` (`LegacyPrincipal` compatibility shim, planned final cleanup)

Next block:

- P0 migration in `app/api/routes/auth.py` to remove `create_access_token`, `SECRET_KEY`, `ALGORITHM` dependency from legacy `security.py`.

### Update 6 - P0 migration started

Started P0 critical migration in:

- `backend/app/api/routes/auth.py`

Changes made:

- Removed legacy import of `create_access_token`, `SECRET_KEY`, `ALGORITHM` from `app.core.security`.
- Switched token verification in `get_current_user_db()` from legacy HS256 decode to modern validator path:
  - `get_jwt_validator(use_local_keys=True)`
  - `await validator.validate(token)`

Current state:

- In app layer, only one intentional legacy reference remains:
  - `backend/app/core/auth_deps.py` compatibility shim (`LegacyPrincipal`), planned for final cleanup phase.
- Targeted runtime tests still pending (interrupted before execution).

### Update 7 - Verification block completed

Verification actions executed:

1. Re-scan for legacy security imports in app layer.
2. Targeted auth tests attempted.
3. Syntax compilation check on all changed files.

Results:

- Legacy import scan result:
  - only remaining `from app.core.security import ...` is in
    `backend/app/core/auth_deps.py` (intentional compatibility shim).

- Targeted tests (`test_auth_flow.py`, `test_module_auth.py`) are currently blocked by pre-existing repository issues unrelated to this migration:
  - environment/config bootstrap mismatch when run from repo root,
  - model import error when run from `backend/` (`app.models.__init__` imports `Course` symbol not exported by `app.models.courses`).

- Syntax validation passed for all changed files via `python3 -m py_compile`.

Implication:

- Migration changes are syntactically valid.
- Functional test verification requires fixing baseline test bootstrap/import issues first.

### Next block

1. Add short note in risk register about current test harness blockers.
2. Move to Sprint 1 Task 2 prep (auth route/runtime validation plan under current constraints).

### Update 8 - Extended test unblock attempt

Additional work performed to improve test collectability:

- Hardened `backend/app/models/__init__.py` to avoid eager hard-fail imports from optional model groups.
- Added compatibility aliases for course models while keeping core user models eagerly available.

Test rerun result:

- Collection still blocked by a separate pre-existing SQLAlchemy model issue in token models:
  - `backend/app/models/token.py` defines attribute name `metadata` (reserved in SQLAlchemy Declarative API), raising `InvalidRequestError` during import.

Conclusion:

- Auth convergence code path changes are in place and syntax-valid.
- Full auth regression tests remain blocked by baseline model-definition debt unrelated to this specific auth migration.

### Update 9 - Pause checkpoint saved

- Session pause prepared before OpenCode update/reset.
- Handoff instructions written to:
  - `docs/brain-basics/OPENCODE_SESSION_HANDOFF.md`
- Sprint 1 remains active; do not start Sprint 2 until token model blocker is fixed and targeted auth tests rerun.

### Update 10 - Sprint 1 auth convergence verification passed

- Token model blocker fixed (`AgentCredential.metadata` -> `meta_json` with DB column compatibility).
- Legacy imports outside compatibility shim remain zero.
- Targeted auth verification now passes:
  - `PYTHONPATH=. pytest tests/test_auth_flow.py tests/test_module_auth.py -q`
  - Result: `33 passed`
- Resilient pipeline report is green:
  - `reports/self_healing/20260305T125033Z/diagnosis_report.json`
