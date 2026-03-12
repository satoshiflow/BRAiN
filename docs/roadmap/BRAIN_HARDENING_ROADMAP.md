# BRAiN Backend Hardening Roadmap

Version: 1.0  
Status: Active Execution Plan  
Date: 2026-03-10  
Purpose: Systematically harden Health, Immune, Diagnostics, and Self-Healing foundation across the backend runtime after P0-P7 completion.

Dependencies:
- `docs/roadmap/BRAIN_SKILL_FIRST_IMPLEMENTATION_ROADMAP.md` (P0-P7 baseline)
- `docs/roadmap/IMPLEMENTATION_PROGRESS.md` (current state snapshot)
- Critical audit findings from 2026-03-10 backend analysis

---

## Executive Summary

After completing P0-P7 (Experience → Observer → Insight → Consolidation → Evolution Control → Deliberation → Discovery → Economy), the backend has a governed layered learning stack with lifecycle/tenant/auth guards, but **critical platform gaps remain**:

- **Health system is fragmented** across `/api/health`, `/api/health/*`, `/api/system/health*` with inconsistent contracts and silent degradation masking.
- **Immune system is split** between legacy `immune` and new `immune_orchestrator`/`recovery_policy_engine`, with weak signal routing and insufficient adapter coverage.
- **Diagnostics/error handling lacks standardization** for failure classification, provenance, correlation, and operator triage surfaces.
- **Audit/event chains are incomplete** for the new learning layers; writes are direct DB commits without durable audit → event ordering.
- **Self-healing foundation does not exist** as a safe, governed control loop.

This roadmap addresses these gaps in five dedicated sprints, each with clear ownership, acceptance criteria, verification matrix, and risk mitigation.

---

## Sprint Structure Overview

| Sprint | Name | Duration Est | Dependencies | Primary Risk |
|--------|------|--------------|--------------|--------------|
| **Sprint A** | Backend Grounding Audit | 1-2 days | None | Incomplete inventory |
| **Sprint B** | Health System Hardening | 3-5 days | Sprint A | Route ambiguity, silent degradation |
| **Sprint C** | Runtime Diagnostics & Error Framework | 3-5 days | Sprint A, Sprint B signals | False positives, correlation gaps |
| **Sprint D** | Immune System Hardening | 4-6 days | Sprint B, Sprint C | Split-brain immune, governance bypass |
| **Sprint E** | Self-Healing Foundation MVP | 3-5 days | Sprint B, Sprint C, Sprint D | Premature autonomy, unsafe actions |

Total estimated effort: **14-23 days** (non-contiguous, includes review/verification cycles).

---

## Sprint A - Backend Grounding Audit

### Objective
Systematically map the backend runtime as the foundation for Sprints B-E, producing an authoritative inventory of health surfaces, failure surfaces, audit/event coverage, immune integration, and learning layer wiring.

### Scope
- **Startup and Wiring**
  - `backend/main.py` (EventStream, immune, recovery, repair wiring)
  - Feature flags, profile-based config, autodiscovery routes
- **Event and Audit Spine**
  - `backend/app/core/event_contract.py`
  - `backend/app/core/audit_bridge.py`
  - `backend/app/modules/audit_logging/`
  - EventStream usage patterns across modules
- **Health/Telemetry/Runtime Audit Surfaces**
  - `/api/health` (legacy)
  - `/api/health/*` (health_monitor)
  - `/api/system/health*` (system_health)
  - `backend/app/modules/health_monitor/`
  - `backend/app/modules/system_health/`
  - `backend/app/modules/runtime_auditor/`
  - `backend/app/modules/telemetry/`
  - `backend/app/modules/neurorail/telemetry/`
- **Immune/Recovery/Repair Surfaces**
  - `backend/app/modules/immune/`
  - `backend/app/modules/immune_orchestrator/`
  - `backend/app/modules/recovery_policy_engine/`
  - `backend/app/modules/opencode_repair/`
  - Adapter paths: `planning`, `neurorail`, `task_queue`
