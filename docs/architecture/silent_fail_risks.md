# False Green / Silent Fail Risk Register

**Version:** 1.0  
**Date:** 2026-03-10  
**Sprint:** A - Backend Grounding Audit  
**Purpose:** Catalog of all known placeholders, fallback-to-ok patterns, missing telemetry, and conflicting health route semantics with file:line references.

---

## Executive Summary

This register identifies **23 critical silent-fail patterns** across the BRAiN backend that create "false green" operational risk:

- **6 fallback-to-ok patterns** where exceptions return success status
- **8 placeholder implementations** that always return healthy/success
- **5 missing telemetry gaps** where critical failures go undetected
- **4 conflicting health route semantics** creating operational ambiguity

**Critical Impact:** Operators cannot trust health status. Immune system may not trigger on actual failures. Learning layer mutations fail silently. Audit records lost without alerts.

---

## 1. Fallback-to-OK Patterns (FALSE GREEN RISK)

### 1.1 Legacy Health Endpoint Returns OK on Exception

**Severity:** CRITICAL  
**Impact:** Health check reports `status: "ok"` even when system_health service fails  
**Detection:** None - operators see false green  
**Blast Radius:** All monitoring/alerting that relies on `/api/health`

**Code:**
```python
# backend/app/api/routes/health.py:42-57
try:
    summary = await service.get_health_summary()
    return {
        "status": "ok" if summary.status.value != "critical" else "degraded",
        "timestamp": summary.timestamp.isoformat(),
        "message": summary.message,
        "enhanced_health_endpoint": "/api/system/health",
    }
except Exception as e:
    # Fallback to simple response
    return {
        "status": "ok",  # ← FALSE GREEN
        "error": str(e),
        "enhanced_health_endpoint": "/api/system/health",
    }
```

**File Reference:** `backend/app/api/routes/health.py:42-57`

**Remediation:** Return `status: "unknown"` or `status: "degraded"` on exception, not `"ok"`

---

### 1.2 System Health Aggregator Silent Fail on Subsystem Unavailability

**Severity:** HIGH  
**Impact:** System health returns partial/stale data when immune/threats/mission subsystems fail  
**Detection:** Logged as warning, but aggregator continues  
**Blast Radius:** Health status summary incomplete

**Code:**
```python
# backend/app/modules/system_health/service.py:191-214
async def _get_immune_health(self) -> Optional[ImmuneHealthData]:
    if not self.immune_service:
        return None
    try:
        summary = self.immune_service.health_summary(minutes=60)
        # ... return ImmuneHealthData
    except Exception as e:
        logger.error(f"[SystemHealth] Failed to get immune health: {e}")
        return None  # ← Aggregator continues with None, may report healthy

# Similar pattern in:
# - _get_threats_health (backend/app/modules/system_health/service.py:216-225)
# - _get_mission_health (backend/app/modules/system_health/service.py:227-242)
```

**File References:**
- `backend/app/modules/system_health/service.py:191-214` (immune)
- `backend/app/modules/system_health/service.py:216-225` (threats)
- `backend/app/modules/system_health/service.py:227-242` (missions)

**Remediation:** Return explicit `unknown` or `degraded` status when subsystem health unavailable, propagate to overall status

---

### 1.3 EventStream Publish Failure Silent Degradation

**Severity:** HIGH  
**Impact:** Events dropped silently when EventStream unavailable or Redis down  
**Detection:** Logged only, no alerting, no retry  
**Blast Radius:** Audit trail gaps, immune system blind to anomalies, observer layer incomplete

**Code:**
```python
# backend/app/modules/course_factory/service.py:856-867
async def _publish_event_safe(self, event: Event) -> None:
    if self.event_stream is None:
        logger.debug("[CourseFactory] EventStream not available, skipping event publish")
        return  # ← Event lost, silent
    try:
        await self.event_stream.publish_event(event)
    except Exception as e:
        logger.error(f"[CourseFactory] Failed to publish event: {e}")
        # ← Event lost, no retry, no alert

# Similar pattern in:
# - ir_governance/validator.py:65-86
# - ir_governance/diff_audit.py:55-76
# - dna/core/service.py:74-136
# - task_queue/service.py:50-56
# - agent_management/service.py:43-49
# - memory/store.py:207-217
```

