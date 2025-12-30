# Sprint 2: Missions Architecture Decision

**Status:** ✅ **DECIDED - Migrate LEGACY Implementation**
**Date:** 2025-12-28
**Analyzed By:** Sprint 2 EventStream Migration Team

---

## Executive Summary

**Problem:** BRAiN has TWO missions implementations running simultaneously with conflicting architectures.

**Discovery:** The systems are **INCOMPATIBLE and BROKEN**:
- NEW API creates missions that are NEVER executed (orphaned)
- LEGACY worker runs but can't see NEW missions
- Route collision causes API requests to hit NEW (broken) instead of LEGACY (working)

**Decision:** **Migrate LEGACY implementation** - it's the only functional system.

---

## Architecture Analysis

### System 1: LEGACY (`backend/modules/missions/`)

**Location:** `backend/modules/missions/`

**Components:**
```
modules/missions/
├── mission_control_runtime.py  # EventStream integration layer ✅
├── queue.py                    # Redis ZSET priority queue
├── worker.py                   # Background worker (started in main.py)
├── models.py                   # MissionPayload, MissionQueueEntry
├── schemas.py                  # API response models
└── api/routes/missions.py      # Full-featured API router
```

**Architecture:**
```
Client → API Router → Runtime → Queue (Redis ZSET)
                              ↓
                         EventStream ✅
                              ↓
                         Worker (background)
                              ↓
                         Mission Execution
```

**Features:**
- ✅ Redis ZSET-based priority queue
- ✅ Background worker processing
- ✅ EventStream integration (TASK_CREATED events)
- ✅ Event history API (`/events/history`)
- ✅ Event stats API (`/events/stats`)
- ✅ Queue preview API (`/queue`)
- ✅ Worker status API (`/worker/status`)
- ✅ Health checks
- ✅ Actually executes missions

**EventStream Coverage:**
- ✅ `TASK_CREATED` (line 92-100 in mission_control_runtime.py)
- ❓ Missing: TASK_STARTED, TASK_COMPLETED, TASK_FAILED (execution lifecycle)

**Integration Points:**
- `backend/main.py:34` - Worker import
- `backend/main.py:135-136` - Worker startup in lifespan
- `backend/main.py:148-149` - Worker shutdown
- `backend/api/routes/missions.py` - Auto-discovered router

**Redis Keys:**
- Queue: Likely `brain:missions:queue` (ZSET)
- Events: EventStream manages (`brain:events:*`)

---

### System 2: NEW (`app/modules/missions/`)

**Location:** `app/modules/missions/`

**Components:**
```
app/modules/missions/
├── service.py       # Direct Redis CRUD operations ❌ NO EventStream
├── executor.py      # Mock executor (just sleeps) ❌
├── router.py        # Modern REST API with auth
└── models.py        # Mission, MissionCreate, MissionStatus
```

**Architecture:**
```
Client → API Router → Service → Redis (direct CRUD)
                              ↓
                         ❌ NO EventStream
                         ❌ NO Queue
                         ❌ NO Worker Integration
                              ↓
                         Mock Executor (asyncio.create_task)
                              ↓
                         ❌ ORPHANED - never actually runs
```

**Features:**
- ✅ Modern REST API design
- ✅ Security/auth integration (`get_current_principal`)
- ✅ Mission CRUD (create, get, list, update_status)
- ✅ Mission logging (`/log`)
- ✅ Statistics (`/stats/overview`)
- ❌ NO EventStream integration
- ❌ NO queue system
- ❌ NO background worker
- ❌ Mock executor (just sleeps)
- ❌ Missions created but NEVER executed

**Redis Keys:**
- Mission data: `brain:missions:mission:{id}` (String - JSON)
- Index: `brain:missions:index` (Set)
- Logs: `brain:missions:log:{id}` (List)
- Stats: `brain:missions:stats` (String - JSON)

**Integration Points:**
- `backend/main.py:66` - Router import
- `backend/main.py:245` - Router registration (**REGISTERED FIRST - WINS**)