- **Learning Layers P0-P7**
  - `backend/app/modules/experience_layer/`
  - `backend/app/modules/observer_core/`
  - `backend/app/modules/insight_layer/`
  - `backend/app/modules/consolidation_layer/`
  - `backend/app/modules/evolution_control/`
  - `backend/app/modules/deliberation_layer/`
  - `backend/app/modules/discovery_layer/`
  - `backend/app/modules/economy_layer/`
- **Legacy/Compatibility**
  - `backend/modules/*` (legacy runtime)
  - `backend/app/compat/*` (compatibility adapters)
  - `backend/api/routes/*` (legacy route wrappers)

### Deliverables
1. **Backend System Map** (`docs/architecture/backend_system_map.md`)
   - Module inventory with health/immune/diagnostics/audit coverage status
   - Signal flow matrix: producer → consumer chains
   - Startup wiring diagram
2. **Failure Surface Inventory** (`docs/architecture/failure_surface_inventory.md`)
   - All mutating/async paths with risk classification
   - Current error handling patterns
   - Audit/event coverage gaps
3. **False Green / Silent Fail Risk Register** (`docs/architecture/silent_fail_risks.md`)
   - Known placeholders, fallback-to-ok patterns, missing telemetry
   - Routes with conflicting health semantics

### Acceptance Criteria
- Every critical backend module is classified as:
  - Health signal producer: yes/no/partial
  - Diagnostics source: yes/no/partial
  - Immune/recovery integrated: yes/no/partial/deferred
  - Audit/event coverage: complete/partial/missing
- Signal flow matrix is complete for health, immune, diagnostics
- All "false green" patterns are documented with file:line references
- Startup wiring is diagrammed with degraded-mode behavior explicit

### Verification
- Manual inventory review by `brain-orchestrator` + `brain-architect`
- Cross-check against `AGENTS.md`, `CLAUDE.md`, existing roadmaps
- Peer review by one external reviewer (security or senior backend)

### Risks
- **Incomplete inventory**: mitigate by using explore agents for module discovery
- **Conflicting source of truth**: mitigate by treating code as authoritative, docs as supporting evidence

---

## Sprint B - Health System Hardening

### Objective
Establish one authoritative, deterministic, and auditable backend health system that unifies fragmented surfaces and eliminates false-green/silent-fail patterns.

### Why Separate Sprint
- Health is cross-cutting platform infrastructure, not a feature
- Current fragmentation creates operational ambiguity and false confidence
- Self-healing foundation requires trustworthy health signals first

### Scope
- **Health Endpoint Unification**
  - Reconcile `/api/health`, `/api/health/*`, `/api/system/health*`
  - Define canonical vs compatibility routes
  - Standardize auth/role matrix
- **Canonical Health Model**
  - Single status vocabulary: `healthy`, `degraded`, `critical`, `unknown`, `stale`
  - Layered health: liveness, service checks, system aggregate, runtime anomalies
- **Health Monitor Hardening**
  - Fix schema/model/service drift in `health_monitor`
  - Harden registration, check execution, threshold transitions, stale handling
  - Replace placeholder checks with real subsystem validation
- **System Health Aggregation**
  - Make `system_health` the explicit rollup layer
  - Eliminate placeholder-to-green fallbacks
  - Require explainable degraded/critical states
- **Runtime Auditor Activation**
  - Wire `runtime_auditor` into startup lifecycle
  - Automatic signal capture from request/queue/worker paths
  - Publish anomalies to unified immune intake (not legacy `ImmuneService`)
- **Legacy Health Route Governance**
  - Ensure `/api/health` does not mask exceptions as `ok`
  - Mark deprecated routes with `Sunset` headers and replacement links

### Workstreams
1. **Health Surface Inventory** (from Sprint A)
2. **Canonical Health Model Definition**
3. **Health Monitor Productionization**
4. **System Health Aggregation Hardening**
5. **Runtime Auditor Wiring**
6. **Health Route Compatibility Matrix**
7. **Audit/Event Consistency for Health Transitions**

