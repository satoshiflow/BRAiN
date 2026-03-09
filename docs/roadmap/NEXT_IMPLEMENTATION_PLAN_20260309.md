# Next Implementation Plan (Post A/B Stabilization)

Version: 1.0  
Date: 2026-03-09  
Status: Active execution plan

---

## 1 Goal

Complete the remaining open B-depth guardrail work first, then move into the minimal Knowledge/Evolution runtime bridge.

Priority order:

1. open B-depth slice (lifecycle/decommission guardrails on legacy edges)
2. residual low-risk shim reduction
3. `experience_layer` as first-class bridge object

---

## 2 Scope

### B-depth (must finish first)

- add/complete lifecycle write guards on legacy and partially guarded write paths:
  - `backend/api/routes/missions.py`
  - `backend/app/modules/missions/router.py`
  - remaining mutating webgenesis lifecycle/ops routes
  - remaining mutating course-factory workflow routes
- extend tests proving `409` behavior under `deprecated`/`retired` module states.

### Residual shim reduction (low risk only)

- continue reducing package/import side effects without broad import refactor.
- keep stop-go safety: if collection/import instability appears, stop and keep compatibility shim.

### Knowledge/Evolution bridge (minimal)

- introduce `experience_layer` only:
  - durable `ExperienceRecord`
  - ingest endpoint from `SkillRun`
  - idempotent write behavior
  - lifecycle guard + tenant-safe retrieval

No `insight_layer`, `pattern_layer`, or auto-evolution mutation in this slice.

---

## 3 Execution Phases

### Phase P1 - B-depth legacy guardrail closure

Deliverables:

- lifecycle guard helpers integrated on open write endpoints
- tests for blocking semantics
- no regression in builder/runtime slices

Stop-go criteria:

- pass targeted tests for touched modules
- pass widened regression slice
- pass RC gate

### Phase P2 - Residual shim reduction

Deliverables:

- eliminate only low-risk package/test side effects
- keep behavior stable for both repo-root and `backend/` test entry patterns

Stop-go criteria:

- import/collection stable
- no RC gate regression

### Phase P3 - Experience Layer MVP

Deliverables:

- module: `backend/app/modules/experience_layer/`
- migration for `experience_records`
- API:
  - `POST /api/experience/skill-runs/{run_id}/ingest`
  - `GET /api/experience/{experience_id}`
  - `GET /api/experience/skill-runs/{run_id}`
- lifecycle write guard
- tests for idempotency, tenant isolation, and run linkage

Stop-go criteria:

- no parallel runtime path introduced
- `SkillRun` remains sole execution truth
- widened regression + RC gate pass

---

## 4 Risks and Mitigations

### Risk R1 - Legacy mission/runtime coupling surprises

Mitigation:

- contain changes to router-level guardrails first
- avoid deep mission-runtime rewrites in this phase

### Risk R2 - Shim reduction breaks old import assumptions

Mitigation:

- low-risk cuts only
- keep compatibility wrappers until test migration is complete

### Risk R3 - Knowledge/Evolution scope creep

Mitigation:

- enforce single-object rule in this phase (`ExperienceRecord` only)
- defer insight/pattern/evolution objects to next phase

---

## 5 Verification Matrix

Targeted checks:

- module/lifecycle guard tests for touched routes
- builder/runtime slice:
  - `course_factory`
  - `webgenesis`
  - `skill_engine`
  - `agent/supervisor orchestration`
  - `task_queue lease`
  - `knowledge_layer` and run-ingest routes

Gate:

- `./scripts/run_rc_staging_gate.sh`

---

## 6 Definition of Done

- B-depth guardrail gaps closed for agreed legacy edges
- residual shim reduction advanced without destabilizing test/RC behavior
- `experience_layer` MVP implemented and verified
- roadmap/progress/spec docs aligned with actual verified state
