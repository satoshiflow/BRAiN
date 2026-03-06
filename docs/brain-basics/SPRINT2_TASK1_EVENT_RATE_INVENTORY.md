# Sprint 2 - Task 1: Event and Rate Limit Inventory

Date: 2026-03-05
Owner: OpenCode
Status: Completed (Compressed)

## Goal

Inventory runtime event backbones and rate limiter implementations to converge on one production-safe path each.

## Findings (initial)

### Event infrastructure

- Multiple patterns coexist:
  - `mission_control_core.core.event_stream.EventStream` in `backend/main.py` and many modules.
  - Legacy/local `app.core.event_bus.EventBus` still used by some modules (example: `modules/paycore/service.py`).
- Convergence target remains:
  - runtime-critical paths should standardize on `EventStream`.

### Rate limiting

- Global limiter configured in `backend/main.py` with Redis-backed options.
- Separate local limiter instance in `backend/app/core/rate_limit.py` and independent limiter in autonomous pipeline.
- Modules import `app.core.rate_limit.limiter`, but startup also creates `app.state.limiter`.

## Immediate next actions

1. Build exact usage map for `EventBus` references and classify by migration effort.
2. Build exact usage map for limiter instances and storage backing.
3. Propose minimal convergence plan (non-breaking, staged).

## Compressed delivery completed

Implemented minimal, high-impact rate-limit convergence:

- `backend/main.py`
  - removed duplicate local `Limiter(...)` instantiation
  - now uses single shared limiter from `app.core.rate_limit`
  - uses shared custom rate-limit exceeded handler

- `backend/app/core/rate_limit.py`
  - single limiter now supports Redis storage via env (`REDIS_URL`/`BRAIN_REDIS_URL`)
  - fallback remains in-memory for local/dev

Validation:

- `python3 -m py_compile backend/main.py backend/app/core/rate_limit.py` -> PASS
- `PYTHONPATH=. pytest tests/test_auth_flow.py tests/test_module_auth.py -q` -> PASS (`33 passed`)

## Sprint 3 handoff

Sprint 3 starts immediately with EventStream-only convergence for runtime-critical modules.
Primary first target for migration: `app/modules/paycore/service.py` still using legacy `app.core.event_bus.EventBus`.
