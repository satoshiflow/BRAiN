# BRAiN Layered Roadmap - Implementation Progress

Status: Active
Canonical roadmap: `docs/roadmap/BRAIN_SKILL_FIRST_IMPLEMENTATION_ROADMAP.md`

## Phase P0.1 - Legacy Write Guard Closure

Completed: 2026-03-09

Delivered:
- extended lifecycle guard coverage on builder write endpoints:
  - `POST /api/course-factory/enhance`
  - `POST /api/course-factory/webgenesis/bind-theme`
  - `POST /api/course-factory/webgenesis/build-sections`
  - `POST /api/course-factory/webgenesis/generate-seo`
  - `POST /api/webgenesis/spec`
- ensured lifecycle `HTTPException(409)` is preserved (not wrapped as `500`) in guarded endpoints.
- expanded lifecycle regression tests for mission template writes and builder write paths.

Verification:
- `PYTHONPATH=. pytest tests/test_legacy_missions_lifecycle_guards.py tests/test_builder_ops_lifecycle_guards.py -q`
- `PYTHONPATH=. pytest tests/test_course_factory.py tests/test_webgenesis_mvp.py -q`

## Phase P0.2 - Low-Risk Shim Reduction and Import Stability

Completed: 2026-03-09

Delivered:
- reduced eager import side effects in module package exports by introducing lazy attribute loading:
  - `backend/app/modules/course_factory/__init__.py`
  - `backend/app/modules/webgenesis/__init__.py`
- preserved existing exported symbols while deferring heavy imports until first use.
- added explicit compatibility tests for lazy export access.

Verification:
- `PYTHONPATH=. pytest tests/test_module_init_lazy_exports.py tests/test_builder_ops_lifecycle_guards.py tests/test_course_factory.py tests/test_webgenesis_mvp.py -q`
- backend collection check:
  - `PYTHONPATH=. pytest tests/test_module_init_lazy_exports.py --collect-only -q`
- repo-root collection check:
  - `PYTHONPATH=backend pytest backend/tests/test_module_init_lazy_exports.py --collect-only -q`

## Phase P1 - Experience Layer MVP

Completed: 2026-03-09

Delivered:
- added new `experience_layer` module:
  - `backend/app/modules/experience_layer/models.py`
  - `backend/app/modules/experience_layer/schemas.py`
  - `backend/app/modules/experience_layer/service.py`
  - `backend/app/modules/experience_layer/router.py`
- added API surfaces:
  - `POST /api/experience/skill-runs/{skill_run_id}/ingest`
  - `GET /api/experience/{experience_id}`
  - `GET /api/experience/skill-runs/{skill_run_id}`
- enforced lifecycle write guard (`409`) for experience ingestion.
- enforced tenant-bound access (`403` when tenant context is missing).
- implemented idempotent ingest with race-safe integrity fallback behavior.
- wired router into backend app composition in `backend/main.py`.
- added migration `backend/alembic/versions/025_add_experience_layer.py` for table creation and lifecycle seeding.
- added router regression tests in `backend/tests/test_experience_layer.py`.

Verification:
- `PYTHONPATH=. pytest tests/test_experience_layer.py tests/test_knowledge_layer.py tests/test_module_lifecycle.py -q`
- reviewer pass (Claude-style): PASS for tenant isolation, ingest race safety, and migration presence.

## Next Phase

## Phase P1B - Observer Core MVP (Read-Only)

Completed: 2026-03-09

Delivered:
- added new `observer_core` module:
  - `backend/app/modules/observer_core/models.py`
  - `backend/app/modules/observer_core/schemas.py`
  - `backend/app/modules/observer_core/service.py`
  - `backend/app/modules/observer_core/router.py`
- added read-only API surfaces:
  - `GET /api/observer/signals`
  - `GET /api/observer/signals/{signal_id}`
  - `GET /api/observer/state`
  - `GET /api/observer/state/entities/{entity_type}/{entity_id}`
  - `GET /api/observer/summary`
- enforced tenant-bound access (`403` when tenant context is missing).
- verified no mutating observer endpoint methods are exposed.
- wired observer router into backend app composition in `backend/main.py`.
- added migration `backend/alembic/versions/026_add_observer_core.py` for observer tables and lifecycle registration.
- added router regression tests in `backend/tests/test_observer_core.py`.

Verification:
- `PYTHONPATH=. pytest tests/test_observer_core.py tests/test_experience_layer.py tests/test_module_lifecycle.py -q`
- reviewer pass (Claude-style): PASS for read-only surface, tenant isolation, and no mutation coupling.

## Next Phase

Planned next: **Phase P2 - Insight Layer Baseline + Knowledge Input Normalization**

Focus:
1. introduce `insight_layer` artifacts (`InsightCandidate`) derived from `ExperienceRecord`.
2. preserve API compatibility while normalizing `knowledge_layer` ingest path away from raw `SkillRun` bypass.
3. add deprecation signaling for direct bypass paths with adapter-first rollout.