### Acceptance Criteria
- One documented canonical health model exists
- Health routes do not contradict each other
- Missing/stale signals produce `unknown` or `degraded`, not `healthy`
- `runtime_auditor` runs automatically and publishes to canonical immune intake
- Legacy `/api/health` exceptions are not masked
- Health degradation/recovery produces durable audit records
- Tests cover: route contracts, status rollup, threshold transitions, stale handling, degraded dependency scenarios

### File/Area Targets
- `backend/main.py` (startup, autodiscovery)
- `backend/app/api/routes/health.py`
- `backend/app/api/routes/system_health.py`
- `backend/app/modules/health_monitor/*`
- `backend/app/modules/system_health/*`
- `backend/app/modules/runtime_auditor/*`
- `backend/app/core/audit_bridge.py`
- `backend/app/core/event_contract.py`
- Tests: `backend/tests/test_health_*.py`, `backend/tests/test_system_health_*.py`, `backend/tests/test_runtime_auditor_*.py`

### Verification Matrix
- **Route Contract Verification**: all health routes registered under expected startup modes, auth boundaries enforced
- **Health Monitor Verification**: service registration, threshold transitions, stale/no-data behavior
- **System Health Verification**: aggregate rollup correctness, explainable degraded/critical states
- **Runtime Auditor Verification**: automatic sampling, anomaly detection, background lifecycle
- **Audit Verification**: health transitions create unified audit entries with correlation IDs
- **RC Gate**: targeted health-system suite in `./scripts/run_rc_staging_gate.sh`

### Risks
- **Route ambiguity**: mitigate by explicit canonical vs compatibility classification
- **Silent degradation**: mitigate by eliminating fallback-to-ok patterns
- **Circular dependency**: mitigate by making health independent of audit/event success

### Done When
- RC gate green for health-system suite
- No "false green" patterns remain in Sprint A risk register
- Operator can trust health status for incident triage

---

## Sprint C - Runtime Diagnostics & Error Framework

### Objective
Create a standardized, correlation-backed, and provenance-linked diagnostic and error handling layer that supports both human operators and later automated recovery.

### Why Separate Sprint
- Health says "how bad", diagnostics says "why"
- Immune needs classified failures, not raw exceptions
- Evidence quality determines recovery safety

### Scope
- **Failure Taxonomy**
  - `request_failure`, `execution_failure`, `integration_failure`, `governance_failure`, `observability_failure`, `learning_pipeline_failure`
  - Standardized failure codes per class
- **Standard Failure Envelope**
  - `FailureRecord` with: `tenant_id`, `correlation_id`, `skill_run_id`, `mission_id`, `entity`, `failure_class`, `failure_code`, `severity`, `retryability`, `operator_action`, `audit_ref`, `event_ref`, `provenance_refs`
- **Structured Logging**
  - Consistent log keys across `backend/app/modules/*`
  - Bounded payloads, redaction rules, tenant-safe logging
- **Traceability & Provenance**
  - `correlation_id` propagation: request → `SkillRun` → audit → event → observer → experience/insight/pattern
  - Provenance links to `ExperienceRecord`, `InsightCandidate`, `PatternCandidate`, governance decisions
- **Operator Diagnostics**
  - Incident timeline API: failure sequence, causal chain, last known state, impacted entities
  - Read surfaces via `observer_core` for queryable incident bundles
- **Observability SLOs**
  - Correlation completeness, audit-link coverage, dropped-event rate, unknown-error rate

### Workstreams
1. **Failure Taxonomy Definition**
2. **Standard Failure Envelope Implementation**
3. **Structured Logging Rollout**
4. **Correlation & Provenance Hardening**
5. **Operator Diagnostic Surfaces**
6. **Observability SLO Tracking**