**File References:**
- `backend/app/modules/course_factory/service.py:856-867`
- `backend/app/modules/ir_governance/validator.py:65-86`
- `backend/app/modules/ir_governance/diff_audit.py:55-76`
- `backend/app/modules/dna/core/service.py:74-136`
- `backend/app/modules/task_queue/service.py:50-56`
- `backend/app/modules/agent_management/service.py:43-49`
- `backend/app/modules/memory/store.py:207-217`

**Remediation:** Implement circuit breaker, alert on event loss, consider fallback to direct DB audit on EventStream failure

---

### 1.4 Audit Bridge Implicit DB Mode Skips Audit Writes

**Severity:** HIGH  
**Impact:** Audit writes skipped when `BRAIN_AUDIT_BRIDGE_IMPLICIT_DB=false` and no explicit db session provided  
**Detection:** Debug log only, audit records missing  
**Blast Radius:** Compliance gap, governance decisions not durably recorded

**Code:**
```python
# backend/app/core/audit_bridge.py:44-57
async def write_unified_audit(..., db: AsyncSession | None = None) -> None:
    try:
        service = get_audit_service()
        if db is not None:
            await service.log_event(db, payload)
            return
        
        implicit_db = os.getenv("BRAIN_AUDIT_BRIDGE_IMPLICIT_DB", "false").lower() == "true"
        if not implicit_db:
            logger.debug("[AuditBridge] skipped implicit DB session for event_type=%s", event_type)
            return  # ← Audit write skipped, silent
        
        async with AsyncSessionLocal() as temp_db:
            await service.log_event(temp_db, payload)
    except Exception as exc:
        logger.error("[AuditBridge] failed to write audit event: %s", exc)
        # ← Audit write failed, no alert
```

**File Reference:** `backend/app/core/audit_bridge.py:44-57`

**Remediation:** Default `BRAIN_AUDIT_BRIDGE_IMPLICIT_DB=true` in production, alert on audit write failures

---

### 1.5 Health Monitor Placeholder Checks Always Return HEALTHY

**Severity:** CRITICAL  
**Impact:** Service health checks always report healthy regardless of actual state  
**Detection:** None - false green  
**Blast Radius:** Health monitor status unreliable, operators cannot detect subsystem failures

**Code:**
```python
# backend/app/modules/health_monitor/service.py:242-284
async def _perform_health_check(self, service: HealthCheckModel) -> HealthCheckResult:
    start = time.time()
    try:
        if service.service_type == "database":
            # Database check would be done here
            # For now, just return healthy
            status = HealthStatus.HEALTHY  # ← PLACEHOLDER
            error = None
        elif service.service_type == "cache":
            # Cache check
            status = HealthStatus.HEALTHY  # ← PLACEHOLDER
            error = None
        elif service.service_type == "external":
            # External API check
            status = HealthStatus.HEALTHY  # ← PLACEHOLDER
            error = None
        else:
            # Internal service
            status = HealthStatus.HEALTHY  # ← PLACEHOLDER
            error = None
        
        response_time = (time.time() - start) * 1000
        return HealthCheckResult(
            service_name=service.service_name,
            status=status,
            response_time_ms=response_time,
            error_message=error,
            output="Check passed"
        )
    except Exception as e:
        return HealthCheckResult(
            service_name=service.service_name,
            status=HealthStatus.UNHEALTHY,
            response_time_ms=(time.time() - start) * 1000,
            error_message=str(e),
            output="Check failed"
        )
```

**File Reference:** `backend/app/modules/health_monitor/service.py:242-284`

