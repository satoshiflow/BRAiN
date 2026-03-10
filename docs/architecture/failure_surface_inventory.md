# Failure Surface Inventory

**Version:** 1.0  
**Date:** 2026-03-10  
**Sprint:** A - Backend Grounding Audit  
**Purpose:** Comprehensive inventory of all mutating/async paths with risk classification, error handling patterns, and audit/event coverage gaps.

---

## Executive Summary

The BRAiN backend has **486 async service methods** and **290+ mutating HTTP endpoints** (POST/PUT/PATCH/DELETE). This inventory identifies all critical failure surfaces across:

- **Request paths:** HTTP endpoints that mutate state
- **Async execution paths:** Background workers, task processors, event handlers
- **Integration paths:** External API calls, database operations, Redis operations
- **Governance paths:** Approval flows, policy enforcement, audit writes

**Critical Findings:**
- **698+ HTTPException raises** across router files
- **Learning layers (P0-P7) lack audit/event coverage** for all mutations
- **Health routes have fallback-to-ok patterns** masking exceptions
- **No standardized error classification taxonomy**
- **Correlation ID propagation incomplete** across learning/execution layers
- **Runtime auditor NOT wired** - continuous monitoring inactive

---

## 1. Failure Surface Classification

### 1.1 Risk Classification Matrix

| Risk Level | Criteria | Impact | Example Paths |
|------------|----------|--------|---------------|
| **CRITICAL** | Data loss, security breach, revenue impact, governance bypass | System integrity, tenant isolation, financial loss | Auth token generation, payment processing, skill/capability lifecycle transitions, DNA mutations, approval consumption |
| **HIGH** | State corruption, failed audit write, learning layer mutations without audit | Data integrity, compliance | Experience ingestion, insight derivation, pattern consolidation, evolution proposals, mission creation |
| **MEDIUM** | Recoverable failures, degraded UX, eventual consistency violations | User experience, system performance | Health check failures, EventStream publish failures, cache misses |
| **LOW** | Logging failures, telemetry gaps, read-only operations | Observability gaps | Metric collection failures, diagnostic retrieval |

---

## 2. Mutating HTTP Endpoints

### 2.1 Authentication & Authorization (CRITICAL)

| Endpoint | Method | Service | Risk | Audit Coverage | Notes |
|----------|--------|---------|------|----------------|-------|
| `/api/auth/register` | POST | `app.services.auth_service` | CRITICAL | Partial | Creates user account, password hash, no audit event |
| `/api/auth/login` | POST | `app.services.auth_service` | CRITICAL | Partial | Issues access/refresh token pair, `backend/app/api/routes/auth.py:168` |
| `/api/auth/refresh` | POST | `app.services.auth_service` | CRITICAL | Partial | Rotates refresh token, revokes old token |
| `/api/auth/logout` | POST | `app.services.auth_service` | CRITICAL | No | Revokes refresh token, no audit event |
| `/api/auth/service-token` | POST | `app.services.auth_service` | CRITICAL | No | Issues service tokens, `backend/app/api/routes/auth.py:437` |
| `/api/auth/agent-token` | POST | `app.services.auth_service` | CRITICAL | No | Issues agent tokens, `backend/app/api/routes/auth.py:482` |

**Error Handling Pattern:** HTTPException with sanitized messages, broad `Exception` catch in routers  
**Audit Gap:** Token issuance/revocation not audited  
**File:** `backend/app/api/routes/auth.py`, `backend/app/services/auth_service.py`

---

### 2.2 Learning Layers (HIGH - NO AUDIT COVERAGE)

#### P0: Experience Layer

| Endpoint | Method | Service | Risk | Audit Coverage | File Reference |
|----------|--------|---------|------|----------------|----------------|
| `/api/experience-layer/skill-runs/{skill_run_id}/ingest` | POST | `experience_layer.service` | HIGH | **MISSING** | `backend/app/modules/experience_layer/router.py:62` |

**Error Handling:** HTTPException 403/404, no correlation ID in error response  
**Failure Mode:** Direct DB insert without audit → event ordering  
**File:** `backend/app/modules/experience_layer/service.py`

#### P1: Observer Core

