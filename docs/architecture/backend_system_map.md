# Backend System Map

**Version:** 1.0  
**Date:** 2026-03-10  
**Sprint:** A - Backend Grounding Audit  
**Purpose:** Authoritative inventory of BRAiN backend runtime architecture with health/immune/diagnostics/audit coverage classification.

---

## Executive Summary

The BRAiN backend consists of **83 app modules** under `backend/app/modules/` plus legacy compatibility surfaces in `backend/modules/` and `backend/api/routes/`. The runtime is anchored by:

- **EventStream** (ADR-001 required core infrastructure) from `mission_control_core`
- **Audit Bridge** (`app.core.audit_bridge`) for unified audit writes
- **Event Contract** (`app.core.event_contract`) for standardized event envelopes
- **Health Monitor**, **System Health**, and **Runtime Auditor** (incomplete/fragmented health surfaces)
- **Immune/Recovery/Repair** split across legacy `immune`, new `immune_orchestrator`, `recovery_policy_engine`, and `opencode_repair`

**Critical Gap:** Health system is fragmented across three route families (`/api/health`, `/api/health/*`, `/api/system/health*`) with conflicting semantics and silent degradation patterns. Audit/event coverage incomplete for learning layers (P0-P7). Immune system split-brain risk.

---

## 1. Module Inventory

### 1.1 Core Infrastructure (backend/app/core)

| Module | Purpose | Health Signal | Diagnostics | Audit/Event | Immune Integration |
|--------|---------|---------------|-------------|-------------|-------------------|
| `event_contract.py` | Event envelope standard | N/A | N/A | **Producer** | N/A |
| `audit_bridge.py` | Unified audit writer | N/A | N/A | **Producer** | N/A |
| `event_bus.py` | Legacy event bus (deprecated) | N/A | N/A | Partial | N/A |
| `database.py` | AsyncSession factory | No | No | No | No |
| `redis_client.py` | Redis connection pool | No | No | No | No |
| `security.py` | Auth/token logic | No | No | Partial | No |
| `auth_deps.py` | FastAPI dependencies | No | No | No | No |
| `logging.py` | Log configuration | N/A | **Producer** | No | No |
| `config.py` | Settings management | N/A | N/A | No | No |

**Status:** Core audit/event infrastructure exists. No explicit health signals from core dependencies (DB, Redis). Security operations lack comprehensive audit trail.

---

### 1.2 Health/Telemetry/Runtime Audit Surfaces

| Module | Health Signal | Diagnostics | Audit/Event | Immune Integration | Notes |
|--------|---------------|-------------|-------------|-------------------|-------|
| `health_monitor/` | **Producer** | Partial | EventStream only | Optional EventStream | `backend/app/modules/health_monitor/service.py:26-294` - EventStream optional, DB-backed service checks, threshold transitions |
| `system_health/` | **Aggregator** | **Producer** | No | Consumes immune/threats | `backend/app/modules/system_health/service.py:61-503` - Aggregates immune/threats/mission/agent health; **fallback-to-ok on exceptions** |
| `runtime_auditor/` | **Producer** | **Producer** | Partial | Publishes to immune | `backend/app/modules/runtime_auditor/service.py:69-628` - Continuous monitoring, anomaly detection, publishes critical anomalies to immune |
| `telemetry/` | Unknown | Unknown | Unknown | Unknown | Not examined in detail |
| `neurorail/telemetry/` | Unknown | Unknown | EventStream likely | Unknown | NeuroRail subsystem telemetry |

**Critical Observations:**
- **Runtime Auditor is NOT wired into startup** - `backend/main.py` does not initialize or start `RuntimeAuditor` background loop
- `system_health` aggregates but has **fallback-to-ok** patterns: `backend/app/api/routes/health.py:54` returns `status: "ok"` on exception
- `health_monitor` has placeholder check implementations: `backend/app/modules/health_monitor/service.py:242-284` always returns `HEALTHY` for database/cache/external

---

### 1.3 Health Routes (Fragmented Surface)