**Remediation:** Implement actual health checks for database (ping), cache (Redis ping), external (HTTP probe), internal (module-specific)

---

### 1.6 System Health Placeholder Threats Data

**Severity:** MEDIUM  
**Impact:** Threats health always reports zero threats, masking actual threat state  
**Detection:** Code comment indicates placeholder  
**Blast Radius:** Threat visibility gap in system health aggregation

**Code:**
```python
# backend/app/modules/system_health/service.py:216-225
async def _get_threats_health(self) -> Optional[ThreatsHealthData]:
    """Get health data from Threats System"""
    # TODO: Implement when ThreatsService API is available
    # For now, return mock data
    return ThreatsHealthData(
        total_threats=0,  # ← PLACEHOLDER
        active_threats=0,  # ← PLACEHOLDER
        critical_threats=0,  # ← PLACEHOLDER
        mitigated_threats=0,  # ← PLACEHOLDER
    )
```

**File Reference:** `backend/app/modules/system_health/service.py:216-225`

**Remediation:** Wire actual ThreatsService API when available, or return `None` to indicate unavailable

---

## 2. Placeholder Implementations (INCOMPLETE FUNCTIONALITY)

### 2.1 Runtime Auditor Edge-of-Chaos Metric Incomplete

**Severity:** MEDIUM  
**Impact:** Edge-of-chaos score calculation missing agent utilization variance  
**Detection:** Code TODO comment  
**Blast Radius:** Incomplete system stability assessment

**Code:**
```python
# backend/app/modules/runtime_auditor/service.py:365-411
def _get_edge_of_chaos_metrics(self) -> EdgeOfChaosMetrics:
    # ... calculation logic ...
    return EdgeOfChaosMetrics(
        score=score,
        entropy=entropy,
        synchronicity_index=synchronicity,
        agent_utilization_variance=None,  # TODO: Calculate from agent metrics ← PLACEHOLDER
        assessment=assessment,
    )
```

**File Reference:** `backend/app/modules/runtime_auditor/service.py:365-411`

**Remediation:** Integrate with agent_management metrics to calculate utilization variance

---

### 2.2 Agent Health Runtime State Tracking Not Implemented

**Severity:** MEDIUM  
**Impact:** Agent health always reports 0 active/idle agents  
**Detection:** Code comment indicates missing implementation  
**Blast Radius:** System health aggregation lacks agent runtime visibility

**Code:**
```python
# backend/app/modules/system_health/service.py:244-262
async def _get_agent_health(self) -> Optional[AgentHealthData]:
    try:
        from app.api.routes.agents import AGENTS
        total = len(AGENTS)
        
        # Runtime state tracking not yet implemented
        # This would require tracking which agents are actively executing missions
        return AgentHealthData(
            total_agents=total,
            active_agents=0,  # Requires runtime state tracking ← PLACEHOLDER
            idle_agents=0,    # Requires runtime state tracking ← PLACEHOLDER
        )
    except Exception as e:
        logger.error(f"Failed to get agent health: {e}")
        return None
```

**File Reference:** `backend/app/modules/system_health/service.py:244-262`

**Remediation:** Integrate with agent_management service to track active/idle state from heartbeat signals

---

### 2.3 Runtime Auditor Latency/Queue Sampling Not Wired

**Severity:** HIGH  
**Impact:** Runtime auditor cannot detect latency spikes or queue saturation  
**Detection:** Code TODO comments  
**Blast Radius:** Anomaly detection incomplete, immune system blind to performance degradation

**Code:**
```python
# backend/app/modules/runtime_auditor/service.py:175-186
async def _collect_metrics(self):
    logger.debug("[RuntimeAuditor] Collecting metrics...")
    
    if self.process:
        memory_mb = self._get_memory_usage_mb()
        self.memory_samples.append(memory_mb)
    
    # TODO: Collect latency samples from API endpoints ← MISSING
    # TODO: Collect queue depth from mission system ← MISSING
    # For now, these will be populated when integrated
```