| Endpoint | Method | Service | Risk | Audit Coverage | File Reference |
|----------|--------|---------|------|----------------|----------------|
| `/api/observer-core/signals` | GET | `observer_core.service` | LOW | N/A | Read-only |
| `/api/observer-core/state` | GET | `observer_core.service` | LOW | N/A | Read-only |

**Failure Mode:** Observer signals generated internally, no explicit ingest endpoint  
**Audit Gap:** Signal generation not audited  
**File:** `backend/app/modules/observer_core/service.py`

#### P2: Insight Layer

| Endpoint | Method | Service | Risk | Audit Coverage | File Reference |
|----------|--------|---------|------|----------------|----------------|
| `/api/insight-layer/skill-runs/{skill_run_id}/derive` | POST | `insight_layer.service` | HIGH | **MISSING** | `backend/app/modules/insight_layer/router.py:62` |
| `/api/insight-layer/insights/{insight_id}/promote` | POST | `insight_layer.service` | HIGH | **MISSING** | Promotion to knowledge not audited |

**Error Handling:** HTTPException 403/404/400  
**Failure Mode:** Insight candidate creation without audit trail  
**File:** `backend/app/modules/insight_layer/service.py`

#### P3: Consolidation Layer

| Endpoint | Method | Service | Risk | Audit Coverage | File Reference |
|----------|--------|---------|------|----------------|----------------|
| `/api/consolidation-layer/skill-runs/{skill_run_id}/derive` | POST | `consolidation_layer.service` | HIGH | **MISSING** | `backend/app/modules/consolidation_layer/router.py:62` |
| `/api/consolidation-layer/patterns/{pattern_id}/promote` | POST | `consolidation_layer.service` | HIGH | **MISSING** | Pattern promotion not audited |

**Failure Mode:** Pattern candidate creation/promotion without audit  
**File:** `backend/app/modules/consolidation_layer/service.py`

#### P4: Evolution Control

| Endpoint | Method | Service | Risk | Audit Coverage | File Reference |
|----------|--------|---------|------|----------------|----------------|
| `/api/evolution-control/proposals` | POST | `evolution_control.service` | HIGH | **MISSING** | `backend/app/modules/evolution_control/router.py:69` |
| `/api/evolution-control/proposals/{proposal_id}/approve` | POST | `evolution_control.service` | CRITICAL | **MISSING** | Governance decision not audited |
| `/api/evolution-control/proposals/{proposal_id}/reject` | POST | `evolution_control.service` | CRITICAL | **MISSING** | Governance decision not audited |

**Error Handling:** HTTPException 403/404/400, ValueError exceptions  
**Failure Mode:** Evolution proposal mutations lack audit trail, governance decisions not durable  
**File:** `backend/app/modules/evolution_control/service.py`

#### P5: Deliberation Layer

| Endpoint | Method | Service | Risk | Audit Coverage | File Reference |
|----------|--------|---------|------|----------------|----------------|
| `/api/deliberation-layer/missions/{mission_id}/summaries` | POST | `deliberation_layer.service` | HIGH | **MISSING** | `backend/app/modules/deliberation_layer/router.py:40` |
| `/api/deliberation-layer/missions/{mission_id}/tensions` | POST | `deliberation_layer.service` | HIGH | **MISSING** | Mission tension creation not audited |

**Failure Mode:** Deliberation artifacts (summaries, tensions) created without audit  
**File:** `backend/app/modules/deliberation_layer/service.py`

#### P6: Discovery Layer

| Endpoint | Method | Service | Risk | Audit Coverage | File Reference |
|----------|--------|---------|------|----------------|----------------|
| `/api/discovery-layer/scans` | POST | `discovery_layer.service` | MEDIUM | **MISSING** | `backend/app/modules/discovery_layer/router.py:68` |
| `/api/discovery-layer/skill-proposals` | GET | `discovery_layer.service` | LOW | N/A | Read-only |
| `/api/discovery-layer/skill-proposals/{proposal_id}/approve` | POST | `discovery_layer.service` | CRITICAL | **MISSING** | Governance decision not audited |
| `/api/discovery-layer/skill-proposals/{proposal_id}/reject` | POST | `discovery_layer.service` | CRITICAL | **MISSING** | Governance decision not audited |