| Route | Handler | Semantics | Audit Coverage | Silent Fail Risk |
|-------|---------|-----------|----------------|------------------|
| `/api/health` | `backend/app/api/routes/health.py:25-57` | Legacy health check (deprecated) | No | **YES** - returns `status: "ok"` on exception (line 54) |
| `/api/health/*` | `backend/app/modules/health_monitor/router.py` | Service-level health checks | EventStream only | Partial - placeholder checks always healthy |
| `/api/system/health` | `backend/app/modules/system_health/router.py` | System-wide health aggregation | No | Partial - fallback patterns exist |

**Conflict:** Three route families with overlapping responsibilities, no canonical route documented, deprecated route still returns `ok` on failure.

---

### 1.4 Immune/Recovery/Repair Surfaces

| Module | Purpose | Health Signal | Diagnostics | Audit/Event | EventStream Integration | Notes |
|--------|---------|---------------|-------------|-------------|------------------------|-------|
| `immune/` (legacy) | Legacy immune events | Consumer | Consumer | Partial | Optional | `backend/app/modules/immune/core/service.py` - event storage, health summary |
| `immune_orchestrator/` | **NEW** immune control plane | Consumer | **Producer** | **Audit Bridge** | **Required** | `backend/app/modules/immune_orchestrator/service.py:142-147` - decision engine, audit writes, EventStream required |
| `recovery_policy_engine/` | Recovery policy executor | Consumer | **Producer** | **Audit Bridge** | **Required** | `backend/app/modules/recovery_policy_engine/service.py:17,182` - policy application, audit writes |
| `genetic_integrity/` | DNA mutation detection | **Producer** | **Producer** | **Audit Bridge** | **Required** | `backend/app/modules/genetic_integrity/service.py:92,189` - integrity scans, audit writes |
| `genetic_quarantine/` | Quarantine enforcement | **Producer** | Partial | **Audit Bridge** | **Required** | `backend/app/modules/genetic_quarantine/service.py:274` |
| `opencode_repair/` | Repair ticket system | Consumer | Partial | **Audit Bridge** | **Required** | `backend/app/modules/opencode_repair/service.py:274` - repair loop consumer |

**Wiring Status (backend/main.py:204-220):**
- EventStream wired to: `immune_orchestrator`, `recovery_policy_engine`, `genetic_integrity`, `genetic_quarantine`, `opencode_repair`
- Repair trigger wired from immune/recovery high-risk outcomes
- **Legacy `immune` is NOT wired** - operates independently with optional EventStream

**Split-Brain Risk:** Legacy `immune` and new `immune_orchestrator` both exist; routing ambiguity for signal intake.

---

### 1.5 Learning Layers (P0-P7)

| Module | Purpose | Health Signal | Diagnostics | Audit/Event | EventStream Integration |
|--------|---------|---------------|-------------|-------------|------------------------|
| `experience_layer/` (P0) | SkillRun experience ingestion | No | No | **Missing** | No |
| `observer_core/` (P1) | Real-time observation signals | No | No | **Missing** | No |
| `insight_layer/` (P2) | Insight derivation | No | No | **Missing** | No |
| `consolidation_layer/` (P3) | Pattern consolidation | No | No | **Missing** | No |
| `evolution_control/` (P4) | Evolution proposals | No | No | **Missing** | No |
| `deliberation_layer/` (P5) | Mission deliberation | No | No | **Missing** | No |
| `discovery_layer/` (P6) | Skill discovery | No | No | **Missing** | No |
| `economy_layer/` (P7) | Economic assessment | No | No | **Missing** | No |

**Critical Gap:** All learning layers perform **direct DB writes** without audit → event ordering. No health signal producers. No diagnostics sources. Governance decisions (approve/reject) lack audit trail.

**File References:**
- Experience: `backend/app/modules/experience_layer/service.py`
- Observer: `backend/app/modules/observer_core/service.py`
- Insight: `backend/app/modules/insight_layer/service.py`
- Consolidation: `backend/app/modules/consolidation_layer/service.py`
- Evolution: `backend/app/modules/evolution_control/service.py`
- Deliberation: `backend/app/modules/deliberation_layer/service.py`
- Discovery: `backend/app/modules/discovery_layer/service.py`
- Economy: `backend/app/modules/economy_layer/service.py`

---

### 1.6 Skills/Capabilities/Execution Runtime