**File Reference:** `backend/app/modules/runtime_auditor/service.py:175-186`

**Remediation:** Wire latency sampling middleware into FastAPI request lifecycle, integrate with task_queue for depth sampling

---

### 2.4 Runtime Auditor Not Wired into Startup

**Severity:** CRITICAL  
**Impact:** Continuous runtime monitoring completely inactive, no anomaly detection, no immune signal publishing  
**Detection:** Missing from `backend/main.py` startup sequence  
**Blast Radius:** Entire runtime auditor subsystem non-functional

**Code:**
```python
# backend/main.py:156-304 (startup lifespan)
# EventStream wired (line 184-248)
# Immune/recovery wired (line 204-220)
# Mission worker wired (line 252-257)
# Metrics collector wired (line 260-263)
# Autoscaler wired (line 266-269)
# RuntimeAuditor NOT WIRED ← MISSING

# Runtime auditor defines background loop:
# backend/app/modules/runtime_auditor/service.py:131-154
async def start(self):
    if self.running:
        logger.warning("[RuntimeAuditor] Already running")
        return
    self.running = True
    self.task = asyncio.create_task(self._collection_loop())
    logger.info("[RuntimeAuditor] Background collection started")
```

**File References:**
- Missing wiring: `backend/main.py:156-304`
- Service implementation: `backend/app/modules/runtime_auditor/service.py:131-154`

**Remediation:** Add runtime_auditor startup wiring in `backend/main.py` lifespan, publish anomalies to immune_orchestrator

---

### 2.5 Learning Layer Correlation ID Capture Missing

**Severity:** HIGH  
**Impact:** Learning layer mutations (P0-P7) cannot be traced back to source SkillRun  
**Detection:** Schema inspection - no correlation_id fields  
**Blast Radius:** Provenance chain broken, incident timeline reconstruction impossible

**Code (Example - Experience Layer):**
```python
# backend/app/modules/experience_layer/service.py
# ExperienceRecord model likely has skill_run_id but no explicit correlation_id field
# No correlation ID propagation in service methods

# Similar gap across all learning layers:
# - insight_layer
# - consolidation_layer
# - evolution_control
# - deliberation_layer
# - discovery_layer
# - economy_layer
```

**File References:**
- `backend/app/modules/experience_layer/service.py`
- `backend/app/modules/insight_layer/service.py`
- `backend/app/modules/consolidation_layer/service.py`
- `backend/app/modules/evolution_control/service.py`
- `backend/app/modules/deliberation_layer/service.py`
- `backend/app/modules/discovery_layer/service.py`
- `backend/app/modules/economy_layer/service.py`

**Remediation:** Add `correlation_id` field to all learning layer schemas, propagate from SkillRun ID through all layers

---

### 2.6 Governance Decision Audit Trail Missing

**Severity:** CRITICAL  
**Impact:** Approve/reject decisions in learning layers (P4, P6, P7) not durably audited  
**Detection:** No `write_unified_audit` calls in service methods  
**Blast Radius:** Compliance gap, governance decisions not traceable

**Code (Example - Evolution Control):**
```python
# backend/app/modules/evolution_control/service.py
# approve_proposal and reject_proposal methods update DB directly
# No write_unified_audit calls
# No audit_bridge usage

# Similar gap in:
# - discovery_layer (skill proposal approve/reject)
# - economy_layer (assessment approve/reject)
```

**File References:**
- `backend/app/modules/evolution_control/service.py`
- `backend/app/modules/discovery_layer/service.py`
- `backend/app/modules/economy_layer/service.py`

**Remediation:** Add `write_unified_audit` calls for all governance decisions with approval context

---

### 2.7 Built-in Skill Seeding Error Handling

**Severity:** LOW  
**Impact:** Skill seeding failures logged but not surfaced to operators  
**Detection:** Warning log only  
**Blast Radius:** Skills may be missing from registry without operator awareness