**Error Handling:** HTTPException 403/422/404/409, PermissionError/ValidationError/NotFoundError exceptions  
**Failure Mode:** Skill discovery and approval decisions lack audit trail  
**File:** `backend/app/modules/discovery_layer/service.py`

#### P7: Economy Layer

| Endpoint | Method | Service | Risk | Audit Coverage | File Reference |
|----------|--------|---------|------|----------------|----------------|
| `/api/economy-layer/assessments` | POST | `economy_layer.service` | HIGH | **MISSING** | `backend/app/modules/economy_layer/router.py:51` |
| `/api/economy-layer/assessments/{assessment_id}/approve` | POST | `economy_layer.service` | CRITICAL | **MISSING** | Economic governance decision not audited |

**Failure Mode:** Economic assessments and approvals lack audit trail  
**File:** `backend/app/modules/economy_layer/service.py`

**Summary:** ALL learning layer mutations (P0-P7) lack audit/event coverage. Governance decisions (approve/reject) across P4, P6, P7 are CRITICAL risk with MISSING audit.

---

### 2.3 Skills/Capabilities Registry (HIGH)

| Endpoint | Method | Service | Risk | Audit Coverage | File Reference |
|----------|--------|---------|------|----------------|----------------|
| `/api/skills-registry/skill-definitions` | POST | `skills_registry.service` | HIGH | Partial | Skill definition creation |
| `/api/skills-registry/skill-definitions/{key}/versions/{version}` | PATCH | `skills_registry.service` | HIGH | Partial | Skill definition update |
| `/api/skills-registry/.../submit-review` | POST | `skills_registry.service` | HIGH | Partial | Lifecycle transition |
| `/api/skills-registry/.../approve` | POST | `skills_registry.service` | CRITICAL | Partial | Governance decision |
| `/api/skills-registry/.../activate` | POST | `skills_registry.service` | CRITICAL | Partial | Activation decision |
| `/api/skills-registry/.../reject` | POST | `skills_registry.service` | CRITICAL | Partial | Governance decision |
| `/api/skills-registry/.../deprecate` | POST | `skills_registry.service` | HIGH | Partial | Lifecycle transition |
| `/api/capabilities-registry/capability-definitions` | POST | `capabilities_registry.service` | HIGH | Partial | Similar pattern to skills |

**Error Handling:** HTTPException with transition errors  
**Audit Gap:** Lifecycle transitions have partial event coverage (likely EventStream only, no audit_bridge)  
**File:** `backend/app/modules/skills_registry/router.py:53-173`, `backend/app/modules/capabilities_registry/router.py:55-175`

---

### 2.4 Agent Management & Task Queue (MEDIUM - EventStream Coverage)

| Endpoint | Method | Service | Risk | Audit Coverage | File Reference |
|----------|--------|---------|------|----------------|----------------|
| `/api/agents/register` | POST | `agent_management.service` | MEDIUM | EventStream | `backend/app/modules/agent_management/router.py:51` |
| `/api/agents/heartbeat` | POST | `agent_management.service` | LOW | EventStream | Agent activation signal |
| `/api/agents/{agent_id}/invoke-skill` | POST | `agent_management.service` | HIGH | Partial | Skill invocation |
| `/api/agents/{agent_id}/delegate` | POST | `agent_management.service` | HIGH | Partial | Delegation decision |
| `/api/agents/{agent_id}/terminate` | POST | `agent_management.service` | HIGH | EventStream | Termination signal |
| `/api/tasks` | POST | `task_queue.service` | MEDIUM | EventStream | Task creation |
| `/api/tasks/{task_id}/start` | POST | `task_queue.service` | MEDIUM | EventStream | Task start |
| `/api/tasks/{task_id}/complete` | POST | `task_queue.service` | MEDIUM | EventStream | Task completion |
| `/api/tasks/{task_id}/fail` | POST | `task_queue.service` | MEDIUM | EventStream | Task failure |

**Error Handling:** HTTPException, EventStream publish failures logged but not raised  
**Audit Gap:** EventStream coverage exists, but no audit_bridge writes for compliance  
**File:** `backend/app/modules/agent_management/service.py:43-198`, `backend/app/modules/task_queue/service.py:50-504`

---

### 2.5 Immune/Recovery/Repair (CRITICAL - Audit Bridge Coverage)

