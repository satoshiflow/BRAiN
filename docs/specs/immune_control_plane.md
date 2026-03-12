# Immune Control Plane Specification

Version: 1.0  
Status: Active  
Date: 2026-03-10  
Sprint: D - Immune System Hardening

## Purpose

Define the canonical immune control plane architecture that resolves the split-brain model between legacy `immune` and new `immune_orchestrator`/`recovery_policy_engine`, establishing one authoritative decision path for incident classification, recovery action selection, and governance-aware containment.

---

## Architecture Overview

### Canonical Control Plane

**Decision Authority:**
- `immune_orchestrator` = canonical incident classification, prioritization, escalation
- `recovery_policy_engine` = canonical recovery action selection, cooldown, escalation policy
- Legacy `immune` = subordinated compatibility layer, no independent decision authority

**Signal Intake:**
- All critical runtime anomalies flow through `immune_orchestrator.ingest_signal()`
- Sources: `runtime_auditor`, `system_health`, `health_monitor`, module-specific adapters
- Format: normalized `IncidentSignal` with correlation, severity, entity, source

**Action Dispatch:**
- `recovery_policy_engine` recommends actions based on policy rules
- `immune_orchestrator` enforces governance gates before dispatch
- High-risk actions (isolate, rollback, escalate) require approval records

**Audit Chain:**
- Every signal → decision → action → outcome linkable by correlation ID
- Durable audit via `audit_bridge`, events via `event_contract`

---

## Split-Brain Resolution

### Legacy `immune` Module

**Status:** Compatibility layer, subordinated to orchestrator

**Permitted Functions:**
- Low-level self-protection (memory threshold kill-switch)
- Compatibility wrapper for existing code expecting `ImmuneService`
- Signal forwarding to `immune_orchestrator`

**Prohibited Functions:**
- Independent incident classification
- Direct recovery action dispatch
- Governance decisions
- Bypass of canonical signal intake

**Migration Path:**
1. Existing `ImmuneService` consumers redirect to `immune_orchestrator` intake
2. Legacy self-protection logic remains for backward compatibility
3. New code uses `immune_orchestrator` directly

### New `immune_orchestrator` Module

**Status:** Canonical decision authority

**Responsibilities:**
- Incident signal ingestion and normalization
- Threat/anomaly classification and prioritization
- Escalation threshold enforcement
- Governance routing for high-risk actions
- Durable decision audit
- Event publication (`immune.decision`)

**Integration Points:**
- `runtime_auditor` → critical anomaly signals
- `system_health` → degradation/critical health signals
- `health_monitor` → service failure signals
- Module adapters → domain-specific failure signals
- `recovery_policy_engine` → recovery action recommendation
- `opencode_repair` → repair ticket creation
- Governance/approval modules → high-risk action approval

---

## Signal Routing

### Normalized IncidentSignal Intake

**Required Fields:**
```python
class IncidentSignal:
    signal_id: UUID
    source: str  # module/component name
    entity_type: str  # skill_run, mission, agent, module, etc.
    entity_id: str
    correlation_id: str
    severity: Literal["info", "warning", "critical"]
    signal_type: str  # anomaly, degradation, failure, threat
    message: str
    technical_details: dict
    occurred_at: datetime
    tenant_id: Optional[str]
```

**Sources (Current):**
- `runtime_auditor` (memory leak, deadlock, cascade failure)
- `system_health` (subsystem critical, aggregate degraded)
- `health_monitor` (service unhealthy)
- `task_queue` adapter (queue stall, worker failure)
- `planning` adapter (planning failure, timeout)
- `neurorail` adapter (enforcement violation, circuit break)

**Sources (Sprint D Expansion):**
- `agent_management` adapter (agent failure, quota breach)
- Module-specific failures via diagnostics framework

### Signal Flow

```
Signal Source
    ↓
immune_orchestrator.ingest_signal()
    ↓
Normalize + Deduplicate + Classify
    ↓
Severity Assessment + Recurrence Check
    ↓
Decision: observe | warn | mitigate | isolate | escalate
    ↓
[if mitigate/isolate/escalate] → recovery_policy_engine.recommend_action()
    ↓
[if requires_governance] → Governance Approval Gate
    ↓
Action Dispatch → opencode_repair | module adapter | containment
    ↓
Audit Record + Event Publish
```

---

## Recovery Policy Engine

### Policy Rules

**Retry Policy:**
- Max retries: 3
- Backoff: exponential (1s, 2s, 4s)
- Cooldown: 60s between retry sequences