**Code:**
```python
# backend/main.py:272-279
if _feature_enabled("ENABLE_BUILTIN_SKILL_SEED", "true"):
    try:
        from app.modules.skills.builtins_seeder import seed_builtin_skills
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await seed_builtin_skills(db)
    except Exception as e:
        logger.warning(f"⚠️ Could not seed built-in skills: {e}")
        # ← Failure silent, startup continues
```

**File Reference:** `backend/main.py:272-279`

**Remediation:** Fail startup on skill seeding error in required mode, or expose seeding status in health endpoint

---

### 2.8 Legacy Supervisor Router Optional Availability

**Severity:** LOW  
**Impact:** Legacy supervisor routes may be unavailable without operator awareness  
**Detection:** Warning log only  
**Blast Radius:** Legacy API consumers may fail without clear error

**Code:**
```python
# backend/main.py:428-440
if os.getenv("ENABLE_LEGACY_SUPERVISOR_ROUTER", "false").lower() == "true":
    try:
        from app.compat.legacy_supervisor import get_legacy_supervisor_router
        app.include_router(
            get_legacy_supervisor_router(),
            prefix="/api",
            tags=["legacy-supervisor"],
        )
    except Exception as e:
        logger.warning(f"⚠️ Legacy supervisor router unavailable: {e}")
        # ← Router not included, silent
```

**File Reference:** `backend/main.py:428-440`

**Remediation:** Expose router availability in debug/health endpoints, or fail startup if required

---

## 3. Missing Telemetry Gaps

### 3.1 HTTP Request Latency Sampling Not Implemented

**Severity:** HIGH  
**Impact:** Runtime auditor cannot detect latency anomalies  
**Detection:** Code TODO comment  
**Blast Radius:** Performance degradation undetected

**Code:**
```python
# backend/app/modules/runtime_auditor/service.py:188-197
def sample_latency(self, latency_ms: float):
    """
    Record a latency sample.
    
    This should be called by API endpoints to track request latency.
    
    Args:
        latency_ms: Request latency in milliseconds
    """
    self.latency_samples.append(latency_ms)

# ← NOT WIRED: No middleware calls this method
```

**File Reference:** `backend/app/modules/runtime_auditor/service.py:188-197`

**Remediation:** Add FastAPI middleware to measure request latency and call `runtime_auditor.sample_latency()`

---

### 3.2 Mission Queue Depth Sampling Not Implemented

**Severity:** HIGH  
**Impact:** Runtime auditor cannot detect queue saturation or deadlock  
**Detection:** Code TODO comment  
**Blast Radius:** Queue bottlenecks undetected

**Code:**
```python
# backend/app/modules/runtime_auditor/service.py:199-208
def sample_queue_depth(self, depth: int):
    """
    Record a queue depth sample.
    
    This should be called by mission system to track queue depth.
    
    Args:
        depth: Current queue depth
    """
    self.queue_depth_samples.append(depth)

# ← NOT WIRED: Task queue does not publish depth samples
```

**File Reference:** `backend/app/modules/runtime_auditor/service.py:199-208`

**Remediation:** Wire task_queue to publish depth samples to runtime_auditor on create/claim/complete operations

---

### 3.3 Database Connection Pool Metrics Not Exposed

**Severity:** MEDIUM  
**Impact:** Cannot detect DB connection exhaustion before failures occur  
**Detection:** No structured telemetry  
**Blast Radius:** DB failures appear sudden without warning

**Remediation:** Expose AsyncSession pool metrics (active connections, wait time, errors) to health monitor

---

### 3.4 Redis Connection Pool Metrics Not Exposed

**Severity:** MEDIUM  
**Impact:** Cannot detect Redis degradation before EventStream failures  
**Detection:** No structured telemetry  
**Blast Radius:** EventStream failures appear sudden

**Remediation:** Expose Redis pool metrics to health monitor, track connection errors

---

### 3.5 External API Call Success/Failure Rates Not Tracked

