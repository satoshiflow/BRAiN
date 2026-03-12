# Immune System Adapter Coverage Matrix

Version: 1.0  
Status: Active  
Date: 2026-03-10  
Sprint: D - Immune System Hardening

## Purpose

Document the current state of adapter coverage across backend modules for immune/recovery integration, classifying each module's integration status and defining the path to comprehensive coverage.

---

## Adapter Types

| Type | Purpose | Example |
|------|---------|---------|
| **Core** | Canonical immune/recovery control plane | `immune_orchestrator`, `recovery_policy_engine` |
| **Signal Producer** | Generates incident signals for immune intake | `runtime_auditor`, `system_health` |
| **Failure Adapter** | Domain-specific failure detection and recovery | `task_queue`, `planning`, `neurorail` |
| **Enforcement Adapter** | Policy/governance enforcement and containment | `neurorail`, `genetic_quarantine` |
| **Action Sink** | Receives recovery/repair actions | `opencode_repair` |
| **Observer-Only** | Diagnostics/telemetry only, no active recovery | Learning layers (P0-P7) |
| **Compatibility** | Legacy compatibility, no new integration | Legacy `immune` module |

---

## Coverage Matrix

### Core Immune/Recovery

| Module | Type | Status | Integration Point | Notes |
|--------|------|--------|-------------------|-------|
| `immune_orchestrator` | Core | ✅ Complete | Canonical incident decision | Fully operational |
| `recovery_policy_engine` | Core | ✅ Complete | Canonical recovery policy | Fully operational |
| `opencode_repair` | Action Sink | ✅ Complete | Repair ticket creation | Wired to immune/recovery triggers |
| `genetic_integrity` | Signal Producer | ✅ Complete | DNA violation detection | Publishes to immune |
| `genetic_quarantine` | Enforcement Adapter | ✅ Complete | Mutation containment | Governance-aware |
| `immune` (legacy) | Compatibility | ✅ Subordinated | Low-level self-protection | Forwards to orchestrator |

### Health & Monitoring

| Module | Type | Status | Integration Point | Notes |
|--------|------|--------|-------------------|-------|
| `runtime_auditor` | Signal Producer | ✅ Complete | Critical anomaly publishing | Wired in Sprint B, publishes to immune_orchestrator |
| `system_health` | Signal Producer | ✅ Complete | Health degradation signals | Wired in Sprint B, publishes to immune_orchestrator |
| `health_monitor` | Signal Producer | ✅ Complete | Service failure events | Publishes to immune_orchestrator |
| `telemetry` | Observer-Only | ⏳ Future | Generic telemetry | No active recovery |
| `neurorail/telemetry` | Observer-Only | ⏳ Future | NeuroRail-specific telemetry | No active recovery |

### Existing Adapters (Pre-Sprint D)

| Module | Type | Status | Integration Point | Notes |
|--------|------|--------|-------------------|-------|
| `task_queue` | Failure Adapter | ✅ Complete | Queue stall, worker failure | Retry/backoff policies |
| `planning` | Failure Adapter | ✅ Complete | Planning failures, timeouts | Retry with backoff |
| `neurorail` | Enforcement Adapter | ✅ Complete | Policy violations, circuit break | Isolate/circuit-break actions |

### Sprint D Expansion

| Module | Type | Status | Integration Point | Notes |
|--------|------|--------|-------------------|-------|
| `agent_management` | Failure Adapter | 🔄 Sprint D | Agent failures, quota breaches | Isolate/throttle actions |

### Learning Layers (P0-P7)

| Module | Type | Status | Integration Point | Notes |
|--------|------|--------|-------------------|-------|
| `experience_layer` | Observer-Only | ⏳ Deferred | Diagnostics framework | No active recovery yet |
| `observer_core` | Observer-Only | ⏳ Deferred | Incident timeline API | Read-only diagnostics |
| `insight_layer` | Observer-Only | ⏳ Deferred | Diagnostics framework | No active recovery yet |
| `consolidation_layer` | Observer-Only | ⏳ Deferred | Diagnostics framework | No active recovery yet |
| `evolution_control` | Observer-Only | ⏳ Deferred | Governance signals | Future governance integration |
| `deliberation_layer` | Observer-Only | ⏳ Deferred | Diagnostics framework | No active recovery yet |
| `discovery_layer` | Observer-Only | ⏳ Deferred | Diagnostics framework | No active recovery yet |
| `economy_layer` | Observer-Only | ⏳ Deferred | Diagnostics framework | No active recovery yet |

### Skills & Capabilities