### Acceptance Criteria
- Every backend failure path emits normalized `FailureRecord` with deterministic classification
- At least 95% of mutating/async paths are traceable from trigger to audit/event/observer signal
- Operator can retrieve single incident timeline without manual log stitching
- Unknown/unclassified errors trend toward zero (tracked metric)
- Health and immune consume diagnostics via stable read contracts only

### File/Area Targets
- `backend/app/core/diagnostics.py` (new)
- `backend/app/core/event_contract.py` (extend)
- `backend/app/core/audit_bridge.py` (extend)
- `backend/app/modules/observer_core/*` (incident timeline API)
- All `backend/app/modules/*/service.py` (failure envelope adoption)
- All `backend/app/modules/*/router.py` (sanitized error responses)
- Tests: `backend/tests/test_diagnostics_*.py`, correlation/provenance integration tests

### Verification Matrix
- **Error Taxonomy**: mapping tests for all failure classes
- **Sanitized Responses**: client responses do not leak internals
- **Correlation Tests**: request → SkillRun → audit → event → observer linkage
- **Provenance Tests**: experience/insight/pattern failures link back to source SkillRun
- **Security/Governance**: tenant isolation, redaction, audit durability
- **Operational Drills**: simulate Redis loss, DB timeout, audit failure, worker stall; diagnostics remain queryable

### Risks
- **False positives**: mitigate by requiring evidence thresholds before classification
- **Correlation gaps**: mitigate by making `correlation_id` mandatory at earliest capture point
- **Redaction failure**: mitigate by schema-enforced redaction + negative tests

### Done When
- RC gate green for diagnostics suite
- Operator incident retrieval time reduced by 80% (measured)
- Unknown-error rate < 5% of total backend errors

---

## Sprint D - Immune System Hardening

### Objective
Establish one canonical, governance-aware, and auditable immune control plane that unifies signal intake, incident decision, recovery policy, and containment actions.

### Why Separate Sprint
- Immune is a control layer, not a passive observer
- Current split-brain model creates routing ambiguity and governance bypass risk
- Self-healing requires deterministic, auditable immune decisions

### Scope
- **Immune Control Plane Consolidation**
  - Reconcile legacy `immune` with new `immune_orchestrator`
  - Define authoritative decision path
- **Runtime Anomaly Ingestion**
  - Unify critical anomaly publishing from `runtime_auditor`, `system_health`, other producers
  - Normalized `IncidentSignal` intake
- **Recovery Policy Hardening**
  - Deterministic retry, circuit-break, isolate, rollback, escalate policies
  - Separate "recommended" from "permitted" actions
  - Governance hooks for high-risk actions
- **Adapter Coverage Expansion**
  - Beyond `planning`, `neurorail`, `task_queue`
  - Classify all modules: integrated, observer-only, compatibility, deferred
  - Minimum: health/runtime/learning-adjacent modules
- **Governance Routing**
  - High-risk actions require approval, not just boolean flags
  - Link `requires_governance_hook` to concrete approval/policy surfaces
- **Audit Chain Hardening**
  - Incident → Decision → Governance → Action → Outcome linkable by correlation ID
- **Startup Reliability**
  - Immune/recovery wiring consistent in required EventStream mode

### Workstreams
1. **Immune Control Plane Consolidation**
2. **Runtime Anomaly Ingestion Hardening**
3. **Recovery Policy Hardening**
4. **Adapter Coverage Expansion**
5. **Governance and Signal Routing**
6. **Audit Chain Completeness**
7. **Bootstrap Reliability**

### Acceptance Criteria
- `immune_orchestrator` is documented and enforced canonical decision path
- Critical runtime/health signals flow through unified intake
- High-risk recovery actions cannot bypass governance routing
- Adapter status documented for all in-scope backend modules
- Incident → Repair/Outcome is auditable with correlation IDs
- Legacy `immune` behavior is subordinated or clearly marked compatibility-only
- Startup wiring produces consistent immune/recovery graph in required EventStream mode