| Module | Health Signal | Diagnostics | Audit/Event | Immune Integration |
|--------|---------------|-------------|-------------|-------------------|
| `skills_registry/` | No | No | Partial | No |
| `capabilities_registry/` | No | No | Partial | No |
| `skill_engine/` | No | No | Partial | No |
| `skill_evaluator/` | No | No | No | No |
| `skill_optimizer/` | No | No | No | No |
| `capability_runtime/` | No | No | Partial | No |
| `agent_management/` | **Producer** | Partial | EventStream | Adapter exists |
| `task_queue/` | **Producer** | Partial | EventStream | Adapter exists |
| `planning/` | No | Partial | EventStream | Adapter exists |

**Status:** Skill execution path has partial EventStream coverage. Agent/task management produce events. Planning has adapter. No health signal aggregation from execution layer.

---

### 1.7 Additional App Modules (Partial Inventory)

| Module Category | Examples | Health Signal | Diagnostics | Audit/Event | Immune Integration |
|-----------------|----------|---------------|-------------|-------------|-------------------|
| **Business/Course** | `course_factory/`, `course_distribution/`, `business_factory/` | No | No | EventStream | No |
| **Governance** | `governance/`, `ir_governance/` | No | Partial | EventStream + Audit | No |
| **AXE Integration** | `axe_fusion/`, `axe_identity/`, `axe_knowledge/`, `axe_widget/` | No | No | Partial | No |
| **Cluster System** | `cluster_system/` | No | No | Partial | No |
| **NeuroRail** | `neurorail/identity/`, `neurorail/lifecycle/`, `neurorail/execution/`, etc. | No | Partial | EventStream | No |
| **Memory/Learning** | `memory/`, `learning/`, `knowledge_layer/`, `knowledge_graph/` | No | No | EventStream (partial) | No |
| **Web/Genesis** | `webgenesis/`, `genesis/` | No | No | Partial | No |
| **DNA/Karma/Credits** | `dna/`, `karma/`, `credits/`, `policy/`, `threats/` | Partial | Partial | Partial | Legacy immune consumer |
| **Sovereign/DMZ** | `sovereign_mode/`, `dmz_control/`, `foundation/` | No | No | Partial | No |
| **PayCore** | `paycore/` | No | No | Partial | No |

**Total Modules:** 83 in `backend/app/modules/`

---

### 1.8 Legacy Compatibility Surfaces

| Surface | Purpose | Health Signal | Audit/Event | Status |
|---------|---------|---------------|-------------|--------|
| `backend/modules/` | Legacy runtime modules | No | No | Compatibility-only, opt-in via `ENABLE_LEGACY_SUPERVISOR_ROUTER` |
| `backend/api/routes/` | Legacy API routes | No | No | Opt-in via `ENABLE_LEGACY_ROUTER_AUTODISCOVERY` |
| `backend/app/compat/` | Compatibility adapters | N/A | No | Active - `legacy_missions`, `legacy_supervisor` |

**Legacy Route Inventory (backend/api/routes/):** 17 route files including `missions.py`, `skills.py`, `business.py`, `courses.py`, `axe.py`, `chat.py`, etc.

---

## 2. Signal Flow Matrix