| Module | Type | Status | Integration Point | Notes |
|--------|------|--------|-------------------|-------|
| `skill_engine` | Observer-Only | ⏳ Deferred | SkillRun failures | Future: execution failure adapter |
| `skill_evaluator` | Observer-Only | ⏳ Deferred | Evaluation failures | Future: quality threshold adapter |
| `skills` (registry) | Observer-Only | ⏳ Deferred | Registry failures | Future: integrity adapter |
| `capabilities` | Observer-Only | ⏳ Deferred | Capability failures | Future: capability health adapter |

### Missions & Orchestration

| Module | Type | Status | Integration Point | Notes |
|--------|------|--------|-------------------|-------|
| `missions` (legacy) | Compatibility | ❌ Not Planned | Legacy runtime | Use task_queue adapter instead |
| `mission_control_core` | Observer-Only | ⏳ Deferred | Mission failures | Future: orchestration adapter |

### Governance & Security

| Module | Type | Status | Integration Point | Notes |
|--------|------|--------|-------------------|-------|
| `governance` | Signal Producer | ⏳ Deferred | Policy decisions | Future: approval workflow integration |
| `audit_logging` | Core Infrastructure | N/A | Durable audit | Not an adapter target |
| `auth` | Observer-Only | ⏳ Deferred | Auth failures | Future: security incident adapter |

### Other App Modules

| Module | Type | Status | Integration Point | Notes |
|--------|------|--------|-------------------|-------|
| `course_factory` | Observer-Only | ⏳ Deferred | Builder failures | Future: builder error adapter |
| `webgenesis` | Observer-Only | ⏳ Deferred | Generation failures | Future: generation error adapter |
| `axe_fusion` | Observer-Only | ⏳ Deferred | Trust violations | Future: DMZ breach adapter |
| `axe_governance` | Observer-Only | ⏳ Deferred | Governance signals | Future: approval flow integration |
| `cluster_management` | Observer-Only | ⏳ Deferred | Cluster health | Future: scaling adapter |
| `knowledge_layer` | Observer-Only | ⏳ Deferred | Knowledge ingestion | Covered by learning layer plan |
| `learning` | Observer-Only | ⏳ Deferred | Strategy failures | Future: learning health adapter |
| `module_lifecycle` | Core Infrastructure | N/A | Lifecycle metadata | Not an adapter target |
| `dna_engine` | Signal Producer | ✅ Via genetic_integrity | DNA mutations | Covered by genetic modules |

---

## Coverage Statistics

| Category | Total Modules | Complete | In Progress | Deferred | Not Planned | Coverage % |
|----------|---------------|----------|-------------|----------|-------------|------------|
| Core Immune/Recovery | 6 | 6 | 0 | 0 | 0 | 100% |
| Health & Monitoring | 5 | 3 | 0 | 2 | 0 | 60% |
| Existing Adapters | 3 | 3 | 0 | 0 | 0 | 100% |
| Sprint D Expansion | 1 | 0 | 1 | 0 | 0 | 0% |
| Learning Layers | 8 | 0 | 0 | 8 | 0 | 0% |
| Skills & Capabilities | 4 | 0 | 0 | 4 | 0 | 0% |
| Missions & Orchestration | 2 | 0 | 0 | 1 | 1 | 0% |
| Governance & Security | 3 | 0 | 0 | 3 | 0 | 0% |
| Other App Modules | 8 | 0 | 0 | 8 | 0 | 0% |
| **TOTAL** | **40** | **12** | **1** | **26** | **1** | **30%** |

**Immediate Coverage (Complete + In Progress):** 13/40 = **32.5%**  
**Planned Coverage (Complete + In Progress + Deferred):** 39/40 = **97.5%**

---

## Integration Patterns

### Signal Producer Pattern

**Purpose:** Module detects anomalies/failures and publishes to immune intake

**Implementation:**
```python
from app.modules.immune_orchestrator.service import get_immune_orchestrator_service

# In module service layer
immune_service = get_immune_orchestrator_service()
await immune_service.ingest_signal(
    source="module_name",
    entity_type="entity_type",
    entity_id=str(entity.id),
    correlation_id=correlation_id,
    severity="critical",  # info, warning, critical
    signal_type="anomaly",  # anomaly, degradation, failure, threat
    message="Brief description",
    technical_details={"key": "value"},
    tenant_id=tenant_id,
)
```

**Examples:**
- `runtime_auditor.publish_critical_anomalies()`
- `system_health` degradation events
- `health_monitor` service failure events

### Failure Adapter Pattern

**Purpose:** Module-specific failure detection and recovery action recommendation