**Severity:** MEDIUM  
**Impact:** Cannot detect integration failures or provider degradation  
**Detection:** Scattered logging only  
**Blast Radius:** Integration issues discovered through user reports

**Remediation:** Centralize external API call telemetry, publish to health monitor or runtime auditor

---

## 4. Conflicting Health Route Semantics

### 4.1 Three Health Route Families with Overlapping Scope

**Severity:** HIGH  
**Impact:** Operational confusion about canonical health endpoint  
**Detection:** Code inspection, documentation gaps  
**Blast Radius:** Monitoring/alerting may use inconsistent endpoints

**Routes:**
1. **`/api/health`** (legacy) - Simple status, deprecated but still active
2. **`/api/health/*`** (health_monitor) - Service-level checks, EventStream integration
3. **`/api/system/health`** (system_health) - System-wide aggregation

**File References:**
- Legacy: `backend/app/api/routes/health.py:25-57`
- Health Monitor: `backend/app/modules/health_monitor/router.py`
- System Health: `backend/app/modules/system_health/router.py`

**Conflicts:**
- No documented canonical endpoint
- Legacy route returns `ok` on exception (false green)
- Health monitor has placeholder checks (false green)
- System health aggregates but allows subsystem failures to return `None` (partial data)

**Remediation:** Designate `/api/system/health` as canonical, deprecate `/api/health` with sunset headers, document health_monitor as internal service-level API

---

### 4.2 Health Status Vocabulary Inconsistency

**Severity:** MEDIUM  
**Impact:** Different status values across health surfaces  
**Detection:** Code inspection  
**Blast Radius:** Parsing/alerting logic must handle multiple vocabularies

**Vocabularies:**
1. **Legacy `/api/health`:** `"ok"`, `"degraded"`
2. **Health Monitor:** `HEALTHY`, `DEGRADED`, `UNHEALTHY`, `UNKNOWN` (HealthStatus enum)
3. **System Health:** `HEALTHY`, `DEGRADED`, `CRITICAL`, `UNKNOWN` (HealthStatus enum)

**File References:**
- Legacy: `backend/app/api/routes/health.py:45`
- Health Monitor: `backend/app/modules/health_monitor/models.py` (HealthStatus enum)
- System Health: `backend/app/modules/system_health/schemas.py` (HealthStatus enum)

**Conflicts:**
- Legacy uses lowercase strings, new uses uppercase enum
- `UNHEALTHY` vs `CRITICAL` naming inconsistency

**Remediation:** Standardize on single HealthStatus enum: `healthy`, `degraded`, `critical`, `unknown`, `stale`

---

### 4.3 Health Check Threshold Semantics Unclear

**Severity:** MEDIUM  
**Impact:** Operators cannot predict when status will transition  
**Detection:** Code inspection  
**Blast Radius:** Health status transitions appear arbitrary

**Thresholds (health_monitor):**
```python
# backend/app/modules/health_monitor/service.py:113-120
if check.consecutive_failures >= 3:
    new_status = HealthStatus.UNHEALTHY
elif check.consecutive_failures >= 1:
    new_status = HealthStatus.DEGRADED
elif check.consecutive_successes >= 2:
    new_status = HealthStatus.HEALTHY
else:
    new_status = HealthStatus.UNKNOWN
```

**Issues:**
- Hardcoded thresholds not configurable
- `UNKNOWN` state logic unclear (when does this occur?)
- Transition from `DEGRADED` to `HEALTHY` requires 2 successes, asymmetric with degradation (1 failure)

**File Reference:** `backend/app/modules/health_monitor/service.py:113-120`

**Remediation:** Document threshold rationale, make configurable, ensure symmetric degradation/recovery logic

---

### 4.4 EventStream Mode Degraded Behavior Undefined

**Severity:** HIGH  
**Impact:** Immune/recovery system not wired in degraded mode, creating safety gap  
**Detection:** Code inspection  
**Blast Radius:** Non-production environments lack governance safeguards