| Endpoint | Method | Service | Risk | Audit Coverage | File Reference |
|----------|--------|---------|------|----------------|----------------|
| `/api/immune-orchestrator/incidents` | POST | `immune_orchestrator.service` | CRITICAL | **Audit Bridge** | Incident submission |
| `/api/immune-orchestrator/decisions/{decision_id}/execute` | POST | `immune_orchestrator.service` | CRITICAL | **Audit Bridge** | Decision execution |
| `/api/recovery-policy/actions` | POST | `recovery_policy_engine.service` | CRITICAL | **Audit Bridge** | Recovery action |
| `/api/genetic-integrity/scans` | POST | `genetic_integrity.service` | CRITICAL | **Audit Bridge** | Integrity scan |
| `/api/genetic-quarantine/quarantine` | POST | `genetic_quarantine.service` | CRITICAL | **Audit Bridge** | Quarantine operation |
| `/api/opencode-repair/tickets` | POST | `opencode_repair.service` | HIGH | **Audit Bridge** | Repair ticket creation |

**Error Handling:** HTTPException, audit write failures logged  
**Audit Coverage:** COMPLETE - uses audit_bridge for all critical operations  
**File:** `backend/app/modules/immune_orchestrator/service.py:147`, `backend/app/modules/recovery_policy_engine/service.py:182`, etc.

---

### 2.6 Missions (HIGH)

| Endpoint | Method | Service | Risk | Audit Coverage | File Reference |
|----------|--------|---------|------|----------------|----------------|
| `/api/missions/templates` | POST | `missions.service` | HIGH | Partial | Mission template creation |
| `/api/missions/templates/{template_id}` | PUT | `missions.service` | HIGH | Partial | Template update |
| `/api/missions/templates/{template_id}` | DELETE | `missions.service` | HIGH | Partial | Template deletion |
| `/api/missions` | POST | `missions.service` | HIGH | Partial | Mission creation |

**Error Handling:** HTTPException  
**Audit Gap:** Mission lifecycle events likely in EventStream only  
**File:** `backend/app/modules/missions/router.py:197-396`

---

### 2.7 WebGenesis (HIGH - Lifecycle Operations)

| Endpoint | Method | Service | Risk | Audit Coverage | File Reference |
|----------|--------|---------|------|----------------|----------------|
| `/api/webgenesis/spec` | POST | `webgenesis.service` | HIGH | Partial | Site spec submission |
| `/api/webgenesis/{site_id}/generate` | POST | `webgenesis.service` | HIGH | Partial | Code generation |
| `/api/webgenesis/{site_id}/build` | POST | `webgenesis.service` | HIGH | Partial | Build execution |
| `/api/webgenesis/{site_id}/deploy` | POST | `webgenesis.service` | HIGH | Partial | Deployment |
| `/api/webgenesis/{site_id}` | DELETE | `webgenesis.service` | HIGH | Partial | Site deletion |
| `/api/webgenesis/{site_id}/rollback` | POST | `webgenesis.service` | HIGH | Partial | Rollback operation |

**Error Handling:** HTTPException 403/404/400/409, lifecycle status guards  
**Audit Gap:** Lifecycle operations partially audited (likely DB audit logs only)  
**File:** `backend/app/modules/webgenesis/router.py:207-1127`

---

### 2.8 Course Factory & Distribution (MEDIUM - EventStream Coverage)

| Endpoint | Method | Service | Risk | Audit Coverage | File Reference |
|----------|--------|---------|------|----------------|----------------|
| `/api/course-factory/generate-ir` | POST | `course_factory.service` | MEDIUM | EventStream | IR generation |
| `/api/course-factory/generate` | POST | `course_factory.service` | HIGH | EventStream | Course generation |
| `/api/course-factory/workflow/transition` | POST | `course_factory.service` | HIGH | EventStream | Workflow transition |
| `/api/course-factory/workflow/rollback` | POST | `course_factory.service` | HIGH | EventStream | Rollback operation |

**Error Handling:** HTTPException, EventStream publish wrapped in _publish_event_safe  
**Audit Gap:** EventStream coverage exists, no audit_bridge writes  
**File:** `backend/app/modules/course_factory/service.py:853-1106`

---

### 2.9 Governance & IR (CRITICAL - EventStream + Audit)

