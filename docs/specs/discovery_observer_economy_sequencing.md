# Discovery, Observer, and Economy Sequencing Note

Status: Active planning note
Date: 2026-03-09
Purpose: Capture sequencing and guardrails for introducing Observer Core,
Discovery Layer, and later Economy logic without destabilizing BRAiN Core.

## 1) Confirmed Direction

1. Preserve existing stable execution modules and governance boundaries.
2. Add cognition layers incrementally around the core.
3. Keep Observer read-only and asynchronous.
4. Keep Discovery proposal-only (no direct runtime mutation).
5. Introduce economy/credits only after the prior layers are stable.

## 2) Placement in Learning Stack

Canonical stack for this repo:

Execution -> Experience -> Insight -> Consolidation -> Knowledge -> Discovery -> Evolution Control -> Skill Evolution

Observer Core runs in parallel as a read-only side layer:

Observer Core -> monitors execution/state signals -> enriches Insight/Consolidation/Discovery inputs

## 3) Repo Integration Points

Primary signal sources for Observer MVP:

- `backend/app/modules/skill_engine/`
- `backend/app/modules/skill_evaluator/`
- `backend/app/modules/learning/`
- `backend/app/modules/task_queue/`
- `backend/app/modules/runtime_auditor/`
- `backend/app/modules/system_health/`
- `backend/app/modules/health_monitor/`
- `backend/app/modules/telemetry/`
- `backend/app/modules/audit_logging/`
- `backend/app/modules/immune_orchestrator/`
- `backend/app/modules/recovery_policy_engine/`
- `backend/mission_control_core/core/event_stream.py`

Planned new modules:

- `backend/app/modules/observer_core/` (next step)
- `backend/app/modules/discovery_layer/` (later step)

## 4) Safety Rules

1. Observer endpoints are read-only; admin controls may replay/reconcile observer data only.
2. Observer does not call mutating paths in `skill_engine`, `skills_registry`, `policy`, or `task_queue`.
3. Discovery emits proposals and evidence only.
4. Evolution Control remains the only gate for promotion/application.
5. No single runtime anomaly can directly change active skills or policies.

## 5) Sequencing Plan

### Step A (next implementation step)

Observer Core MVP:
- normalized `ObservationSignal`
- derived `ObserverState`
- read APIs
- EventStream consumer + idempotent ingestion
- tenant isolation and audit/event ordering tests

### Step B

Discovery Layer MVP:
- `SkillGap`, `CapabilityGap`, `SkillProposal`, `ProposalEvidence`
- consumes Knowledge + Consolidation + Observer signals
- proposal queue only; no direct mutation

### Step C (deferred)

Economy/selection support:
- start with minimal dimensions: confidence, frequency, impact, cost
- apply in Discovery prioritization and Evolution Control ranking
- keep credits/karma/reward/promotion-weight conceptually distinct

## 6) Risks and Mitigations

1. Role creep (Observer becomes optimizer) -> enforce read-only ACL and no mutating dependencies.
2. Proposal inflation (Discovery noise) -> require evidence thresholds and governance review.
3. Tenant leakage -> strict tenant binding at ingest + tenant-filtered reads.
4. Event duplication/order drift -> idempotent dedup keys and monotonic projection rules.
5. Economy overreach too early -> defer until Observer + Discovery contracts are stable.