### File/Area Targets
- `backend/main.py` (startup wiring)
- `backend/app/modules/immune/`
- `backend/app/modules/immune_orchestrator/*`
- `backend/app/modules/recovery_policy_engine/*`
- `backend/app/modules/runtime_auditor/*` (publish to immune)
- `backend/app/modules/system_health/*` (publish to immune)
- `backend/app/modules/opencode_repair/*` (repair sink)
- Adapter producers: `backend/app/modules/planning/`, `backend/app/modules/neurorail/`, `backend/app/modules/task_queue/`, `backend/app/modules/agent_management/`, etc.
- Tests: `backend/tests/test_immune_*.py`, `backend/tests/test_recovery_*.py`, adapter-path tests

### Verification Matrix
- **Contract Verification**: `immune.decision`, `recovery.action` event envelopes
- **Routing Verification**: `runtime_auditor` → canonical immune, `system_health` → canonical immune
- **Governance Verification**: isolate/rollback/escalate cannot bypass approval
- **Audit Verification**: correlation IDs link source signal → decision → action → outcome
- **Adapter Verification**: in-scope producers have adapter, observer contract, or deferred status
- **Bootstrap Verification**: required EventStream mode wires immune/recovery consistently
- **RC Gate**: immune/recovery suite

### Risks
- **Split-brain immune**: mitigate by making `immune_orchestrator` authoritative
- **Governance bypass**: mitigate by requiring approval records, not JSON presence
- **Adapter drift**: mitigate by versioned adapter contracts and validation tests
- **False positive overload**: mitigate by dedup/rate-limit at ingestion

### Done When
- RC gate green for immune/recovery suite
- No critical anomaly publishing bypasses canonical immune intake
- High-risk actions are blocked without governance approval (negative test passes)

---

## Sprint E - Self-Healing Foundation MVP

### Objective
Establish the safe, bounded, and auditable control loop foundation for future self-healing automation, without enabling unsafe autonomous behavior prematurely.

### Why After Sprint B/C/D
- Self-healing requires trustworthy health signals (Sprint B)
- Self-healing requires classified diagnostics (Sprint C)
- Self-healing requires governed immune decisions (Sprint D)
- Premature autonomy is operationally unsafe

### Scope
- **Control Loop Definition**
  - detect → classify → summarize → decide → approve → act → verify → rollback
  - Explicit boundaries between stages
- **Action Classes (Narrow MVP Set)**
  - `retry` (safe, bounded)
  - `isolate` (reversible)
  - `backoff` (reversible)
  - `circuit_break` (reversible)
  - `repair_ticket` (human-in-loop)
  - **NOT** broad autonomous mutation yet
- **Safety Rails**
  - Cooldowns, recurrence thresholds, anti-loop protection
  - Rollback-safe thresholds
  - Maximum blast radius limits
- **Evidence Thresholds**
  - Self-healing only on verified, classified, correlated signals
  - No action on `unknown` failures or missing diagnostics
- **Post-Action Verification**
  - Every action requires success/failure/no-effect evaluation
  - Automatic rollback on verification failure

### Workstreams
1. **Control Loop Architecture**
2. **Safe Action Class Implementation**
3. **Safety Rails and Thresholds**
4. **Evidence Quality Gates**
5. **Post-Action Verification Framework**
6. **Operator Override and Manual Mode**

### Acceptance Criteria
- Self-healing control loop is documented with clear stage boundaries
- Only narrow, reversible action classes are enabled
- Every action is explainable, auditable, and reversible
- No action executes without verified evidence thresholds
- Post-action verification is mandatory and enforced
- Operator can disable self-healing per module/entity/tenant
- Tests cover: control loop stages, safety rails, rollback paths, evidence thresholds, governance integration

### File/Area Targets
- `backend/app/modules/self_healing/` (new module)
- `backend/app/modules/immune_orchestrator/*` (action dispatch)
- `backend/app/modules/recovery_policy_engine/*` (policy enforcement)
- `backend/app/modules/opencode_repair/*` (repair execution)
- `backend/app/core/event_contract.py` (self-healing events)
- `backend/app/core/audit_bridge.py` (self-healing audit)
- Tests: `backend/tests/test_self_healing_*.py`, safety-rail tests, rollback tests