### 2.1 Health Signal Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        Health Signal Producers                  │
├─────────────────────────────────────────────────────────────────┤
│ health_monitor         → EventStream (optional)                 │
│ runtime_auditor        → immune_orchestrator (if wired)         │
│ agent_management       → EventStream → health_monitor           │
│ task_queue             → EventStream → health_monitor           │
│ immune (legacy)        → internal storage only                  │
│ threats                → system_health (direct call)            │
│ missions (compat)      → system_health (direct call)            │
└─────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                        Health Aggregators                        │
├─────────────────────────────────────────────────────────────────┤
│ system_health          → /api/system/health, /api/health        │
│                          (aggregates immune, threats, missions) │
└─────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                         Health Consumers                         │
├─────────────────────────────────────────────────────────────────┤
│ Operators/Monitoring   → /api/health, /api/system/health        │
│ immune_orchestrator    → (could consume, not currently wired)   │
└─────────────────────────────────────────────────────────────────┘
```

**Gap:** `runtime_auditor` is NOT wired into startup, so anomaly → immune signal path is inactive. Health routes don't publish audit records on degradation.

---

### 2.2 Immune/Recovery Signal Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Anomaly/Incident Producers                   │
├─────────────────────────────────────────────────────────────────┤
│ runtime_auditor        → immune_orchestrator (NOT WIRED)        │
│ system_health          → (no immune publishing)                 │
│ planning adapter       → immune_orchestrator (via adapter)      │
│ neurorail adapter      → immune_orchestrator (via adapter)      │
│ task_queue adapter     → immune_orchestrator (via adapter)      │
│ genetic_integrity      → immune_orchestrator                    │
│ genetic_quarantine     → immune_orchestrator                    │
└─────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Immune Decision Layer                         │
├─────────────────────────────────────────────────────────────────┤
│ immune_orchestrator    → decision engine + priority routing     │
│ immune (legacy)        → (parallel system, NOT integrated)      │
└─────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Recovery Policy Engine                        │
├─────────────────────────────────────────────────────────────────┤
│ recovery_policy_engine → retry, circuit-break, isolate, etc.   │
│                        → triggers repair_trigger callback       │
└─────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                        Repair Execution                          │
├─────────────────────────────────────────────────────────────────┤
│ opencode_repair        → creates repair tickets from signals    │
└─────────────────────────────────────────────────────────────────┘
```

**Split-Brain Risk:** Legacy `immune` operates independently. No documented authoritative path.

---