**Code:**
```python
# backend/main.py:229-248
elif eventstream_mode == "degraded":
    # DEGRADED MODE: EventStream disabled, explicit log
    logger.warning(
        "⚠️ DEGRADED MODE: EventStream disabled. "
        "This violates ADR-001 and should ONLY be used in Dev/CI."
    )
    event_stream = None
    app.state.event_stream = None
    # ← Immune/recovery NOT wired when EventStream None
```

**File Reference:** `backend/main.py:229-248`

**Consequences:**
- Immune orchestrator not initialized
- Recovery policy engine not initialized
- Repair trigger callbacks not set
- Genetic integrity/quarantine services initialized but non-functional

**Remediation:** Document degraded mode behavior explicitly, fail startup in staging/production if degraded mode detected

---

## 5. Risk Mitigation Priority Matrix

| Risk ID | Pattern | Severity | Detectability | Remediation Effort | Priority |
|---------|---------|----------|---------------|-------------------|----------|
| 1.1 | Legacy health fallback-to-ok | CRITICAL | None | Low | **P0** |
| 1.5 | Health monitor placeholder checks | CRITICAL | None | Medium | **P0** |
| 2.4 | Runtime auditor not wired | CRITICAL | Missing logs | Low | **P0** |
| 2.6 | Governance decision audit gap | CRITICAL | Audit query | High | **P0** |
| 1.3 | EventStream publish silent fail | HIGH | Logs only | Medium | **P1** |
| 1.4 | Audit bridge implicit mode skip | HIGH | Debug logs | Low | **P1** |
| 2.5 | Learning layer correlation ID gap | HIGH | None | High | **P1** |
| 3.1 | Latency sampling not wired | HIGH | None | Medium | **P1** |
| 3.2 | Queue depth sampling not wired | HIGH | None | Medium | **P1** |
| 4.1 | Conflicting health route semantics | HIGH | Docs/code | High | **P1** |
| 4.4 | Degraded mode undefined behavior | HIGH | Warning log | Medium | **P1** |
| 1.2 | System health subsystem silent fail | HIGH | Logs only | Medium | **P2** |
| 1.6 | Threats health placeholder | MEDIUM | Code comment | Medium | **P2** |
| 2.1 | Edge-of-chaos metric incomplete | MEDIUM | Code comment | Medium | **P2** |
| 2.2 | Agent health state tracking missing | MEDIUM | Code comment | High | **P2** |
| 2.3 | Runtime auditor sampling gaps | HIGH | Code comment | Medium | **P2** |
| 3.3 | DB pool metrics not exposed | MEDIUM | None | Medium | **P2** |
| 3.4 | Redis pool metrics not exposed | MEDIUM | None | Medium | **P2** |
| 3.5 | External API telemetry missing | MEDIUM | Scattered logs | High | **P2** |
| 4.2 | Health status vocabulary conflict | MEDIUM | Code inspection | Medium | **P2** |
| 4.3 | Health threshold semantics unclear | MEDIUM | Code inspection | Low | **P3** |
| 2.7 | Skill seeding error silent | LOW | Warning log | Low | **P3** |
| 2.8 | Legacy router optional silent | LOW | Warning log | Low | **P3** |

---

## 6. Sprint B (Health System Hardening) Priority Targets

Based on this risk register, Sprint B should immediately address:

### P0 (Blocking Production Reliability)

1. **Fix legacy health fallback-to-ok (1.1)**
   - File: `backend/app/api/routes/health.py:54`
   - Change: Return `status: "unknown"` on exception, not `"ok"`
   - Effort: 1 hour

2. **Replace health monitor placeholder checks (1.5)**
   - File: `backend/app/modules/health_monitor/service.py:242-284`
   - Change: Implement actual DB/Redis/external checks
   - Effort: 1-2 days