### Verification Matrix
- **Control Loop Verification**: each stage produces expected outputs and audit records
- **Action Safety Verification**: only permitted action classes execute, high-risk actions blocked
- **Evidence Threshold Verification**: actions blocked when evidence incomplete or unverified
- **Rollback Verification**: post-action verification failures trigger automatic rollback
- **Governance Verification**: governance-required actions cannot bypass approval
- **Operator Override Verification**: manual mode disables autonomous actions
- **RC Gate**: self-healing suite

### Risks
- **Premature autonomy**: mitigate by narrow action classes + mandatory governance
- **Unsafe actions**: mitigate by whitelist-only permitted actions
- **Evidence quality**: mitigate by mandatory threshold enforcement
- **Loop failures**: mitigate by anti-loop protection and cooldowns

### Done When
- RC gate green for self-healing suite
- Control loop stages are independently testable and auditable
- No unsafe action class is enabled
- Operator override works reliably

---

## Cross-Sprint Governance

### Module Lifecycle Integration
- Each sprint deliverable updates `backend/app/modules/module_lifecycle/` with contract status, event coverage, audit policy, migration adapter
- Deprecated/retired modules block hardening writes (consistency with P0-P7 pattern)

### Documentation Cadence
- Each sprint produces:
  - Architecture spec in `docs/specs/`
  - Implementation evidence in `docs/roadmap/IMPLEMENTATION_PROGRESS.md`
  - Updated system map in `docs/architecture/`
- Monthly governance packages (started in Post-P7 cadence) include hardening progress

### Verification Standards
- All sprints require:
  - Targeted pytest suite green
  - `./scripts/run_rc_staging_gate.sh` green
  - Peer review by `brain-security-reviewer` + `brain-verification-engineer`
  - Durable audit evidence for mutating paths

### Risk Mitigation Matrix

| Risk | Sprint | Mitigation |
|------|--------|------------|
| Incomplete inventory | A | Use explore agents, treat code as truth |
| Route ambiguity | B | Canonical vs compatibility classification |
| Silent degradation | B | Eliminate fallback-to-ok patterns |
| Correlation gaps | C | Mandatory `correlation_id` at earliest capture |
| Split-brain immune | D | Make `immune_orchestrator` authoritative |
| Governance bypass | D | Require approval records, not JSON flags |
| Premature autonomy | E | Narrow action classes + mandatory governance |

---

## Success Criteria (All Sprints Complete)

- Backend has one authoritative health model with deterministic status and explainable degradations
- All critical runtime paths emit classified, correlated, and auditable failure records
- Immune/recovery control plane is unified, governance-aware, and adapter-backed
- Self-healing foundation exists as safe, bounded, and auditable control loop
- No "false green" patterns remain
- Operator incident triage time reduced by 80%
- RC gate includes health/diagnostics/immune/self-healing suites
- Documentation is synchronized with runtime behavior

---

## Next Steps

1. **Commit this roadmap** to `docs/roadmap/BRAIN_HARDENING_ROADMAP.md`
2. **Update roadmap index** in `docs/roadmap/README.md`
3. **Start Sprint A** in current or new session
4. **Track progress** in `docs/roadmap/IMPLEMENTATION_PROGRESS.md`
5. **Monthly governance package** includes hardening status starting 2026-04

---

## Related Documents

- `docs/roadmap/BRAIN_SKILL_FIRST_IMPLEMENTATION_ROADMAP.md` (P0-P7 baseline)
- `docs/roadmap/IMPLEMENTATION_PROGRESS.md` (execution log)
- `docs/roadmap/BRAIN_POST_P7_OPERATIONS_CADENCE.md` (ongoing operations)
- `AGENTS.md` (agent execution model)
- `CLAUDE.md` (security/architecture constraints)
