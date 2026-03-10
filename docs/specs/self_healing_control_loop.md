# Self-Healing Control Loop Specification

**Status**: MVP Foundation (Sprint E)  
**Domain**: Runtime Resilience & Self-Healing  
**Related**: `immune_control_plane.md`, `failure_taxonomy.md`, `canonical_health_model.md`

## Overview

The Self-Healing Control Loop provides automated detection → decision → action → verification for runtime incidents. This spec defines the MVP foundation for autonomous resilience in BRAiN.

## Goals

1. **Close the OODA Loop**: Observe (health/diagnostics) → Orient (immune decisions) → Decide (recovery policy) → Act (healing actions)
2. **Safety-First Execution**: All healing actions execute within strict safety rails and governance boundaries
3. **Verification & Learning**: Track healing effectiveness and build runtime confidence
4. **Minimal Blast Radius**: Start with safe, reversible actions; escalate only when necessary

## Non-Goals (Post-MVP)

- Full autonomous healing for all failure modes (MVP focuses on subset)
- Machine learning-based action selection (deterministic rules for MVP)
- Cross-tenant healing coordination
- Advanced rollback/undo strategies

---

## Architecture

### Control Loop Phases

```
┌─────────────────────────────────────────────────────────┐
│                   OBSERVE (Continuous)                   │
│  - health_monitor: Periodic health checks               │
│  - runtime_auditor: Circuit breaker state               │
│  - observer_core: Timeline anomalies                    │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              ORIENT (Immune Orchestrator)                │
│  - Signal ingestion & prioritization                    │
│  - Blast radius assessment                              │
│  - Recurrence tracking                                  │
│  - Governance routing (ISOLATE/ESCALATE)                │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│         DECIDE (Recovery Policy Engine)                  │
│  - Policy selection based on failure type               │
│  - Cooldown enforcement                                 │
│  - Retry budget calculation                             │
│  - Action plan creation                                 │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│            ACT (Self-Healing Executor) [NEW]            │
│  - Safety rail validation                               │
│  - Action execution with timeout                        │
│  - Rollback on failure                                  │
│  - Audit trail emission                                 │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│           VERIFY (Healing Verifier) [NEW]               │
│  - Post-action health check                             │
│  - Effectiveness scoring                                │
│  - Learning signal emission                             │
│  - Escalation on verification failure                   │
└─────────────────────────────────────────────────────────┘
```

### New Components (Sprint E)

1. **SelfHealingExecutor**: Executes healing actions within safety boundaries
2. **HealingVerifier**: Validates healing effectiveness post-action
3. **SafetyRails**: Pre-execution validation rules
4. **HealingAction Classes**: Typed action definitions (RestartService, ClearCache, etc.)

---

## Component Specifications

### 1. SelfHealingExecutor

**Location**: `backend/app/modules/self_healing/executor.py`

**Responsibilities**:
- Execute healing actions with timeout enforcement
- Apply safety rail validation before execution
- Emit audit/event for every action attempt
- Handle rollback on failure
- Track execution history for recurrence detection

**Interface**:
```python
class SelfHealingExecutor:
    async def execute_action(
        self,
        action: HealingAction,
        context: ExecutionContext,
        db: AsyncSession | None = None
    ) -> ActionResult
```

**Safety Rails** (pre-execution checks):
- Tenant isolation validated
- Cooldown period respected
- Retry budget available
- Blast radius within limits
- Governance approval present (if required)
- No concurrent healing actions on same entity

**Action Types (MVP)**:
1. `RestartServiceAction`: Restart a failed service container
2. `ClearCacheAction`: Clear Redis cache for entity
3. `ResetCircuitBreakerAction`: Reset circuit breaker state
4. `FlushQueueAction`: Clear stuck queue entries
5. `NoOpAction`: Observe-only (no intervention)

### 2. HealingVerifier

**Location**: `backend/app/modules/self_healing/verifier.py`

**Responsibilities**:
- Run post-action health verification
- Score healing effectiveness (0.0-1.0)
- Emit learning signals for policy refinement
- Trigger escalation if verification fails

**Interface**:
```python
class HealingVerifier:
    async def verify_healing(
        self,
        action_result: ActionResult,
        original_signal: IncidentSignal,
        db: AsyncSession | None = None
    ) -> VerificationResult
```