---

## Critical Problem: Route Collision

**In `backend/main.py`:**

```python
# Line 245: NEW router registered FIRST
app.include_router(app_missions_router, tags=["missions"])

# Line 248: LEGACY router auto-discovered SECOND
_include_legacy_routers(app)  # Discovers backend/api/routes/missions.py
```

**FastAPI Behavior:** First registered router WINS on path collision.

**Result:**
- Client requests to `/api/missions/*` hit NEW router
- NEW router creates missions in `brain:missions:mission:{id}` keys
- LEGACY worker reads from MissionQueue (different keys)
- **Missions are created but NEVER executed** ❌

---

## Storage Collision

**NEW Implementation:**
```python
# app/modules/missions/service.py
MISSION_KEY_PREFIX = "brain:missions:mission:"  # {id} → JSON
MISSION_INDEX_KEY = "brain:missions:index"      # Set
MISSION_LOG_PREFIX = "brain:missions:log:"      # {id} → List
MISSION_STATS_KEY = "brain:missions:stats"      # JSON
```

**LEGACY Implementation:**
```python
# backend/modules/missions/queue.py (inferred)
Queue key: likely "brain:missions:queue"  # ZSET with priority scores
```

**Problem:** Different key spaces → **NO DATA SHARING** → Systems don't see each other.

---

## Worker Analysis

**LEGACY Worker:**
```python
# backend/main.py:132-149
if os.getenv("ENABLE_MISSION_WORKER", "true").lower() == "true":
    mission_worker_task = await start_mission_worker()
    logger.info("✅ Mission worker started")
```

**Status:** ✅ Running
**Processing:** MissionQueue (LEGACY keys)
**Problem:** Can't see NEW missions (different Redis keys)

**NEW "Executor":**
```python
# app/modules/missions/executor.py:10-34
class MissionExecutor:
    async def execute(self, mission: Mission) -> None:
        await asyncio.sleep(1.0)  # Mock work
        await update_status(mission.id, MissionStatus.COMPLETED)
```

**Status:** ❌ Mock implementation
**Trigger:** `asyncio.create_task()` in router (fire-and-forget)
**Problem:** No queue, no priority, no retry, just sleeps

---

## EventStream Coverage

### LEGACY Implementation

**File:** `backend/modules/missions/mission_control_runtime.py`

**Current Coverage:**
```python
# Lines 24-29: Imports
from backend.mission_control_core.core import (
    EventStream,
    Event,
    EventType,
    emit_task_event,
)

# Line 64: Initialization
self.event_stream = EventStream(redis_url=self.redis_url)
await self.event_stream.initialize()

# Lines 92-100: Event Publishing
await emit_task_event(
    self.event_stream,
    task_id=result.mission_id,
    event_type=EventType.TASK_CREATED,
    source=created_by,
    mission_id=result.mission_id,
    extra_data={
        "mission_type": payload.type,
        "priority": payload.priority.name,
    }
)
```

**Events Published:**
- ✅ `TASK_CREATED` - When mission enqueued

**Missing Events (Execution Lifecycle):**
- ❌ `TASK_STARTED` - When worker picks up mission
- ❌ `TASK_COMPLETED` - When mission succeeds
- ❌ `TASK_FAILED` - When mission fails
- ❌ `TASK_RETRIED` - When mission retries
- ❌ `TASK_CANCELLED` - When mission cancelled

**Estimated Missing:** 5 event types

### NEW Implementation

**EventStream Coverage:** ❌ **NONE** - No imports, no integration

---

## Decision Matrix