| Endpoint | Method | Service | Risk | Audit Coverage | File Reference |
|----------|--------|---------|------|----------------|----------------|
| `/api/governance/approvals` | POST | `governance.service` | CRITICAL | Partial | Approval request creation |
| `/api/governance/approvals/{approval_id}/approve` | POST | `governance.service` | CRITICAL | Partial | Approval decision |
| `/api/governance/approvals/{approval_id}/reject` | POST | `governance.service` | CRITICAL | Partial | Rejection decision |
| `/api/ir-governance/validate` | POST | `ir_governance.validator` | HIGH | EventStream | IR validation |
| `/api/ir-governance/approvals` | POST | `ir_governance.approvals` | CRITICAL | EventStream | IR approval request |
| `/api/ir-governance/approvals/consume` | POST | `ir_governance.approvals` | CRITICAL | EventStream | Approval consumption |

**Error Handling:** HTTPException, EventStream publish failures logged  
**Audit Gap:** Governance decisions use EventStream but not audit_bridge for durable compliance record  
**File:** `backend/app/modules/governance/governance_service.py:106`, `backend/app/modules/ir_governance/approvals.py:148-181`

---

### 2.10 Memory & Learning (MEDIUM)

| Endpoint | Method | Service | Risk | Audit Coverage | File Reference |
|----------|--------|---------|------|----------------|----------------|
| `/api/memory/store` | POST | `memory.service` | MEDIUM | EventStream | Memory entry creation |
| `/api/memory/entries/{memory_id}` | DELETE | `memory.service` | MEDIUM | EventStream | Memory deletion |
| `/api/memory/sessions` | POST | `memory.service` | LOW | EventStream | Session creation |
| `/api/memory/skill-runs/{skill_run_id}/ingest` | POST | `memory.service` | MEDIUM | EventStream | SkillRun memory ingestion |
| `/api/learning/metrics` | POST | `learning.service` | LOW | No | Metric entry creation |
| `/api/learning/strategies` | POST | `learning.service` | MEDIUM | No | Learning strategy creation |
| `/api/learning/experiments` | POST | `learning.service` | MEDIUM | No | Experiment creation |

**Error Handling:** HTTPException  
**Audit Gap:** Learning metrics/strategies/experiments not audited  
**File:** `backend/app/modules/memory/service.py`, `backend/app/modules/learning/router.py:90-334`

---

## 3. Async Execution Paths

### 3.1 Background Workers

| Worker | Trigger | Risk | Audit Coverage | File Reference |
|--------|---------|------|----------------|----------------|
| Mission Worker | Startup (ENABLE_MISSION_WORKER=true) | HIGH | Partial | `backend/app/compat/legacy_missions.py` |
| Metrics Collector | Startup (ENABLE_METRICS_COLLECTOR=true) | LOW | No | `backend/app/workers/metrics_collector.py` |
| Autoscaler | Startup (ENABLE_AUTOSCALER=true) | MEDIUM | No | `backend/app/workers/autoscaler.py` |
| Runtime Auditor | **NOT WIRED** | HIGH | No | `backend/app/modules/runtime_auditor/service.py:156-169` |

**Failure Mode:** Mission worker failures may not propagate to health system  
**Critical Gap:** Runtime auditor NOT started at startup, continuous monitoring inactive  
**File:** `backend/main.py:252-269`

---

### 3.2 EventStream Handlers (Implicit)

| Handler | Event Type | Risk | Audit Coverage | File Reference |
|---------|------------|------|----------------|----------------|
| Immune decision handler | `immune.incident` | CRITICAL | Audit Bridge | `backend/app/modules/immune_orchestrator/service.py` |
| Recovery action handler | `recovery.trigger` | CRITICAL | Audit Bridge | `backend/app/modules/recovery_policy_engine/service.py` |
| Repair trigger handler | `immune.high_risk`, `recovery.high_risk` | HIGH | Audit Bridge | `backend/main.py:214-220` |

**Error Handling:** EventStream publish failures logged, handlers may fail silently  
**Audit Gap:** EventStream subscription/handler failures not audited  

---

### 3.3 Database Operations (All async services)

