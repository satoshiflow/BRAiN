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

## Phase P4 - Deliberation Summary + Tension Artifacts

Completed: 2026-03-09

Delivered:
- added new `deliberation_layer` module:
  - `backend/app/modules/deliberation_layer/models.py`
  - `backend/app/modules/deliberation_layer/schemas.py`
  - `backend/app/modules/deliberation_layer/service.py`
  - `backend/app/modules/deliberation_layer/router.py`
- added deliberation API surfaces:
  - `POST /api/deliberation/missions/{mission_id}/summaries`
  - `GET /api/deliberation/missions/{mission_id}/summaries/latest`
  - `POST /api/deliberation/missions/{mission_id}/tensions`
  - `GET /api/deliberation/missions/{mission_id}/tensions`
- enforced tenant-bound access (`403` without tenant context) and lifecycle write guards (`409`) on mutating endpoints.
- enforced bounded non-chain-of-thought payload policy:
  - top-level `extra` fields forbidden,
  - `evidence` map limited in size and key length,
  - only scalar evidence values allowed,
  - forbidden reasoning keys rejected recursively.
- added migration `backend/alembic/versions/029_add_deliberation_layer.py` for deliberation persistence and lifecycle seed.
- wired deliberation router into backend app composition in `backend/main.py`.
- added tests in `backend/tests/test_deliberation_layer.py`.

Verification:
- `PYTHONPATH=. pytest tests/test_deliberation_layer.py tests/test_module_lifecycle.py tests/test_consolidation_layer.py tests/test_evolution_control.py tests/test_evolution_control_service.py -q`
- reviewer pass (Claude-style): PASS for bounded non-CoT policy, tenant isolation, and lifecycle guard coverage.

## Phase P5 - Stabilization, Decommission, and Operational Cadence

Completed: 2026-03-09

Delivered:
- strengthened lifecycle retirement safety in `module_lifecycle` service:
  - `deprecated/retired` transitions require `replacement_target` and `sunset_phase`
  - `retired` transitions require `kill_switch` to be present.
- added decommission ledger contract and API:
  - `GET /api/module-lifecycle/decommission/ledger` (admin/system-admin only)
  - readiness + blockers projection per deprecated/retired module.
- added ledger schemas and service projection:
  - `ModuleDecommissionLedgerEntry`
  - `ModuleDecommissionLedgerResponse`
  - `list_decommission_ledger(...)`
- added regression tests for ledger endpoint and retirement safety in `backend/tests/test_module_lifecycle.py`.

Verification:
- `PYTHONPATH=. pytest tests/test_deliberation_layer.py tests/test_module_lifecycle.py tests/test_consolidation_layer.py tests/test_evolution_control.py tests/test_evolution_control_service.py -q`
- `./scripts/run_rc_staging_gate.sh`
- reviewer pass (Claude-style): PASS for decommission ledger safety and lifecycle retirement constraints.

## Phase P6 - Discovery Layer MVP (Proposal-Only)

Completed: 2026-03-09

Delivered:
- finalized discovery contracts with explicit evidence/threshold response shape:
  - `backend/app/modules/discovery_layer/schemas.py`
- extended discovery persistence for deterministic dedup + prioritization:
  - migration `backend/alembic/versions/031_finalize_discovery_contracts.py`
  - `dedup_key`, `evidence_score`, `priority_score`
- extended discovery service to consume and threshold-check multi-source inputs:
  - consolidation pattern confidence/support
  - observer signal counts
  - knowledge evidence counts
- added proposal list surface for review workflows:
  - `GET /api/discovery/proposals`
- preserved proposal-only behavior and mediated handoff:
  - review queue still routes through `evolution_control`
- updated tests:
  - `backend/tests/test_discovery_layer.py`
  - `backend/tests/test_discovery_layer_service.py`

Verification:
- `PYTHONPATH=. pytest tests/test_discovery_layer.py tests/test_discovery_layer_service.py tests/test_evolution_control.py tests/test_evolution_control_service.py -q`
- lifecycle + auth/tenant behavior covered by route/service regression tests.

## Phase P7 - Economy and Selection Support (Deferred -> MVP Baseline)

Completed: 2026-03-09

Delivered:
- added new `economy_layer` module:
  - `backend/app/modules/economy_layer/models.py`
  - `backend/app/modules/economy_layer/schemas.py`
  - `backend/app/modules/economy_layer/service.py`
  - `backend/app/modules/economy_layer/router.py`
- added economy API surfaces:
  - `POST /api/economy/proposals/{proposal_id}/analyze`
  - `GET /api/economy/assessments/{assessment_id}`
  - `POST /api/economy/assessments/{assessment_id}/queue-review`
- implemented minimal economy dimensions (`confidence`, `frequency`, `impact`, `cost`) and weighted score for prioritization.
- integrated economy signals into discovery proposal prioritization metadata and evolution review ranking support.
- added migration `backend/alembic/versions/032_add_economy_layer.py` for persistence and lifecycle seed.
- wired economy router into backend app composition in `backend/main.py`.
- added/updated tests:
  - `backend/tests/test_economy_layer.py`
  - `backend/tests/test_economy_layer_service.py`
  - `backend/tests/test_evolution_control.py`
  - `backend/tests/test_evolution_control_service.py`
- updated RC gate suite in `scripts/run_rc_staging_gate.sh` to include discovery/evolution/economy checks.