| Criteria | LEGACY | NEW | Merge Both |
|----------|--------|-----|------------|
| **Functional** | ✅ Yes | ❌ No (broken) | ⚠️ After effort |
| **EventStream** | ✅ Partial (1 event) | ❌ None | ✅ After migration |
| **Queue System** | ✅ Redis ZSET | ❌ None | ✅ From LEGACY |
| **Worker** | ✅ Background worker | ❌ Mock executor | ✅ From LEGACY |
| **Modern REST** | ⚠️ Basic | ✅ Full featured | ✅ From NEW |
| **Security/Auth** | ❌ None | ✅ get_current_principal | ✅ From NEW |
| **API Coverage** | ✅ Full (8 endpoints) | ⚠️ Partial (7 endpoints) | ✅ Combined |
| **Migration Effort** | 🟢 Low (4-6h) | 🔴 High (12-16h) | 🔴 Very High (20-30h) |
| **Risk** | 🟢 Low (already works) | 🔴 High (full rebuild) | 🔴 Very High (complexity) |
| **Production Ready** | ✅ Yes (in use) | ❌ No (never worked) | ⚠️ After testing |

---

## Options Analysis

### Option A: Migrate LEGACY ✅ **RECOMMENDED**

**Description:** Complete EventStream migration for LEGACY implementation.

**Tasks:**
1. Disable NEW router (comment out `main.py:245`)
2. Verify LEGACY router discovery
3. Add 5 missing event types (TASK_STARTED, COMPLETED, FAILED, RETRIED, CANCELLED)
4. Update worker to publish execution events
5. Write 15+ tests for all event types
6. Update documentation
7. Remove NEW implementation (cleanup)

**Effort:** 4-6 hours

**Pros:**
- ✅ Already functional (queue + worker)
- ✅ Partially migrated (TASK_CREATED exists)
- ✅ Low risk (extends working system)
- ✅ Fast delivery
- ✅ Production-ready (already in use)

**Cons:**
- ❌ No security/auth integration
- ❌ Less modern REST design
- ❌ Loses NEW's cleaner models

**Risk:** 🟢 **LOW**

---

### Option B: Migrate NEW

**Description:** Add EventStream, queue, worker to NEW implementation.

**Tasks:**
1. Integrate EventStream into service.py
2. Build queue system (Redis ZSET)
3. Build background worker
4. Replace mock executor with real execution
5. Add 6+ event types
6. Write 18+ tests
7. Migrate data from LEGACY to NEW keys
8. Disable LEGACY worker

**Effort:** 12-16 hours

**Pros:**
- ✅ Modern REST design
- ✅ Security/auth integration
- ✅ Cleaner models

**Cons:**
- ❌ Full rebuild required
- ❌ NEW never worked (untested architecture)
- ❌ Data migration complexity
- ❌ High risk (greenfield)
- ❌ Longer delivery time

**Risk:** 🔴 **HIGH**

---

### Option C: Merge Both

**Description:** Combine NEW API design with LEGACY backend.

**Tasks:**
1. Analyze incompatibilities
2. Design unified data model
3. Refactor NEW router to use LEGACY backend
4. Migrate LEGACY to use NEW models
5. Merge Redis key spaces
6. Migrate EventStream to unified system
7. Add security to LEGACY
8. Comprehensive testing
9. Data migration scripts

**Effort:** 20-30 hours

**Pros:**
- ✅ Best of both worlds
- ✅ Modern API + working backend
- ✅ Full feature set

**Cons:**
- ❌ Very high complexity
- ❌ Long delivery time
- ❌ High risk (merge conflicts)
- ❌ Extensive testing required

**Risk:** 🔴 **VERY HIGH**

---

### Option D: Quick Fix (Bridge Solution)

**Description:** Make NEW router use LEGACY backend.

**Tasks:**
1. Modify NEW service.py to call LEGACY runtime
2. Keep NEW router for API surface
3. Redirect to LEGACY queue/worker
4. Add EventStream passthrough

**Effort:** 6-8 hours

**Pros:**
- ✅ Quick fix
- ✅ Preserves NEW API design
- ✅ Uses working LEGACY backend

**Cons:**
- ❌ Band-aid solution
- ❌ Technical debt
- ❌ Confusing architecture
- ❌ Still needs full migration later

**Risk:** 🟡 **MEDIUM**