| Operation Category | Risk | Audit Coverage | Error Handling Pattern |
|--------------------|------|----------------|------------------------|
| INSERT (create operations) | HIGH | Varies by module | HTTPException on constraint violations, broad catch |
| UPDATE (state mutations) | HIGH | Varies by module | HTTPException on not found, broad catch |
| DELETE (data removal) | CRITICAL | Varies by module | HTTPException on not found, cascade failures possible |
| SELECT (read operations) | LOW | N/A | HTTPException 404 on not found |

**Common Pattern:**
```python
try:
    result = await db.execute(...)
    await db.commit()
except Exception as e:
    logger.error(...)
    raise HTTPException(status_code=500, detail="Internal server error")
```

**Risk:** Broad exception catch masks specific failure modes, no structured failure classification

---

### 3.4 Redis Operations

| Operation | Risk | Failure Mode | Recovery Pattern |
|-----------|------|--------------|------------------|
| EventStream publish | MEDIUM | Redis unavailable → event lost | Logged, no retry |
| Rate limit token bucket | LOW | Redis unavailable → rate limit fails open | Degraded mode |
| Session storage | MEDIUM | Redis unavailable → session lost | User re-authenticates |
| Approval token cache | CRITICAL | Redis unavailable → approval verification fails | Operations blocked |

**Critical Gap:** No circuit breaker or fallback for Redis failures in EventStream publish

---

### 3.5 External API Calls

| Integration | Risk | Timeout | Retry Policy | Audit Coverage |
|-------------|------|---------|--------------|----------------|
| LLM providers (OpenAI, Anthropic, etc.) | HIGH | Varies | Module-specific | Partial |
| Payment gateways (PayCore) | CRITICAL | 30s (likely) | Unknown | Partial |
| Email/SMS (connectors) | MEDIUM | Unknown | Unknown | No |
| Hetzner DNS | MEDIUM | Unknown | Unknown | No |

**Failure Mode:** External API failures may not be classified, no standard retry/circuit-break policy  
**Audit Gap:** External API failures not consistently audited

---

## 4. Error Handling Patterns

### 4.1 Router-Level Error Handling

**Pattern 1: Specific Exception Mapping (Common)**
```python
try:
    result = await service.operation(...)
    return result
except PermissionError as exc:
    raise HTTPException(status_code=403, detail=str(exc)) from exc
except NotFoundError as exc:
    raise HTTPException(status_code=404, detail=str(exc)) from exc
except ValidationError as exc:
    raise HTTPException(status_code=422, detail=str(exc)) from exc
except ValueError as exc:
    raise HTTPException(status_code=400, detail=str(exc)) from exc
```

**Found in:** Learning layers, discovery layer, evolution control  
**Risk:** `str(exc)` may leak internal details  
**File:** `backend/app/modules/discovery_layer/router.py:96-99`

---

**Pattern 2: Broad Catch with Fallback (RISKY)**
```python
try:
    summary = await service.get_health_summary()
    return {"status": "ok" if summary.status.value != "critical" else "degraded", ...}
except Exception as e:
    return {"status": "ok", "error": str(e), ...}
```

**Found in:** Legacy health endpoint  
**Risk:** Masks failures as success, returns `status: "ok"` on exception  
**File:** `backend/app/api/routes/health.py:42-57`

---

**Pattern 3: HTTPException Re-raise (BEST)**
```python
except HTTPException:
    raise
except Exception as e:
    logger.error(...)
    raise HTTPException(status_code=500, detail="Internal server error")
```

**Found in:** WebGenesis, course factory  
**Risk:** Generic error message, no correlation ID in response  
**File:** `backend/app/modules/webgenesis/router.py:264-268`

---

**Pattern 4: Service-Level Exception (Good)**
```python
# Service raises custom exceptions
raise PermissionError("Tenant ID mismatch")
# Router catches and maps to HTTPException
except PermissionError as exc:
    raise HTTPException(status_code=403, detail=str(exc))
```

**Found in:** Learning layers, skills registry  
**Risk:** `str(exc)` may leak details if exception message not sanitized

---

### 4.2 Service-Level Error Handling

**Pattern 1: Log and Return None (Silent Fail)**
```python
try:
    return await self._get_mission_health()
except Exception as e:
    logger.warning(f"Mission health unavailable: {e}")
    return None
```