Verification:
- `PYTHONPATH=. pytest tests/test_economy_layer.py tests/test_economy_layer_service.py tests/test_discovery_layer.py tests/test_discovery_layer_service.py tests/test_evolution_control.py tests/test_evolution_control_service.py -q`
- `./scripts/run_rc_staging_gate.sh`

## Hardening Sprints (Post-P7)

### Sprint A - Backend Grounding Audit

Completed: 2026-03-10

Delivered:
- comprehensive backend system mapping:
  - `docs/architecture/backend_system_map.md` (83 modules, 486 async methods, 290+ endpoints)
  - `docs/architecture/failure_surface_inventory.md` (failure classifications across 7 categories)
  - `docs/architecture/silent_fail_risks.md` (23 critical silent-fail patterns documented)
- identified critical gaps:
  - health system fragmentation (3 conflicting endpoint families)
  - false-green health patterns in legacy routes
  - runtime auditor not wired to startup
  - 84% of modules lacking complete audit/event coverage

Verification:
- audit artifacts reviewed for completeness
- documented findings inform Sprint B-E execution

### Sprint B - Health System Hardening

Completed: 2026-03-10

Delivered:
- fixed legacy `/api/health` false-green pattern (backend/app/api/routes/health.py:54)
- implemented real health checks for DB, Redis, HTTP dependencies
- wired `runtime_auditor` into startup with immune_orchestrator integration (backend/main.py)
- fixed `system_health` fallback-to-ok patterns
- created canonical health model spec (`docs/specs/canonical_health_model.md`)
- added comprehensive health system test suite (`backend/tests/test_health_system.py`, 23 tests)
- updated RC gate to include health suite (`scripts/run_rc_staging_gate.sh`)

Verification:
- `PYTHONPATH=. pytest tests/test_health_system.py -q`
- `./scripts/run_rc_staging_gate.sh` (health gate passing)

### Sprint C - Runtime Diagnostics & Error Framework

Completed: 2026-03-10

Delivered:
- created comprehensive diagnostics framework:
  - `backend/app/core/diagnostics.py` (421 lines, FailureRecord class, 6 failure taxonomies)
  - correlation ID propagation utilities
  - provenance linking for failure chains
- implemented failure taxonomy spec (`docs/specs/failure_taxonomy.md`, 394 lines)
- added incident timeline API to observer_core:
  - `GET /api/observer/timeline` (correlation-based incident reconstruction)
  - service logic with timeline assembly (backend/app/modules/observer_core/service.py)
- added comprehensive diagnostics test suite (`backend/tests/test_diagnostics.py`, 44 tests)
- updated RC gate to include diagnostics suite

Verification:
- `PYTHONPATH=. pytest tests/test_diagnostics.py -q`
- `./scripts/run_rc_staging_gate.sh` (diagnostics gate passing)

### Sprint D - Immune System Hardening

Completed: 2026-03-10

Delivered:
- created immune control plane architecture spec (`docs/specs/immune_control_plane.md`)
- documented adapter coverage matrix (`docs/architecture/immune_adapter_coverage.md`):
  - 30% immediate coverage (health_monitor, runtime_auditor, observer_core)
  - 97.5% planned coverage across all 83 modules
- added comprehensive immune system test suite (`backend/tests/test_immune_system.py`, 32 tests):
  - core decision logic tests (6 tests)
  - governance routing tests (6 tests)
  - audit chain completeness tests (4 tests)
  - event stream integration tests (3 tests)
  - adapter coverage pattern tests (4 tests)
  - end-to-end healing flow test
- updated RC gate to include immune suite

Verification:
- `PYTHONPATH=. pytest tests/test_immune_system.py -q` (32 tests passing)
- `./scripts/run_rc_staging_gate.sh` (immune gate passing)

### Sprint E - Self-Healing Foundation (MVP Stub)

Completed: 2026-03-10

Delivered:
- created self-healing control loop spec (`docs/specs/self_healing_control_loop.md`):
  - OODA loop architecture (Observe → Orient → Decide → Act → Verify)
  - 5 healing action types defined (RestartService, ClearCache, ResetCircuitBreaker, FlushQueue, NoOp)
  - safety rails specification (cooldown, blast radius, concurrent action limits)
  - verification & effectiveness scoring model
- implemented MVP foundation stubs:
  - `backend/app/modules/self_healing/schemas.py` (HealingAction classes, ExecutionContext, ActionResult, VerificationResult)
  - `backend/app/modules/self_healing/executor.py` (SelfHealingExecutor stub with logging)
- established integration points with immune_orchestrator and recovery_policy_engine

Note: Sprint E delivers **specification + foundation stubs** for future implementation. Full healing action execution planned for post-hardening sprint.

Verification:
- spec artifacts reviewed for architectural completeness
- schemas validate and import cleanly

## Next Phase

Planned next: **Post-P7 Operations and Evolution Cadence**

Execution spec:
- `docs/roadmap/BRAIN_POST_P7_OPERATIONS_CADENCE.md`
- `docs/roadmap/BRAIN_HARDENING_ROADMAP.md` (Sprints A-E completed)

Focus:
1. operate monthly contract/roadmap review cadence with governance evidence bundles.
2. harden anti-gaming, explainability, and rollback thresholds for economy scoring.
3. track production quality gates (tenant isolation, audit ordering, RC gate drift) as steady-state SLOs.
4. expand self-healing action implementation based on Sprint E foundation.