### 2.3 Audit/Event Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        Audit Producers                           │
├─────────────────────────────────────────────────────────────────┤
│ audit_bridge           → audit_logging module (PostgreSQL)      │
│ immune_orchestrator    → audit_bridge (decisions)               │
│ recovery_policy_engine → audit_bridge (actions)                 │
│ genetic_integrity      → audit_bridge (scans)                   │
│ genetic_quarantine     → audit_bridge (quarantine ops)          │
│ opencode_repair        → audit_bridge (repair tickets)          │
│ Learning layers (P0-P7) → MISSING (direct DB writes only)      │
└─────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────┐
│                        Event Producers                           │
├─────────────────────────────────────────────────────────────────┤
│ EventStream publishers:                                          │
│ - course_factory, ir_governance, task_queue, agent_management  │
│ - memory, planning, dna, health_monitor (optional)             │
│ - immune_orchestrator, recovery_policy_engine, etc. (via core)  │
│ NOT publishing:                                                  │
│ - experience_layer, observer_core, insight_layer,              │
│   consolidation_layer, evolution_control, deliberation_layer,  │
│   discovery_layer, economy_layer                                │
└─────────────────────────────────────────────────────────────────┘
```

**Critical Gap:** Learning layers (P0-P7) do NOT publish audit or event records. Governance decisions (approve/reject) lack audit trail.

---

## 3. Startup Wiring Diagram

### 3.1 Startup Sequence (backend/main.py:156-304)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Logging Configuration                                         │
│    app.core.logging.configure_logging()                          │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Startup Profile Detection                                     │
│    BRAIN_STARTUP_PROFILE = full | minimal (default: full)       │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Redis Connection (optional)                                   │
│    get_redis() → ping → set app.state.redis                     │
│    WARNING if unavailable (EventStream disabled)                │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. EventStream Initialization (ADR-001 required by default)     │
│    BRAIN_EVENTSTREAM_MODE = required | degraded (default: req) │
│    - required: MUST start, RuntimeError if unavailable          │
│    - degraded: Skip with warning (Dev/CI only)                  │
│    EventStream(redis_url) → initialize() → start()              │
│    Set app.state.event_stream                                    │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Immune/Recovery/Repair Wiring (main.py:204-220)             │
│    - get_immune_orchestrator_service(event_stream)              │
│    - get_recovery_policy_service(event_stream)                  │
│    - get_genetic_integrity_service(event_stream)                │
│    - get_genetic_quarantine_service(event_stream)               │
│    - get_opencode_repair_service(event_stream)                  │
│    - Set repair_trigger callbacks from immune/recovery          │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. Planning EventStream Injection (optional, main.py:223-227)  │
│    Try: set_planning_event_stream(event_stream)                 │
│    WARNING if unavailable                                        │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. Mission Worker (optional, main.py:252-257)                  │
│    ENABLE_MISSION_WORKER=true (default: true)                   │
│    start_mission_worker(event_stream) → background task         │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 8. Metrics Collector (optional, main.py:260-263)               │
│    ENABLE_METRICS_COLLECTOR=true (default: true)                │
│    start_metrics_collector(collection_interval=30)              │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 9. Autoscaler Worker (optional, main.py:266-269)               │
│    ENABLE_AUTOSCALER=true (default: true)                        │
│    start_autoscaler(check_interval=60)                          │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 10. Built-in Skill Seeding (optional, main.py:272-279)         │
│     ENABLE_BUILTIN_SKILL_SEED=true (default: true)              │
│     seed_builtin_skills(db)                                      │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Degraded Mode Behavior

| Mode | EventStream | Immune/Recovery | Mission Worker | Health | Notes |
|------|-------------|-----------------|----------------|--------|-------|
| **required** (default) | **MUST start** | Wired | Wired with EventStream | Partial | Production default per ADR-001 |
| **degraded** (Dev/CI) | Skipped with warning | **NOT wired** | Wired without EventStream | Partial | Violates ADR-001 |
| **Redis unavailable** | Disabled | **NOT wired** | May fail | Partial | Fallback path |

**Critical Observation:** In degraded mode or Redis-unavailable mode, immune/recovery system is NOT wired, creating a governance/safety gap.

---

### 3.3 NOT Wired at Startup

| Component | Status | Impact |
|-----------|--------|--------|
| `runtime_auditor` | **NOT initialized** | Continuous monitoring inactive, anomaly → immune path broken |
| `health_monitor` | **NOT initialized** | Service health checks inactive |
| Learning layer audit/event | **NOT wired** | P0-P7 mutations not audited |
| Legacy `immune` | Optional via module import | Split-brain risk, no canonical path |

---

## 4. Coverage Classification Summary

### 4.1 Health Signal Coverage

| Category | Producer | Partial | No Coverage |
|----------|----------|---------|-------------|
| **Core Infrastructure** | 0 | 0 | 9 |
| **Health/Telemetry** | 3 | 1 | 1 |
| **Immune/Recovery** | 2 | 0 | 4 |
| **Learning Layers (P0-P7)** | 0 | 0 | 8 |
| **Skills/Execution** | 2 | 1 | 6 |
| **Other App Modules** | ~5 | ~10 | ~58 |

**Total Modules with Health Signals:** ~12 / 83 (14%)

---

### 4.2 Diagnostics Coverage

| Category | Producer | Partial | No Coverage |
|----------|----------|---------|-------------|
| **Core Infrastructure** | 1 (logging) | 0 | 8 |
| **Health/Telemetry** | 2 | 1 | 2 |
| **Immune/Recovery** | 3 | 1 | 2 |
| **Learning Layers (P0-P7)** | 0 | 0 | 8 |
| **Skills/Execution** | 0 | 3 | 6 |
| **Other App Modules** | ~5 | ~15 | ~53 |

**Total Modules with Diagnostics:** ~11 / 83 (13%)

---

### 4.3 Audit/Event Coverage

| Category | Complete | Partial | Missing |
|----------|----------|---------|---------|
| **Core Infrastructure** | 2 (event_contract, audit_bridge) | 1 | 6 |
| **Health/Telemetry** | 0 | 2 | 3 |
| **Immune/Recovery** | 4 (orchestrator, recovery, integrity, quarantine, repair) | 1 | 1 |
| **Learning Layers (P0-P7)** | 0 | 0 | **8** |
| **Skills/Execution** | 0 | 4 | 5 |
| **Other App Modules** | ~10 | ~20 | ~43 |

**Total Modules with Complete Audit/Event:** ~16 / 83 (19%)  
**Critical Gap:** Learning layers (P0-P7) have ZERO audit/event coverage

---

### 4.4 Immune Integration Coverage

| Category | Integrated | Adapter Exists | Observer-Only | Deferred |
|----------|------------|----------------|---------------|----------|
| **Core Infrastructure** | 0 | 0 | 0 | 9 |
| **Health/Telemetry** | 1 (runtime_auditor if wired) | 0 | 2 | 2 |
| **Immune/Recovery** | 5 (orchestrator, recovery, integrity, quarantine, repair) | 0 | 1 (legacy immune) | 0 |
| **Learning Layers (P0-P7)** | 0 | 0 | 0 | **8** |
| **Skills/Execution** | 0 | 3 (agent_mgmt, task_queue, planning) | 2 | 4 |
| **Other App Modules** | ~2 | ~5 | ~10 | ~56 |

**Total Modules with Immune Integration:** ~8 / 83 (10%)

---

## 5. Architectural Observations

### 5.1 Strengths

1. **EventStream backbone exists** and is wired to immune/recovery/repair with required mode
2. **Audit bridge provides unified audit writing** to PostgreSQL
3. **Event contract standardizes event envelopes** for runtime events
4. **Immune/recovery/repair** architecture is governance-aware and uses audit bridge
5. **Adapter pattern** exists for immune integration (planning, neurorail, task_queue)

### 5.2 Critical Gaps

1. **Health system fragmentation:** Three route families (`/api/health`, `/api/health/*`, `/api/system/health*`) with conflicting semantics
2. **Runtime auditor NOT wired:** Continuous monitoring inactive, anomaly → immune path broken
3. **Learning layers (P0-P7) lack audit/event coverage:** Direct DB writes without durable audit → event ordering
4. **Immune split-brain risk:** Legacy `immune` and new `immune_orchestrator` both exist with no documented canonical path
5. **Health routes have silent-fail patterns:** Legacy `/api/health` returns `ok` on exception
6. **Placeholder health checks:** `health_monitor` has placeholder implementations that always return `HEALTHY`

### 5.3 Governance Risks

1. **Immune routing ambiguity:** No documented authoritative decision path between legacy and new immune
2. **Degraded mode disables immune/recovery:** Violates safety requirements in non-production environments
3. **Learning layer governance decisions lack audit trail:** Approve/reject operations not audited
4. **Health degradation lacks audit records:** No durable record of health state transitions outside EventStream

---

## 6. File Reference Index

### Health/Telemetry/Runtime Audit
- `backend/app/api/routes/health.py` (legacy health endpoint)
- `backend/app/api/routes/system_health.py` (wrapper)
- `backend/app/modules/health_monitor/service.py` (service checks)
- `backend/app/modules/system_health/service.py` (aggregator)
- `backend/app/modules/runtime_auditor/service.py` (continuous monitoring)

### Immune/Recovery/Repair
- `backend/app/modules/immune/core/service.py` (legacy immune)
- `backend/app/modules/immune_orchestrator/service.py` (new immune)
- `backend/app/modules/recovery_policy_engine/service.py` (policy engine)
- `backend/app/modules/genetic_integrity/service.py` (integrity scans)
- `backend/app/modules/genetic_quarantine/service.py` (quarantine)
- `backend/app/modules/opencode_repair/service.py` (repair tickets)

### Core Infrastructure
- `backend/app/core/event_contract.py` (event envelopes)
- `backend/app/core/audit_bridge.py` (unified audit writer)
- `backend/mission_control_core/core/event_stream.py` (EventStream)

### Learning Layers (P0-P7)
- `backend/app/modules/experience_layer/service.py` (P0)
- `backend/app/modules/observer_core/service.py` (P1)
- `backend/app/modules/insight_layer/service.py` (P2)
- `backend/app/modules/consolidation_layer/service.py` (P3)
- `backend/app/modules/evolution_control/service.py` (P4)
- `backend/app/modules/deliberation_layer/service.py` (P5)
- `backend/app/modules/discovery_layer/service.py` (P6)
- `backend/app/modules/economy_layer/service.py` (P7)

### Startup/Lifecycle
- `backend/main.py` (unified entry point, startup wiring)

---

## 7. Next Steps (Sprint B-E Dependencies)

This system map serves as authoritative input for:

- **Sprint B (Health System Hardening):** Reconcile route families, eliminate silent-fail patterns, wire runtime_auditor
- **Sprint C (Diagnostics & Error Framework):** Standardize failure taxonomy, add correlation/provenance to learning layers
- **Sprint D (Immune System Hardening):** Consolidate legacy/new immune, expand adapter coverage, document canonical path
- **Sprint E (Self-Healing Foundation MVP):** Build control loop on hardened health/diagnostics/immune foundation

---

**End of Backend System Map**