**Verification Checks**:
- Health check passed (via health_monitor)
- Original symptom resolved
- No new incidents introduced (blast radius check)
- Performance metrics within acceptable range

**Effectiveness Scoring**:
- `1.0`: Full recovery, no new issues
- `0.8`: Partial recovery, minor side effects
- `0.5`: Inconclusive, requires monitoring
- `0.2`: Failed, new issues introduced
- `0.0`: Complete failure, rollback required

### 3. SafetyRails

**Location**: `backend/app/modules/self_healing/safety_rails.py`

**Responsibilities**:
- Validate action safety before execution
- Enforce governance boundaries
- Check cooldown periods
- Validate retry budgets

**Rules** (MVP):
```python
@dataclass
class SafetyRails:
    max_concurrent_actions: int = 3  # System-wide
    max_actions_per_entity_per_hour: int = 5
    min_cooldown_seconds: int = 300  # 5 minutes
    max_blast_radius: int = 10
    require_governance_for_blast_radius: int = 5
    
    async def validate_action(
        self,
        action: HealingAction,
        context: ExecutionContext
    ) -> ValidationResult
```

### 4. HealingAction Classes

**Location**: `backend/app/modules/self_healing/actions.py`

**Base Class**:
```python
class HealingAction(BaseModel):
    action_id: str
    action_type: str
    target_entity: str
    correlation_id: str
    blast_radius: int
    estimated_duration_seconds: int
    requires_governance: bool
    rollback_strategy: str | None
    context: Dict[str, Any]
```

**Concrete Actions**:
```python
class RestartServiceAction(HealingAction):
    action_type: Literal["restart_service"] = "restart_service"
    service_name: str
    container_id: str | None
    graceful_shutdown: bool = True

class ClearCacheAction(HealingAction):
    action_type: Literal["clear_cache"] = "clear_cache"
    cache_key_pattern: str
    redis_instance: str = "default"

class ResetCircuitBreakerAction(HealingAction):
    action_type: Literal["reset_circuit_breaker"] = "reset_circuit_breaker"
    circuit_name: str
    
class FlushQueueAction(HealingAction):
    action_type: Literal["flush_queue"] = "flush_queue"
    queue_name: str
    max_items: int = 1000

class NoOpAction(HealingAction):
    action_type: Literal["noop"] = "noop"
```

---

## Data Models

### ExecutionContext

```python
@dataclass
class ExecutionContext:
    tenant_id: str
    actor: str  # "self_healing_executor"
    correlation_id: str
    original_signal: IncidentSignal
    decision: ImmuneDecision
    policy: RecoveryDecision
    timestamp: datetime
    timeout_seconds: int = 60
    dry_run: bool = False
```

### ActionResult

```python
@dataclass
class ActionResult:
    action_id: str
    action_type: str
    status: Literal["success", "failure", "timeout", "skipped"]
    execution_time_ms: int
    error_message: str | None
    context: Dict[str, Any]
    rollback_executed: bool = False
    audit_ref: str | None = None
    event_ref: str | None = None
```

### VerificationResult

```python
@dataclass
class VerificationResult:
    verification_id: str
    action_id: str
    effectiveness_score: float  # 0.0-1.0
    checks_passed: int
    checks_failed: int
    symptom_resolved: bool
    new_incidents_detected: bool
    recommendation: Literal["success", "monitor", "escalate", "rollback"]
    details: Dict[str, Any]
```

---

## Integration Points

### 1. Immune Orchestrator → Self-Healing Executor

**Trigger**: When immune orchestrator creates ISOLATE or ESCALATE decision

```python
# In immune_orchestrator/service.py
if decision.requires_governance_hook and self._repair_trigger:
    await self._repair_trigger({
        "source_module": "immune_orchestrator",
        "signal_id": signal.id,
        "decision_id": decision.decision_id,
        "correlation_id": signal.correlation_id,
        ...
    })
```

**Repair Trigger Handler** (new):
```python
# In self_healing/orchestrator.py
async def handle_repair_request(request: dict) -> None:
    # 1. Fetch recovery policy
    policy = await recovery_policy_engine.decide_recovery(...)
    
    # 2. Build healing action
    action = build_action_from_policy(policy)
    
    # 3. Execute with safety rails
    result = await executor.execute_action(action, context)
    
    # 4. Verify healing
    verification = await verifier.verify_healing(result, signal)
    
    # 5. Emit learning signal
    await emit_learning_signal(verification)
```