3. **Wire runtime auditor into startup (2.4)**
   - File: `backend/main.py:156-304`
   - Change: Add runtime_auditor initialization and start after EventStream
   - Effort: 2-4 hours

4. **Add governance decision audit trail (2.6)**
   - Files: `backend/app/modules/evolution_control/service.py`, `backend/app/modules/discovery_layer/service.py`, `backend/app/modules/economy_layer/service.py`
   - Change: Add `write_unified_audit` calls to approve/reject methods
   - Effort: 1 day

### P1 (Required for Sprint C/D Foundations)

5. **Implement EventStream publish circuit breaker (1.3)**
   - Files: All modules using `_publish_event_safe` pattern
   - Change: Track consecutive failures, alert on circuit open, consider fallback to direct audit
   - Effort: 2-3 days

6. **Enable audit bridge implicit mode by default (1.4)**
   - File: `backend/app/core/audit_bridge.py:49`
   - Change: Default `BRAIN_AUDIT_BRIDGE_IMPLICIT_DB=true`, alert on audit write failures
   - Effort: 2 hours

7. **Wire latency and queue sampling (3.1, 3.2)**
   - Files: Add FastAPI middleware for latency, wire task_queue for depth
   - Effort: 1-2 days

8. **Resolve health route conflicts (4.1)**
   - Files: All health route files
   - Change: Designate canonical endpoint, add sunset headers to legacy, document hierarchy
   - Effort: 1 day

---

## 7. File Reference Index by Risk Category

### Fallback-to-OK Patterns
- `backend/app/api/routes/health.py:42-57` (legacy health)
- `backend/app/modules/system_health/service.py:191-242` (subsystem failures)
- `backend/app/modules/course_factory/service.py:856-867` (EventStream publish)
- `backend/app/core/audit_bridge.py:44-57` (audit bridge skip)

### Placeholder Implementations
- `backend/app/modules/health_monitor/service.py:242-284` (health checks)
- `backend/app/modules/system_health/service.py:216-225` (threats)
- `backend/app/modules/runtime_auditor/service.py:365-411` (edge-of-chaos)
- `backend/app/modules/system_health/service.py:244-262` (agent state)
- `backend/main.py:156-304` (runtime auditor not wired)
- Learning layer services (no correlation_id capture)
- Learning layer services (no governance audit)

### Missing Telemetry
- `backend/app/modules/runtime_auditor/service.py:188-197` (latency sampling)
- `backend/app/modules/runtime_auditor/service.py:199-208` (queue sampling)
- Database/Redis pool metrics (no specific file - infrastructure gap)
- External API telemetry (scattered across modules)

### Conflicting Semantics
- `backend/app/api/routes/health.py:25-57` (legacy health route)
- `backend/app/modules/health_monitor/router.py` (service health)
- `backend/app/modules/system_health/router.py` (system health)
- `backend/main.py:229-248` (degraded mode)

---

## 8. Detection and Monitoring Recommendations

### Immediate Monitoring Additions

1. **EventStream publish failure rate**
   - Metric: `eventstream_publish_errors_total`
   - Alert: > 5% failure rate over 5 minutes

2. **Audit write failure rate**
   - Metric: `audit_write_errors_total`
   - Alert: > 0 failures in production

3. **Health check execution success rate**
   - Metric: `health_check_execution_success_rate`
   - Alert: < 95% over 5 minutes

4. **Runtime auditor lifecycle**
   - Metric: `runtime_auditor_running` (boolean gauge)
   - Alert: value = 0 in production

5. **Learning layer mutation audit coverage**
   - Metric: `learning_layer_mutations_without_audit_total`
   - Alert: > 0 in production

### Health Endpoint SLOs

- **Availability:** `/api/system/health` should return 200 with valid JSON 99.9% of the time
- **Latency:** P95 latency < 500ms
- **Accuracy:** Health status should match actual subsystem state (no false greens)
- **Freshness:** Health data should be < 60s stale

---

**End of Silent Fail Risk Register**