---

## Final Decision: **Option A - Migrate LEGACY** ✅

### Rationale

1. **Functionality First**
   - LEGACY is the ONLY working implementation
   - NEW creates orphaned missions (user-facing bug)
   - Can't ship broken NEW in Sprint 2

2. **EventStream Readiness**
   - LEGACY already has EventStream (1/6 events)
   - Adding 5 events is straightforward
   - NEW requires ground-up integration

3. **Risk vs Reward**
   - LEGACY: Low risk, fast delivery (4-6h)
   - NEW: High risk, long delivery (12-16h), untested
   - Sprint 2 goal is EventStream migration, not architecture overhaul

4. **Production Impact**
   - LEGACY is likely already in production use
   - NEW has never worked (no user impact from removal)
   - Minimal disruption to existing workflows

5. **Sprint Velocity**
   - Sprint 2 has 3-4 more modules to migrate after missions
   - Can't spend 20-30h on merge experiment
   - Need fast, reliable delivery

### Trade-offs Accepted

- ❌ Won't get NEW's security/auth integration (defer to Sprint 3)
- ❌ Won't get NEW's cleaner REST design (acceptable)
- ❌ Technical debt remains (but working system > broken modern code)

### Future Work (Post-Sprint 2)

- **Sprint 3 or later:** Add security/auth to LEGACY
- **Sprint 4 or later:** Refactor LEGACY to modern REST patterns
- **Sprint 5 or later:** Remove NEW implementation entirely

---

## Implementation Plan

### Phase 1: Disable NEW Router (30 min)

**File:** `backend/main.py`

```python
# Line 245: Comment out NEW router
# app.include_router(app_missions_router, tags=["missions"])  # DISABLED: Route collision with LEGACY
```

**Verify:** `curl http://localhost:8000/api/missions/info` returns LEGACY response

---

### Phase 2: Analyze LEGACY EventStream (1h)

**Tasks:**
1. Read `backend/modules/missions/worker.py` - identify execution lifecycle
2. Read `backend/modules/missions/queue.py` - identify event trigger points
3. Map event types to execution states
4. Document current vs required events

**Deliverable:** Event coverage analysis document

---

### Phase 3: Add Missing Events (2-3h)

**Events to Add:**

1. **TASK_STARTED** (`EventType.TASK_STARTED`)
   - When: Worker picks mission from queue
   - Location: `worker.py` - start of execution
   - Payload: `{mission_id, type, priority, started_at, worker_id}`

2. **TASK_COMPLETED** (`EventType.TASK_COMPLETED`)
   - When: Mission execution succeeds
   - Location: `worker.py` - after successful execution
   - Payload: `{mission_id, duration_ms, result_summary, completed_at}`

3. **TASK_FAILED** (`EventType.TASK_FAILED`)
   - When: Mission execution fails
   - Location: `worker.py` - exception handler
   - Payload: `{mission_id, error, retry_count, failed_at, will_retry}`

4. **TASK_RETRIED** (`EventType.TASK_RETRIED`)
   - When: Mission re-enqueued after failure
   - Location: `worker.py` - retry logic
   - Payload: `{mission_id, retry_count, max_retries, next_attempt_at}`

5. **TASK_CANCELLED** (`EventType.TASK_CANCELLED`)
   - When: Mission cancelled via API
   - Location: `api/routes/missions.py` - cancel endpoint (if exists)
   - Payload: `{mission_id, cancelled_by, cancelled_at, reason}`

**Pattern:** Use existing `emit_task_event()` helper from `mission_control_runtime.py`

---

### Phase 4: Tests (1-2h)

**Test File:** `backend/tests/test_missions_events.py`

**Coverage:**
- ✅ TASK_CREATED event published on enqueue
- ✅ TASK_STARTED event published when worker picks mission
- ✅ TASK_COMPLETED event published on success
- ✅ TASK_FAILED event published on exception
- ✅ TASK_RETRIED event published on retry
- ✅ TASK_CANCELLED event published on cancel (if endpoint exists)
- ✅ Event envelope structure (Charter v1.0)
- ✅ Non-blocking event publishing
- ✅ Graceful degradation without EventStream