### 2. Recovery Policy Engine → Healing Actions

**Mapping**:
```python
# RecoveryAction → HealingAction
"restart_service" → RestartServiceAction
"clear_cache" → ClearCacheAction
"reset_breaker" → ResetCircuitBreakerAction
"flush_queue" → FlushQueueAction
"noop" → NoOpAction
```

### 3. Health Monitor → Verification

**Post-Action Check**:
```python
# After healing action execution
health_status = await health_monitor.check_entity_health(
    entity_id=action.target_entity,
    check_types=["database", "redis", "http"]
)

if health_status.status == "healthy":
    effectiveness_score = 1.0
elif health_status.status == "degraded":
    effectiveness_score = 0.5
else:
    effectiveness_score = 0.0
```

---

## Audit & Event Contract

### Audit Records

**Action Execution**:
```python
await write_unified_audit(
    event_type="self_healing.action.executed",
    action=action.action_type,
    actor="self_healing_executor",
    actor_type="system",
    resource_type="healing_action",
    resource_id=action.action_id,
    severity="info" if result.status == "success" else "warning",
    message=f"Healing action {action.action_type} executed: {result.status}",
    correlation_id=action.correlation_id,
    details={
        "target_entity": action.target_entity,
        "blast_radius": action.blast_radius,
        "execution_time_ms": result.execution_time_ms,
        "decision_id": context.decision.decision_id,
        "signal_id": context.original_signal.id,
    },
    db=db
)
```

**Verification Completion**:
```python
await write_unified_audit(
    event_type="self_healing.verification.completed",
    action="verify_healing",
    actor="healing_verifier",
    actor_type="system",
    resource_type="verification_result",
    resource_id=verification.verification_id,
    severity="info" if verification.symptom_resolved else "warning",
    message=f"Healing verification: {verification.recommendation}",
    correlation_id=action.correlation_id,
    details={
        "effectiveness_score": verification.effectiveness_score,
        "symptom_resolved": verification.symptom_resolved,
        "new_incidents": verification.new_incidents_detected,
    },
    db=db
)
```

### Event Stream

**Action Executed Event**:
```python
payload = build_runtime_event_payload(
    event_type="self_healing.action.executed",
    severity=EventSeverity.INFO,
    source="self_healing_executor",
    entity=action.target_entity,
    correlation_id=action.correlation_id,
    data={
        "action_id": action.action_id,
        "action_type": action.action_type,
        "status": result.status,
        "blast_radius": action.blast_radius,
    }
)
```

---

## Error Handling

### Execution Failures

**Timeout**:
- Action exceeds `timeout_seconds`
- Status: `timeout`
- Rollback attempted if `rollback_strategy` defined
- Escalate to governance layer

**Safety Rail Violation**:
- Action fails pre-execution validation
- Status: `skipped`
- Audit emitted with violation details
- No execution attempted

**Action Failure**:
- Execution raises exception
- Status: `failure`
- Rollback attempted
- Error logged with full stack trace
- Escalate if critical entity

### Verification Failures

**Health Check Failed Post-Action**:
- `effectiveness_score`: `0.0`
- `recommendation`: `rollback`
- Trigger rollback action if available
- Escalate to immune orchestrator

**New Incidents Introduced**:
- `new_incidents_detected`: `true`
- `recommendation`: `escalate`
- Immediate escalation to governance layer
- No further healing actions on entity (cooldown extended)

---

## Safety Boundaries

### Cooldown Enforcement

```python
# Check last action timestamp
last_action = await get_last_action_for_entity(entity_id, db)
if last_action:
    elapsed = (now - last_action.timestamp).total_seconds()
    if elapsed < min_cooldown_seconds:
        return ValidationResult(
            valid=False,
            reason=f"Cooldown active: {min_cooldown_seconds - elapsed}s remaining"
        )
```

### Concurrent Action Limit

```python
# Check system-wide concurrent actions
active_actions = await get_active_actions(db)
if len(active_actions) >= max_concurrent_actions:
    return ValidationResult(
        valid=False,
        reason="System-wide concurrent action limit reached"
    )
```

### Blast Radius Gate

```python
if action.blast_radius > max_blast_radius:
    return ValidationResult(
        valid=False,
        reason=f"Blast radius {action.blast_radius} exceeds limit {max_blast_radius}"
    )

if action.blast_radius >= require_governance_for_blast_radius:
    if not context.decision.requires_governance_hook:
        return ValidationResult(
            valid=False,
            reason="Governance approval required for blast radius"
        )
```

