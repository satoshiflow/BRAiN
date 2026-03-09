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

## Phase P2 - Insight Layer Baseline + Knowledge Input Normalization

Completed: 2026-03-09

Delivered:
- added new `insight_layer` module:
  - `backend/app/modules/insight_layer/models.py`
  - `backend/app/modules/insight_layer/schemas.py`
  - `backend/app/modules/insight_layer/service.py`
  - `backend/app/modules/insight_layer/router.py`
- added insight API surfaces:
  - `POST /api/insights/skill-runs/{skill_run_id}/derive`
  - `GET /api/insights/{insight_id}`
  - `GET /api/insights/skill-runs/{skill_run_id}`
- normalized knowledge ingest path to experience mediation:
  - `knowledge_layer.ingest_run_lesson` now uses `experience_layer.ingest_skill_run`
  - removed direct raw skill-run reads from knowledge ingest service path.
- kept existing knowledge ingest API path stable (`POST /api/knowledge-items/run-lessons/{skill_run_id}`).
- added deprecation metadata on the legacy-style knowledge ingest path:
  - `Deprecation: true`
  - `Sunset` header
  - `Link` header to experience ingest successor path
- tightened tenant isolation on knowledge reads/search and write paths (`403` without tenant context).
- wired insight router into backend app composition in `backend/main.py`.
- added migration `backend/alembic/versions/027_add_insight_layer.py` for table creation and lifecycle seeding.
- added tests:
  - `backend/tests/test_insight_layer.py`
  - `backend/tests/test_knowledge_layer_service.py`
  - updated `backend/tests/test_knowledge_layer.py` for deprecation header and tenant requirements.

Verification:
- `PYTHONPATH=. pytest tests/test_insight_layer.py tests/test_knowledge_layer.py tests/test_knowledge_layer_service.py tests/test_experience_layer.py tests/test_observer_core.py -q`
- `PYTHONPATH=. pytest tests/test_module_lifecycle.py -q`
- reviewer pass (Claude-style): PASS for tenant isolation, lifecycle guards, API compatibility, and knowledge ingest normalization.

## Next Phase

## Phase P3 - Consolidation Layer + Evolution Control Bootstrap

Completed: 2026-03-09

Delivered:
- added new `consolidation_layer` module:
  - `backend/app/modules/consolidation_layer/models.py`
  - `backend/app/modules/consolidation_layer/schemas.py`
  - `backend/app/modules/consolidation_layer/service.py`
  - `backend/app/modules/consolidation_layer/router.py`
- added pattern API surfaces:
  - `POST /api/consolidation/skill-runs/{skill_run_id}/derive`
  - `GET /api/consolidation/{pattern_id}`
  - `GET /api/consolidation/skill-runs/{skill_run_id}`
- added new `evolution_control` module:
  - `backend/app/modules/evolution_control/models.py`
  - `backend/app/modules/evolution_control/schemas.py`
  - `backend/app/modules/evolution_control/service.py`
  - `backend/app/modules/evolution_control/router.py`
- added evolution API surfaces:
  - `POST /api/evolution/proposals/patterns/{pattern_id}`
  - `GET /api/evolution/proposals/{proposal_id}`
  - `POST /api/evolution/proposals/{proposal_id}/transition`
- enforced lifecycle write guards for consolidation/evolution mutating endpoints.
- enforced tenant-bound access (`403` without tenant context).
- added governance-safe apply gate in proposal transitions:
  - `approved -> applied` requires governance evidence (`approval_id`, `policy_decision_id`, `reviewer_id`)
  - `validation_state` must be `validated`
  - durable transition trail is recorded in proposal metadata.
- added migration `backend/alembic/versions/028_add_consolidation_and_evolution_control.py` for persistence and lifecycle seeds.
- wired routers into backend app composition in `backend/main.py`.
- added tests:
  - `backend/tests/test_consolidation_layer.py`
  - `backend/tests/test_evolution_control.py`
  - `backend/tests/test_evolution_control_service.py`

Verification:
- `PYTHONPATH=. pytest tests/test_consolidation_layer.py tests/test_evolution_control.py tests/test_evolution_control_service.py tests/test_insight_layer.py tests/test_knowledge_layer.py tests/test_module_lifecycle.py -q`
- reviewer pass (Claude-style): PASS for tenant isolation, lifecycle guards, governance-safe proposal lifecycle, and no direct skill/policy mutation.

## Next Phase

Planned next: **Phase P4 - Deliberation Summary + Tension Artifacts**

Focus:
1. add bounded mission deliberation artifacts (`DeliberationSummary`, `MissionHypothesis`, `MissionPerspective`, `MissionTension`).
2. keep deliberation data minimal and explicitly non-chain-of-thought.
3. keep execution ownership unchanged (`SkillRun` remains canonical execution anchor).