**Circuit Break Policy:**
- Threshold: 5 failures in 60s window
- Open duration: 300s
- Half-open test: single probe request

**Isolate Policy:**
- Governance required: YES
- Reversibility: YES (de-isolate action)
- Max blast radius: single entity + dependents

**Rollback Policy:**
- Governance required: YES
- Approval record: `governance_decisions` table link
- Verification: post-rollback health check

**Escalate Policy:**
- Governance required: ALWAYS
- Human approval: REQUIRED for production
- Auto-escalate: only in dev/staging

### Governance Hooks

**High-Risk Actions:**
- `isolate`, `rollback`, `escalate`, `quarantine`

**Approval Requirements:**
- Approval record in `governance_decisions` table
- Approval includes: `decision_id`, `approver_id`, `policy_id`, `approved_at`
- Not just boolean flag or JSON presence

**Bypass Prevention:**
- Service-level validation: approval record must exist and be valid
- API-level enforcement: high-risk endpoints require admin/system-admin role
- Audit trail: all bypass attempts logged as governance violations

---

## Adapter Coverage Matrix

| Module | Status | Adapter Type | Integration Point | Governance |
|--------|--------|--------------|-------------------|------------|
| `immune_orchestrator` | ✅ Complete | Core | N/A | Self |
| `recovery_policy_engine` | ✅ Complete | Core | N/A | Policy enforcement |
| `runtime_auditor` | ✅ Complete | Signal producer | `publish_critical_anomalies()` | Read-only |
| `system_health` | ✅ Complete | Signal producer | Degradation events | Read-only |
| `health_monitor` | ✅ Complete | Signal producer | Service failure events | Read-only |
| `task_queue` | ✅ Complete | Failure adapter | Queue/worker failures | Mitigate |
| `planning` | ✅ Complete | Failure adapter | Planning failures | Retry |
| `neurorail` | ✅ Complete | Enforcement adapter | Violation containment | Isolate |
| `agent_management` | 🔄 Sprint D | Failure adapter | Agent failures | Isolate |
| `opencode_repair` | ✅ Complete | Action sink | Repair ticketing | Approval required |
| `genetic_integrity` | ✅ Complete | Threat producer | DNA violations | Quarantine |
| `genetic_quarantine` | ✅ Complete | Containment | Mutation isolation | Governance required |
| Learning layers (P0-P7) | ⏳ Deferred | Observer-only | Diagnostics framework | Future |

**Legend:**
- ✅ Complete: Fully integrated and tested
- 🔄 Sprint D: In-scope for current sprint
- ⏳ Deferred: Documented, implementation scheduled for future sprint
- ❌ Not Planned: Out of scope

---

## Startup Wiring

### Required EventStream Mode

```python
# backend/main.py (lines ~203-220)

# Wire EventStream into immune/recovery architecture
get_immune_orchestrator_service(event_stream=event_stream)
get_recovery_policy_service(event_stream=event_stream)
get_genetic_integrity_service(event_stream=event_stream)
get_genetic_quarantine_service(event_stream=event_stream)
repair_service = get_opencode_repair_service(event_stream=event_stream)

# Wire repair loop triggers from immune/recovery high-risk outcomes
immune_service = get_immune_orchestrator_service()
recovery_service = get_recovery_policy_service()

async def _repair_trigger(payload: dict) -> None:
    from app.modules.opencode_repair.schemas import RepairAutotriggerRequest
    await repair_service.create_ticket_from_signal(
        RepairAutotriggerRequest(**payload), 
        db=None
    )

immune_service.set_repair_trigger(_repair_trigger)
recovery_service.set_repair_trigger(_repair_trigger)
```

### Degraded Mode Behavior

When EventStream is unavailable (dev/CI degraded mode):
- Immune/recovery services instantiate but signal intake logs warnings
- No durable event publication
- Audit records still written (DB-backed)
- Repair triggers disabled
- Manual recovery only

---

## Audit Chain Requirements

### Correlation ID Propagation

**Every step must preserve correlation_id:**
1. Signal ingestion → `IncidentSignal.correlation_id`
2. Immune decision → `ImmuneDecision.correlation_id`
3. Recovery action → `RecoveryAction.correlation_id`
4. Governance approval → `GovernanceDecision.correlation_id`
5. Repair ticket → `RepairTicket.correlation_id`
6. Action outcome → `ActionOutcome.correlation_id`

### Durable Audit Records