**Estimated Tests:** 15-18 tests

---

### Phase 5: Documentation (1h)

**Files to Update:**

1. **`backend/modules/missions/README.md`** (create)
   - Overview
   - Architecture diagram
   - EventStream integration
   - Event types (6 total)
   - Usage examples
   - Consumer guidelines

2. **`backend/modules/missions/EVENTS.md`** (create)
   - Complete event specifications
   - Payload schemas
   - Consumer recommendations

3. **`SPRINT2_MISSIONS_MIGRATION.md`** (create)
   - Migration report
   - Changes made
   - Testing results
   - Metrics

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Disable NEW | 30 min | None |
| Phase 2: Analysis | 1h | Phase 1 |
| Phase 3: Add Events | 2-3h | Phase 2 |
| Phase 4: Tests | 1-2h | Phase 3 |
| Phase 5: Documentation | 1h | Phase 4 |
| **Total** | **5-7h** | Sequential |

**Buffer:** +1h for unexpected issues
**Final Estimate:** **6-8 hours**

---

## Success Criteria

### Must Have (Sprint 2)
- ✅ NEW router disabled (no route collision)
- ✅ LEGACY router serving all requests
- ✅ 6 event types published (CREATED, STARTED, COMPLETED, FAILED, RETRIED, CANCELLED)
- ✅ 15+ tests passing
- ✅ Charter v1.0 compliance
- ✅ Non-blocking event publishing
- ✅ Documentation complete

### Nice to Have (Future)
- ⚪ Security/auth integration (defer to Sprint 3)
- ⚪ Modern REST refactoring (defer to Sprint 4)
- ⚪ NEW implementation removal (defer to Sprint 5)

---

## Appendix: Key Files

### LEGACY Implementation
```
backend/modules/missions/
├── mission_control_runtime.py   # EventStream integration ✅
├── queue.py                     # Redis ZSET queue
├── worker.py                    # Background worker ⚠️ NEEDS EVENTS
├── models.py                    # Data models
├── schemas.py                   # API schemas
└── (to create)
    ├── README.md               # Documentation
    └── EVENTS.md               # Event specifications

backend/api/routes/
└── missions.py                 # API router (auto-discovered)

backend/tests/
└── test_missions_events.py     # EventStream tests (to create)
```

### NEW Implementation (TO BE DISABLED)
```
app/modules/missions/
├── service.py      # ❌ Direct Redis, no EventStream
├── executor.py     # ❌ Mock executor
├── router.py       # ❌ Broken (creates orphaned missions)
└── models.py       # Modern models (could salvage later)
```

### Integration Points
```
backend/main.py
├── Line 34:  Worker import
├── Line 66:  NEW router import (DISABLE)
├── Line 135: Worker startup
├── Line 148: Worker shutdown
├── Line 245: NEW router registration (COMMENT OUT) ❌
└── Line 248: LEGACY router auto-discovery ✅
```

---

## Risks & Mitigation

### Risk 1: LEGACY might have undocumented dependencies
**Likelihood:** Medium
**Impact:** Medium
**Mitigation:** Thorough testing before disabling NEW

### Risk 2: Existing users might rely on NEW API endpoints
**Likelihood:** Low (NEW never worked)
**Impact:** Low
**Mitigation:** Check logs for NEW endpoint usage before disabling

### Risk 3: EventStream changes might break existing TASK_CREATED consumers
**Likelihood:** Low
**Impact:** Medium
**Mitigation:** Maintain backward compatibility, add new events incrementally

---

## Approval

**Recommended By:** Sprint 2 Migration Team
**Reviewed By:** [Pending]
**Approved By:** [Pending]
**Date:** 2025-12-28

---

**Next Steps:** Proceed to Phase 1 - Disable NEW Router