---

## MVP Scope

### In Scope (Sprint E)

1. ✅ **Core Components**:
   - SelfHealingExecutor (with safety rails)
   - HealingVerifier (with effectiveness scoring)
   - SafetyRails (validation rules)
   - 5 HealingAction classes

2. ✅ **Integration**:
   - Wire immune_orchestrator → SelfHealingExecutor
   - Wire RecoveryPolicyEngine → action selection
   - Wire health_monitor → verification

3. ✅ **Audit/Event Coverage**:
   - Action execution audit
   - Verification audit
   - Event stream integration

4. ✅ **Testing**:
   - Unit tests for each action type
   - Safety rail validation tests
   - End-to-end healing flow test
   - Verification scoring tests

### Out of Scope (Post-MVP)

- Advanced rollback strategies (beyond simple undo)
- Machine learning-based action selection
- Multi-action orchestration (workflows)
- Cross-tenant healing coordination
- Advanced learning/feedback loops (observability only)
- UI for healing action approval/review

---

## Testing Strategy

### Unit Tests

1. **Action Execution**:
   - Each action type executes successfully
   - Timeout enforcement works
   - Rollback triggers on failure

2. **Safety Rails**:
   - Cooldown period enforced
   - Concurrent action limit enforced
   - Blast radius validation works
   - Governance requirement enforced

3. **Verification**:
   - Effectiveness scoring accurate
   - Health check integration works
   - Escalation triggers correctly

### Integration Tests

1. **End-to-End Healing Flow**:
   - Signal → Decision → Policy → Action → Verification
   - Correlation ID propagates through entire flow
   - Audit chain complete

2. **Failure Scenarios**:
   - Action timeout → rollback
   - Verification failure → escalation
   - Safety rail violation → skipped execution

### Contract Tests

1. **Audit Completeness**: Every action produces audit record
2. **Event Emission**: Every action produces event
3. **Correlation Propagation**: correlation_id preserved end-to-end

---

## Success Criteria

### Functional

- [ ] All 5 action types executable
- [ ] Safety rails block unsafe actions
- [ ] Verification scores healing effectiveness
- [ ] Audit/event coverage complete
- [ ] End-to-end healing flow works

### Non-Functional

- [ ] Action execution < 60s (timeout enforced)
- [ ] Safety rail validation < 100ms
- [ ] Verification check < 10s
- [ ] Zero unhandled exceptions in executor
- [ ] 100% audit coverage for actions

### Testing

- [ ] 40+ tests passing
- [ ] RC gate green with self-healing suite
- [ ] No new silent-fail patterns introduced

---

## Migration Path

### Phase 1 (Sprint E - MVP)

1. Create self_healing module structure
2. Implement executor + verifier + safety_rails
3. Define 5 action classes
4. Wire immune_orchestrator → executor
5. Add comprehensive test suite
6. Update RC gate

### Phase 2 (Post-Sprint E)

1. Add more action types (based on incident patterns)
2. Implement advanced rollback strategies
3. Build learning/feedback loop
4. Add governance UI for action approval
5. Implement multi-action workflows

---

## Open Questions

1. **Rollback Strategy**: Should we implement compensating transactions or snapshots?
   - **MVP Decision**: Simple undo actions only (e.g., restart → no-op, clear_cache → no rollback)

2. **Dry Run Mode**: Should we support dry-run mode for testing?
   - **MVP Decision**: Yes, add `dry_run` flag to ExecutionContext

3. **Governance Approval Flow**: How do we handle async approval for high-blast-radius actions?
   - **MVP Decision**: Block execution until approval present; emit event for governance layer to act

4. **Learning Signal Format**: What format for learning signals to feed back into policy refinement?
   - **MVP Decision**: Structured VerificationResult; post-MVP will build learning loop

---

## References

- **Immune Control Plane**: `docs/specs/immune_control_plane.md`
- **Failure Taxonomy**: `docs/specs/failure_taxonomy.md`
- **Health Model**: `docs/specs/canonical_health_model.md`
- **Recovery Policy Engine**: `backend/app/modules/recovery_policy_engine/`
- **Immune Orchestrator**: `backend/app/modules/immune_orchestrator/`
