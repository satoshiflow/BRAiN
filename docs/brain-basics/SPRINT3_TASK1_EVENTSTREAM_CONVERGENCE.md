# Sprint 3 - Task 1: EventStream Convergence

Date: 2026-03-05
Owner: OpenCode
Status: In Progress (First migration slice complete)

## Goal

Replace runtime dependency on legacy/stub event bus paths with `EventStream`-aligned publishing in critical modules.

## Scope (compressed start)

1. Migrate first critical module path still using `app.core.event_bus.EventBus`.
2. Keep behavior non-breaking (best-effort event publishing, no hard failures on publish).
3. Capture event contract notes for mission/planning/skills/memory follow-up.

## First target

- `backend/app/modules/paycore/service.py`
  - currently imports and uses `EventBus` with local Redis fetch.

## Constraints

- No broad refactor in this block.
- Preserve operational behavior.
- Add clear fallback logging if event publish unavailable.

## Progress update

Completed first migration slice:

- `backend/app/modules/paycore/service.py`
  - removed runtime dependency on `app.core.event_bus.EventBus`
  - added shared `EventStream` injection (`set_event_stream` + app state wiring via dependency path)
  - kept non-blocking publish fallback behavior with explicit logs when stream unavailable

Regression guard:

- `PYTHONPATH=. pytest tests/test_auth_flow.py tests/test_module_auth.py -q` -> PASS (`33 passed`)

Next slice:

- identify next runtime-critical module still coupled to legacy event-bus path and migrate with same non-breaking pattern.

## Micro-step (guard rail)

- Added import guard to prevent reintroduction of legacy core EventBus in runtime app code:
  - `scripts/check_no_legacy_event_bus.py`
- Added guard execution to resilient pipeline plan:
  - `scripts/pipeline_plan.example.json`

Verification:

- `python3 scripts/check_no_legacy_event_bus.py` -> PASS
- `python3 scripts/resilient_pipeline_runner.py --plan scripts/pipeline_plan.example.json --always-zero` -> PASS

## Incremental hardening (2026-03-05 follow-up)

- `backend/app/modules/paycore/router.py`
  - fixed tenant ownership checks to use explicit tenant lookup methods instead of response-model fields.
- `backend/app/modules/paycore/service.py`
  - added `get_intent_tenant_id` and `get_refund_tenant_id` helper queries for secure ownership validation.

Regression check:

- `PYTHONPATH=. pytest tests/test_auth_flow.py tests/test_module_auth.py -q` -> PASS (`33 passed`)

## Additional micro-steps (2026-03-06)

- PayCore dependency hygiene:
  - fixed FastAPI dependency signature for service factory to avoid request-field parsing errors in dependency analysis.
  - file: `backend/app/modules/paycore/service.py`
- PayCore ownership regression tests:
  - added focused ownership guard tests covering tenant match/mismatch/default override and missing refund tenant.
  - file: `backend/tests/test_paycore_ownership.py`
- TD-02 continuation:
  - migrated remaining module-level Pydantic v1 validators to v2 `@field_validator` in:
    - `backend/app/modules/webgenesis/schemas.py`
    - `backend/app/modules/aro/schemas.py`

Verification:

- `PYTHONPATH=. pytest tests/test_paycore_ownership.py tests/test_auth_flow.py tests/test_module_auth.py -q` -> PASS (`38 passed`)

## Guard hardening (2026-03-06)

- strengthened legacy EventBus guard to AST-based import detection.
- now blocks direct and indirect import forms:
  - `import app.core.event_bus`
  - `from app.core.event_bus import ...`
  - `from app.core import event_bus`
- file: `scripts/check_no_legacy_event_bus.py`

Verification:

- `python3 scripts/check_no_legacy_event_bus.py` -> PASS