**Implementation:**
```python
from app.modules.recovery_policy_engine.service import get_recovery_policy_service

# In module failure handler
recovery_service = get_recovery_policy_service()
decision = await recovery_service.request_recovery(
    db=db,
    source="module_name",
    entity_id=str(entity.id),
    failure_type="timeout",  # timeout, quota_exceeded, validation_failed, etc.
    severity="high",
    retry_count=0,
    recurrence=1,
    context={"additional": "data"},
    correlation_id=correlation_id,
)

# Execute recommended action
if decision.action == "retry":
    await module_retry_logic()
elif decision.action == "isolate":
    await module_isolate_logic()
```

**Examples:**
- `task_queue` queue stall → retry/backoff
- `planning` planning timeout → retry with backoff
- `agent_management` quota breach → isolate/throttle

### Enforcement Adapter Pattern

**Purpose:** Policy enforcement and containment actions

**Implementation:**
```python
from app.modules.recovery_policy_engine.service import get_recovery_policy_service

# In enforcement layer
recovery_service = get_recovery_policy_service()

# Check if action is permitted
if not recovery_service.is_action_permitted(
    action="isolate",
    entity_id=str(entity.id),
    requires_governance=True,
):
    raise HTTPException(403, "Action requires governance approval")

# Execute containment
await module_specific_containment()

# Report outcome
await recovery_service.record_outcome(
    decision_id=decision.decision_id,
    success=True,
    details={"containment": "active"},
)
```

**Examples:**
- `neurorail` policy violations → circuit-break
- `genetic_quarantine` mutation isolation → quarantine

---

## Adapter Development Roadmap

### Phase 1: Critical Coverage (Sprint D)
- ✅ `runtime_auditor` → immune (Complete, Sprint B)
- ✅ `system_health` → immune (Complete, Sprint B)
- ✅ `health_monitor` → immune (Complete, Sprint B)
- 🔄 `agent_management` failure adapter (Sprint D)

### Phase 2: Learning Layer Integration (Post-Sprint E)
- ⏳ `experience_layer` → diagnostics integration
- ⏳ `insight_layer` → diagnostics integration
- ⏳ `consolidation_layer` → diagnostics integration
- ⏳ `discovery_layer` → diagnostics integration
- ⏳ `evolution_control` → governance signal integration

### Phase 3: Execution Layer Adapters (Future Sprint)
- ⏳ `skill_engine` → execution failure adapter
- ⏳ `skill_evaluator` → quality threshold adapter
- ⏳ `mission_control_core` → orchestration adapter

### Phase 4: Security & Governance (Future Sprint)
- ⏳ `governance` → approval workflow integration
- ⏳ `auth` → security incident adapter
- ⏳ `axe_fusion` → trust violation adapter

---

## Testing Requirements

### Adapter Integration Tests

Each adapter must have:
- ✅ Signal ingestion test (immune receives signals correctly)
- ✅ Policy decision test (recovery returns correct action)
- ✅ Governance gate test (high-risk actions blocked without approval)
- ✅ Audit chain test (correlation IDs link signal → decision → action → outcome)

### Negative Tests

Each adapter must verify:
- ❌ Cross-tenant signals rejected
- ❌ High-risk actions without approval blocked
- ❌ Invalid signals rejected with clear error
- ❌ Circular recovery loops prevented by cooldown

---

## Maintenance & Updates

**Ownership:** `brain-architect` + `brain-security-reviewer`

**Update Cadence:**
- Sprint boundary: Update coverage statistics
- New module addition: Classify integration type and add to matrix
- Adapter implementation: Move from Deferred → In Progress → Complete
- Quarterly review: Verify deferred items, reprioritize based on operational needs

**Change Process:**
1. Propose adapter addition/modification
2. Update this matrix with proposed status
3. Implement adapter following pattern guidelines
4. Add tests per testing requirements
5. Update matrix to Complete status
6. Update `docs/roadmap/IMPLEMENTATION_PROGRESS.md`

---

## Success Criteria

- ✅ All core immune/recovery modules fully integrated
- ✅ All health/monitoring signal producers wired
- ✅ All pre-Sprint D adapters documented and tested
- ✅ Sprint D expansion (agent_management) complete
- ✅ Learning layer integration plan documented
- ✅ Coverage statistics tracked and updated
- ✅ Integration patterns documented with code examples
- ✅ Testing requirements defined for all adapter types

---

## Related Documents

- `docs/specs/immune_control_plane.md` (canonical control plane architecture)
- `docs/roadmap/BRAIN_HARDENING_ROADMAP.md` (Sprint D scope)
- `docs/architecture/backend_system_map.md` (full module inventory)
- `docs/specs/canonical_health_model.md` (health signal sources)
- `docs/specs/failure_taxonomy.md` (diagnostics framework)