**Found in:** System health service  
**Risk:** Health aggregator treats `None` as unknown, may mask critical failures  
**File:** `backend/app/modules/system_health/service.py:229-242`

---

**Pattern 2: Log and Raise Custom Exception (Best)**
```python
try:
    await db.execute(...)
except SQLAlchemyError as e:
    logger.error(...)
    raise DatabaseError("Failed to persist record") from e
```

**Found in:** Immune/recovery modules  
**Risk:** None if exception sanitized

---

**Pattern 3: EventStream Publish Failure (Degraded)**
```python
async def _publish_event_safe(self, event: Event) -> None:
    if self.event_stream is None:
        logger.debug("EventStream not available, skipping event")
        return
    try:
        await self.event_stream.publish_event(event)
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")
```

**Found in:** Course factory, IR governance, DNA service  
**Risk:** Event loss silent, no retry, no alerting  
**File:** `backend/app/modules/course_factory/service.py:856-867`

---

## 5. Audit/Event Coverage Gaps

### 5.1 Missing Audit Coverage (HIGH RISK)

| Operation | Risk | Current Coverage | Gap |
|-----------|------|------------------|-----|
| Learning layer mutations (P0-P7) | HIGH | **NONE** | Direct DB writes, no audit_bridge calls |
| Governance decisions (approve/reject) | CRITICAL | EventStream only | No durable audit record via audit_bridge |
| Token issuance/revocation | CRITICAL | Partial | Auth operations not audited |
| Health degradation/recovery | MEDIUM | EventStream only | No audit_bridge writes for compliance |
| Skill/capability lifecycle transitions | HIGH | EventStream only | No audit_bridge writes |
| Mission template CRUD | HIGH | Partial | Deletion not audited |
| Memory deletion | MEDIUM | EventStream only | No audit_bridge writes |

**File References:**
- Learning layers: `backend/app/modules/experience_layer/service.py`, `backend/app/modules/insight_layer/service.py`, etc.
- Governance: `backend/app/modules/governance/governance_service.py`, `backend/app/modules/discovery_layer/service.py`
- Auth: `backend/app/services/auth_service.py`

---

### 5.2 Correlation ID Propagation Gaps

| Path | Correlation ID Source | Propagation Status | Gap |
|------|----------------------|-------------------|-----|
| HTTP Request → SkillRun | Generated at skill_engine | Partial | Not propagated to all learning layers |
| SkillRun → Experience → Insight → Pattern | SkillRun ID | **Missing** | Learning layers don't capture correlation_id |
| SkillRun → Audit → Event → Observer | SkillRun ID | **Missing** | Audit/event correlation incomplete |
| Mission → SkillRun | Mission ID | Partial | Not always propagated to audit records |
| Governance decision → Audit | Approval ID | **Missing** | Governance decisions lack correlation ID in audit |

**Critical Gap:** Learning layer mutations (P0-P7) do NOT capture or propagate correlation IDs from source SkillRun

---

### 5.3 EventStream vs Audit Bridge Coverage

| Module | EventStream | Audit Bridge | Gap |
|--------|-------------|--------------|-----|
| Immune/Recovery/Repair | ✅ Required | ✅ Required | None |
| Agent Management | ✅ Yes | ❌ No | No compliance record |
| Task Queue | ✅ Yes | ❌ No | No compliance record |
| Course Factory | ✅ Yes | ❌ No | No compliance record |
| IR Governance | ✅ Yes | ❌ No | Governance decisions not durably audited |
| Memory | ✅ Yes | ❌ No | Memory operations not audited |
| Planning | ✅ Yes | ❌ No | Planning decisions not audited |
| Health Monitor | ✅ Optional | ❌ No | Health transitions not audited |
| Learning Layers (P0-P7) | ❌ No | ❌ No | **COMPLETE COVERAGE GAP** |

**Pattern:** Most modules use EventStream for events but NOT audit_bridge for durable audit records

---

## 6. Critical Failure Scenarios

### 6.1 Silent Fail Scenarios

