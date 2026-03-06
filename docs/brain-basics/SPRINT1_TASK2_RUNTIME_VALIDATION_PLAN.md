# Sprint 1 - Task 2: Auth Runtime Validation Plan

Date: 2026-03-04
Owner: OpenCode
Status: Completed

## Goal

Validate auth convergence behavior under current repository constraints,
while full pytest regression remains partially blocked by baseline model debt.

## Constraints

- Full auth tests currently blocked by SQLAlchemy model issue in `backend/app/models/token.py` (`metadata` reserved attribute name).
- Local environment does not fully mirror production stack.

## Validation Strategy (Layered)

### Layer A - Static safety checks (completed)

- Legacy auth imports removed from `backend/app/modules/**`.
- P0 route `backend/app/api/routes/auth.py` switched to modern validator flow.
- Syntax checks on touched files passed.

### Layer B - Deterministic code contract checks (next)

1. Dependency contract scan:
   - ensure routers use `auth_deps` dependencies only.
2. Role dependency matrix check:
   - verify mutating endpoints require role dependencies.
3. Error handling sanity for auth route:
   - ensure invalid token path returns 401 consistently.

### Layer C - Targeted runtime checks (after baseline blocker fix)

1. `test_auth_flow.py`
2. `test_module_auth.py`
3. Minimal route-level auth smoke tests for migrated modules.

## Immediate next actions

1. Create a micro-checklist for migrated modules (auth dependency + role gate + principal source).
2. Add a temporary CI-style grep gate for legacy auth imports.
3. Isolate and schedule fix for `token.py` model blocker as prerequisite for full regression.

## Progress Updates

### Update 1 - Resilient execution routine implemented

Added resilient pipeline runner and executed it with an example plan.

New files:

- `scripts/resilient_pipeline_runner.py`
- `scripts/pipeline_plan.example.json`
- `docs/brain-basics/SELF_HEALING_AND_DIAGNOSTICS_STATUS.md`

Validation run:

- Command:
  - `python3 scripts/resilient_pipeline_runner.py --plan scripts/pipeline_plan.example.json --always-zero`
- Report generated:
  - `reports/self_healing/20260304T142916Z/diagnosis_report.json`

Observed diagnosis:

- Pipeline continued after failing auth test step.
- Root cause tagged automatically as `sqlalchemy_model_error` with concrete recommendation.

### Update 2 - Step 2/3 execution completed

Work completed:

- Fixed SQLAlchemy declarative blocker in token model:
  - `backend/app/models/token.py`
  - changed Python attribute `metadata` -> `meta_json` while preserving DB column name (`Column("metadata", ...)`).

- Re-ran targeted auth checks:
  - `PYTHONPATH=. pytest tests/test_auth_flow.py tests/test_module_auth.py -q`
  - test collection now proceeds (import blocker removed).

- Re-ran resilient pipeline twice and generated new reports:
  - `reports/self_healing/20260305T111844Z/diagnosis_report.json`
  - `reports/self_healing/20260305T112017Z/diagnosis_report.json`

- Improved diagnosis quality in runner:
  - `scripts/resilient_pipeline_runner.py`
  - added explicit failure tags for auth-flow and module-auth classes.

Current verification state:

- Legacy auth import gate: PASS
- Compile step: PASS
- Auth tests: PASS (33 passed)

Conclusion:

- Step 2 (blocker removal) and Step 3 (resilient verification loop) are complete.
- Targeted auth stabilization completed via:
  - RS256 signing compatibility fix in `app/services/auth_service.py` (PEM key bytes for python-jose)
  - module auth test harness alignment in `tests/test_module_auth.py`

### Update 3 - Final success verification

- Command:
  - `PYTHONPATH=. pytest tests/test_auth_flow.py tests/test_module_auth.py -q`
- Result:
  - `33 passed`
- Resilient runner:
  - `python3 scripts/resilient_pipeline_runner.py --plan scripts/pipeline_plan.example.json --always-zero`
  - report: `reports/self_healing/20260305T125033Z/diagnosis_report.json`
  - overall status: `success`
