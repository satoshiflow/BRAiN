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

## Next Phase

Planned next: **Phase P1 - Experience Layer MVP**

Focus:
1. add `backend/app/modules/experience_layer/` contracts and storage model.
2. implement idempotent `SkillRun -> ExperienceRecord` ingestion.
3. keep current APIs stable with adapter-first rollout.