| Scenario | Failure Path | Risk | Detection | File Reference |
|----------|--------------|------|-----------|----------------|
| Health check exception | `/api/health` returns `ok` | HIGH | None | `backend/app/api/routes/health.py:54` |
| EventStream unavailable | Events dropped, logged only | MEDIUM | Logs only | Course factory, IR governance, etc. |
| Audit write failure | Operation succeeds, audit lost | HIGH | Logs only | `backend/app/core/audit_bridge.py:56-57` |
| Runtime auditor not wired | Continuous monitoring inactive | HIGH | None | `backend/main.py` (missing wiring) |
| Redis unavailable | EventStream disabled, immune unwired | CRITICAL | Startup warning | `backend/main.py:176-248` |

---

### 6.2 Cascading Failure Scenarios

| Trigger | Cascade Path | Impact | Mitigation |
|---------|--------------|--------|------------|
| Database timeout | All async services block → request timeout → health degraded | System-wide outage | None currently |
| Redis failure | EventStream down → immune unwired → recovery disabled | Governance/safety gap | Degraded mode |
| Learning layer direct write failure | No audit → no event → observer blind → insight/pattern lost | Data integrity loss | None currently |
| Approval token Redis loss | Approval verification fails → governance blocked | Operational halt | None currently |

---

### 6.3 Race Condition Risks

| Operation | Risk | Impact | File Reference |
|-----------|------|--------|----------------|
| Skill lifecycle transition (concurrent approve/reject) | State race | Undefined state | `backend/app/modules/skills_registry/service.py` |
| Health check concurrent updates | Status inconsistency | False health signal | `backend/app/modules/health_monitor/service.py:76-167` |
| EventStream publish during shutdown | Lost events | Audit gap | `backend/main.py:286-288` |

---

## 7. Recommendations for Sprint C (Diagnostics & Error Framework)

Based on this inventory, Sprint C should address:

1. **Standardize Failure Taxonomy:**
   - `request_failure`, `execution_failure`, `integration_failure`, `governance_failure`, `observability_failure`, `learning_pipeline_failure`
   - Map all HTTPException raises to failure classes

2. **Standard Failure Envelope:**
   - `FailureRecord` with `tenant_id`, `correlation_id`, `skill_run_id`, `mission_id`, `failure_class`, `failure_code`, `severity`, `retryability`, `operator_action`, `audit_ref`, `event_ref`, `provenance_refs`

3. **Correlation ID Propagation:**
   - Mandatory in all learning layer mutations
   - Propagate from request → SkillRun → audit → event → observer → experience/insight/pattern

4. **Audit Coverage for Learning Layers:**
   - Add `write_unified_audit` calls to all P0-P7 mutations
   - Capture governance decisions (approve/reject) in durable audit records

5. **Structured Error Responses:**
   - Include correlation ID in HTTPException detail/headers
   - Sanitize exception messages to prevent internal detail leaks

6. **EventStream Failure Handling:**
   - Implement circuit breaker for publish failures
   - Alert on event loss (currently silent)

7. **Health Check Hardening:**
   - Eliminate fallback-to-ok pattern in `/api/health`
   - Wire runtime_auditor into startup

---

## 8. File Reference Index

### High-Risk Mutating Paths
- **Auth:** `backend/app/api/routes/auth.py`, `backend/app/services/auth_service.py`
- **Learning Layers (P0-P7):** `backend/app/modules/experience_layer/`, `backend/app/modules/insight_layer/`, `backend/app/modules/consolidation_layer/`, `backend/app/modules/evolution_control/`, `backend/app/modules/deliberation_layer/`, `backend/app/modules/discovery_layer/`, `backend/app/modules/economy_layer/`
- **Immune/Recovery:** `backend/app/modules/immune_orchestrator/service.py`, `backend/app/modules/recovery_policy_engine/service.py`
- **Governance:** `backend/app/modules/governance/governance_service.py`, `backend/app/modules/ir_governance/approvals.py`

### Error Handling Patterns
- **Fallback-to-ok:** `backend/app/api/routes/health.py:42-57`
- **EventStream safe publish:** `backend/app/modules/course_factory/service.py:856-867`
- **Service exception mapping:** `backend/app/modules/discovery_layer/router.py:96-99`

### Audit Gaps
- **Learning layers:** All service.py files in P0-P7 modules (no audit_bridge calls)
- **Governance decisions:** `backend/app/modules/evolution_control/service.py`, `backend/app/modules/discovery_layer/service.py`, `backend/app/modules/economy_layer/service.py`

---

**End of Failure Surface Inventory**