**Required for each stage:**
- Signal: `audit_logging` entry + `immune.signal` event
- Decision: `immune_orchestrator` DB record + `immune.decision` event
- Action: `recovery_policy_engine` DB record + `recovery.action` event
- Governance: `governance_decisions` DB record + `governance.approval` event (if required)
- Outcome: `repair` or adapter-specific record + outcome event

### Event Publication Ordering

**Invariant:** Durable state write → durable audit → event publish

**Failure Handling:**
- Event publish failure does not block state write
- Event publish failures logged and tracked (observability SLO)
- Eventual consistency: events may lag, state is authoritative

---

## Security & Governance

### Authorization Matrix

| Action | Role Required | Governance | Audit |
|--------|---------------|------------|-------|
| Ingest signal | Service-to-service | No | Yes |
| Observe/warn | Operator | No | Yes |
| Mitigate (retry/backoff) | Operator | No | Yes |
| Isolate | Admin | Yes | Yes |
| Rollback | Admin | Yes | Yes |
| Escalate | Admin | Always | Yes |
| Quarantine | System Admin | Always | Yes |

### Tenant Isolation

**All immune/recovery actions are tenant-scoped:**
- Signal ingestion validates `tenant_id` when provided
- Actions cannot cross tenant boundaries
- Cross-tenant signals rejected with `403`
- Audit records include tenant context

### Governance Bypass Prevention

**Enforcement Layers:**
1. **Service Layer:** `recovery_policy_engine.execute_action()` validates approval record
2. **API Layer:** High-risk endpoints require role check via `require_role(SystemRole.ADMIN)`
3. **Audit Layer:** Bypass attempts logged as governance violations
4. **Testing:** Negative tests verify bypass attempts fail with `403`

---

## Verification & Testing

### Test Coverage Requirements

**Immune System Suite:**
- ✅ Signal routing (runtime_auditor → immune, system_health → immune)
- ✅ Decision classification (observe, warn, mitigate, isolate, escalate)
- ✅ Governance gate enforcement (high-risk actions blocked without approval)
- ✅ Audit chain completeness (correlation IDs link all stages)
- ✅ Adapter integration (task_queue, planning, neurorail, agent_management)
- ✅ Bootstrap reliability (startup wiring, degraded mode)

**Negative Tests:**
- ❌ High-risk action without approval → `403 Forbidden`
- ❌ Cross-tenant signal → `403 Forbidden`
- ❌ Missing correlation ID → rejected or generated
- ❌ Circular recovery loop → cooldown enforced

### RC Gate Integration

```bash
# scripts/run_rc_staging_gate.sh

echo "[gate] immune system hardening (Sprint D)"
PYTHONPATH=. pytest \
  tests/test_immune_system.py \
  tests/test_immune_orchestrator.py \
  tests/test_recovery_policy_engine.py \
  -q -x --disable-warnings
```

---

## Migration & Adoption

### Phase 1: Immediate (Sprint D)
- ✅ Document canonical control plane (this spec)
- ✅ Wire runtime_auditor → immune_orchestrator
- ✅ Wire system_health → immune_orchestrator
- 🔄 Add agent_management adapter
- 🔄 Add governance approval enforcement
- 🔄 Add immune system test suite

### Phase 2: Post-Sprint D
- Migrate remaining `ImmuneService` direct calls to orchestrator
- Add learning layer adapters (P0-P7 modules)
- Expand adapter coverage to all high-risk mutating modules
- Add SLO tracking for immune/recovery performance

### Phase 3: Operational Hardening
- Tune policy thresholds based on production metrics
- Add anti-gaming detection for recurrence abuse
- Expand governance approval automation
- Add self-healing integration (Sprint E)

---

## Success Criteria

- ✅ `immune_orchestrator` is documented and enforced canonical decision path
- ✅ Legacy `immune` is subordinated or compatibility-only
- ✅ All critical runtime/health signals flow through unified intake
- ✅ High-risk actions cannot bypass governance routing
- ✅ Incident → Repair/Outcome is auditable with correlation IDs
- ✅ Adapter status documented for all in-scope modules
- ✅ Startup wiring produces consistent immune/recovery graph
- ✅ RC gate includes immune-system verification

---

## Related Documents

- `docs/roadmap/BRAIN_HARDENING_ROADMAP.md` (Sprint D scope)
- `docs/architecture/backend_system_map.md` (immune coverage baseline)
- `docs/specs/canonical_health_model.md` (health signal sources)
- `docs/specs/failure_taxonomy.md` (diagnostics integration)
- `AGENTS.md` (agent execution model for immune agents)
