# Sprint 5 Phase 0: Missions Module Analysis

**Analysis Date:** December 29, 2025
**Module:** Missions
**Sprint:** Sprint 5 - Resource Management & Hardware (Module 4/4 - Final)
**Status:** Individual module

---

## Executive Summary

Pre-migration analysis for the **Missions** module - the largest and most complex module in Sprint 5. This module provides the core mission management system with Redis-based CRUD operations, logging, and statistics. Module is **LARGE** size (164 lines service + 113 lines router = 277 lines total). Estimated migration time: **2.5 hours**.

### Module Overview

| Aspect | Details |
|--------|---------|
| **Purpose** | Mission lifecycle management and tracking |
| **Files** | 4 (service.py, router.py, models.py, executor.py) |
| **Total Lines** | 277 lines (service 164 + router 113) |
| **Complexity** | **LARGE** (Redis CRUD, stats, logging) |
| **Dependencies** | Redis, Security (Principal) |

---

## Module Structure

### Location
`backend/app/modules/missions/`

### Files
```
missions/
├── __init__.py         # Module exports
├── models.py           # Pydantic models (60 lines)
├── service.py          # Business logic (164 lines)
├── router.py           # API endpoints (113 lines)
├── executor.py         # Mission execution logic
└── schemas.py          # Additional schemas (if exists)
```

### Architecture Type
**Functional module** - No classes, function-based service layer with Redis storage

---

## Current Implementation

### service.py (164 lines)

**Public Functions (6):**

```python
async def create_mission(payload: MissionCreate) -> Mission:
    """Create new mission in Redis"""
    # 1. Generate mission ID
    # 2. Create Mission object with PENDING status
    # 3. Save to Redis (SET + SADD to index)
    # 4. Update statistics
    # 5. Add log entry
    # 6. Return mission

async def get_mission(mission_id: str) -> Optional[Mission]:
    """Retrieve mission by ID from Redis"""

async def list_missions(status: Optional[MissionStatus] = None) -> MissionListResponse:
    """List all missions (with optional status filter)"""
    # 1. Get all mission IDs from index (SMEMBERS)
    # 2. Fetch each mission
    # 3. Filter by status if provided
    # 4. Sort by created_at (newest first)
    # 5. Return list

async def append_log_entry(mission_id: str, entry: MissionLogEntry) -> None:
    """Append log entry to mission's log (Redis LIST)"""

async def get_log(mission_id: str) -> MissionLogResponse:
    """Retrieve mission's complete log"""

async def update_status(mission_id: str, status: MissionStatus) -> Optional[Mission]:
    """Update mission status"""
    # 1. Get current mission
    # 2. Store old status
    # 3. Update to new status
    # 4. Save to Redis
    # 5. Update statistics
    # 6. Add log entry
    # 7. Return updated mission

async def get_stats() -> MissionStatsResponse:
    """Get mission statistics (total, by_status)"""
```

**Private Functions (2):**
```python
async def _update_stats_on_create(redis, status) -> None:
    """Increment total and status count"""

async def _update_stats_on_status_change(redis, old_status, new_status) -> None:
    """Decrement old status, increment new status"""
```

**Analysis:**
- **Type:** Functional module (no classes)
- **Async:** Already fully async
- **Storage:** Redis (strings, sets, lists)
- **State:** Stateless (all state in Redis)
- **Complexity:** High (CRUD operations, statistics tracking, logging)

**Redis Keys:**
- `brain:missions:mission:{id}` - Mission data (JSON string)
- `brain:missions:index` - Set of all mission IDs
- `brain:missions:log:{id}` - Mission log entries (LIST)
- `brain:missions:stats` - Mission statistics (JSON string)

### router.py (113 lines)

**Endpoints (9):**
```python
GET /api/missions/health               # Health check
GET /api/missions                      # List missions
POST /api/missions                     # Create mission
GET /api/missions/{id}                 # Get mission
POST /api/missions/{id}/status         # Update status
POST /api/missions/{id}/log            # Append log entry
GET /api/missions/{id}/log             # Get mission log
GET /api/missions/stats/overview       # Get statistics
POST /api/missions/{id}/execute        # Execute mission
```

**Analysis:**
- **Security:** All endpoints use Principal authentication (except health)
- **Async:** Already fully async
- **Error Handling:** HTTPException for 404s
- **Background Tasks:** Uses asyncio.create_task for mission execution

**Import Issue Found:**
```python
# Line 8 - WRONG:
from app.core.security import Principal, get_current_principal

# Should be:
from ...core.security import Principal, get_current_principal
```

---

## Event Opportunities

### Primary Events (HIGH PRIORITY)

#### 1. mission.created (HIGH)
**When:** POST /api/missions (after create_mission)
**Why Important:**
- Critical lifecycle event
- Triggers workflows, notifications
- Audit trail for mission creation

**Payload:**
```json
{
  "mission_id": "uuid",
  "name": "Mission name",
  "description": "Description",
  "status": "PENDING",
  "created_by": "principal_id",
  "created_at": 1703001234.567
}
```

#### 2. mission.status_changed (HIGH)
**When:** POST /api/missions/{id}/status (after update_status)
**Why Important:**
- Most critical event (status transitions are key to mission lifecycle)
- Enables workflow automation
- Track mission progress
- Alert on failures

**Payload:**
```json
{
  "mission_id": "uuid",
  "old_status": "PENDING",
  "new_status": "RUNNING",
  "changed_at": 1703001234.567
}
```

**Status Transitions:**
- PENDING → RUNNING (mission started)
- RUNNING → COMPLETED (mission succeeded)
- RUNNING → FAILED (mission failed)
- ANY → CANCELLED (mission cancelled)

#### 3. mission.log_appended (MEDIUM)
**When:** POST /api/missions/{id}/log (after append_log_entry)
**Why Important:**
- Track mission progress
- Debug issues
- Audit trail

**Payload:**
```json
{
  "mission_id": "uuid",
  "log_level": "info",
  "message": "Step completed",
  "appended_at": 1703001234.567
}
```

### Secondary Events (OPTIONAL)

#### 4. mission.stats_queried (OPTIONAL)
**When:** GET /api/missions/stats/overview
**Why:** Track dashboard queries

#### 5. mission.retrieved (OPTIONAL)
**When:** GET /api/missions/{id}
**Why:** Monitor mission access patterns

#### 6. mission.list_queried (OPTIONAL)
**When:** GET /api/missions
**Why:** Track list queries

**Recommendation:** Implement **3 primary events** (created, status_changed, log_appended)

---

## Event Count Summary

| Event Type | Priority | Implementation | Value |
|------------|----------|----------------|-------|
| mission.created | **HIGH** | **Required** | Critical lifecycle |
| mission.status_changed | **HIGH** | **Required** | Most important |
| mission.log_appended | MEDIUM | Recommended | Debugging, audit |
| mission.stats_queried | OPTIONAL | Skip | Low value |
| mission.retrieved | OPTIONAL | Skip | Noise |
| mission.list_queried | OPTIONAL | Skip | Noise |

**Recommended:** **3 events** (created, status_changed, log_appended)

---

## EventStream Integration Strategy

### Pattern Selection

Missions is **functional** (no classes), so we'll use the **Module-Level EventStream Pattern**:

```python
import logging
import time

logger = logging.getLogger(__name__)

# Optional EventStream import
try:
    from backend.app.core.event_stream import EventStream, Event
except ImportError:
    EventStream = None
    Event = None

# Module-level state
_event_stream: Optional["EventStream"] = None

def set_event_stream(stream: "EventStream") -> None:
    """Initialize EventStream for this module"""
    global _event_stream
    _event_stream = stream

async def _emit_event_safe(event_type: str, payload: dict) -> None:
    """Emit event with error handling (non-blocking)"""
    # ... implementation
```

Same pattern as all Sprint 5 modules.

---

## Implementation Plan

### Integration Points

#### 1. service.py - Module-Level Setup

**Add at module level (after imports):**
```python
import logging

logger = logging.getLogger(__name__)

# Optional EventStream import (Sprint 5)
try:
    from backend.app.core.event_stream import EventStream, Event
except ImportError:
    EventStream = None
    Event = None

_event_stream: Optional["EventStream"] = None

def set_event_stream(stream: "EventStream") -> None:
    global _event_stream
    _event_stream = stream

async def _emit_event_safe(event_type: str, payload: dict) -> None:
    # ... implementation
```

**Lines Added:** ~50 lines

#### 2. create_mission() - Event Integration

```python
async def create_mission(payload: MissionCreate) -> Mission:
    # ... existing logic to create mission ...

    # EVENT: mission.created (HIGH PRIORITY)
    await _emit_event_safe("mission.created", {
        "mission_id": mission.id,
        "name": mission.name,
        "description": mission.description or "",
        "status": mission.status.value,
        "created_at": mission.created_at,
    })

    return mission
```

**Lines Added:** ~8 lines

#### 3. update_status() - Event Integration

```python
async def update_status(mission_id: str, status: MissionStatus) -> Optional[Mission]:
    mission = await get_mission(mission_id)
    if not mission:
        return None

    old_status = mission.status

    # ... existing logic to update status ...

    # EVENT: mission.status_changed (HIGH PRIORITY)
    await _emit_event_safe("mission.status_changed", {
        "mission_id": mission.id,
        "old_status": old_status.value,
        "new_status": mission.status.value,
        "changed_at": mission.updated_at,
    })

    return mission
```

**Lines Added:** ~8 lines

#### 4. append_log_entry() - Event Integration

```python
async def append_log_entry(mission_id: str, entry: MissionLogEntry) -> None:
    # ... existing logic to append log ...

    # EVENT: mission.log_appended (MEDIUM PRIORITY)
    await _emit_event_safe("mission.log_appended", {
        "mission_id": mission_id,
        "log_level": entry.level,
        "message": entry.message,
        "appended_at": entry.timestamp,
    })
```

**Lines Added:** ~8 lines

### router.py - Import Fix

**Line 8:**
```python
# Before:
from app.core.security import Principal, get_current_principal

# After:
from ...core.security import Principal, get_current_principal
```

**Total Lines Added:** ~74 lines (+45% growth from 164 → 238)

---

## Migration Complexity Assessment

### Complexity Breakdown

| Aspect | Complexity | Notes |
|--------|------------|-------|
| Code Size | **LARGE** | 164 lines service |
| Async Conversion | NONE | Already fully async |
| Event Integration | MEDIUM | 3 events, clear insertion points |
| Import Fixes | LOW | One import in router.py |
| Testing | **MEDIUM-HIGH** | Mock Redis operations |
| **Overall** | **MEDIUM-HIGH** | **~2.5 hours** |

### Time Estimate

| Phase | Time | Notes |
|-------|------|-------|
| 0 - Analysis | 15 min | ✅ Current phase |
| 1 - Event Design | 20 min | 3 event specs |
| 2 - Implementation | 40 min | 3 event integrations + import fix |
| 3 - Consumers | - | Skipped |
| 4 - Testing | 50 min | Mock Redis, test all functions |
| 5 - Documentation | 25 min | Summary + commit |
| **Total** | **2.5 hours** | |

---

## Testing Strategy

### Test Requirements

**Mock Dependencies:**
1. **MockRedis** - Comprehensive Redis mock
   - `.get()`, `.set()`, `.sadd()`, `.smembers()`
   - `.rpush()`, `.lrange()` (for logs)
2. **MockEventStream** - Capture events
3. **MockEvent** - Charter v1.0 compliant

**MockRedis Example:**
```python
class MockRedis:
    def __init__(self):
        self.data = {}      # Key-value store
        self.sets = {}      # Set storage
        self.lists = {}     # List storage

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value):
        self.data[key] = value

    async def sadd(self, key, value):
        if key not in self.sets:
            self.sets[key] = set()
        self.sets[key].add(value)

    async def smembers(self, key):
        return self.sets.get(key, set())

    async def rpush(self, key, value):
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].append(value)

    async def lrange(self, key, start, stop):
        return self.lists.get(key, [])
```

### Test Cases

1. ✅ `test_mission_created`
   - Create mission
   - Verify mission.created event
   - Verify payload (mission_id, name, status, etc.)

2. ✅ `test_mission_status_changed`
   - Create mission
   - Update status PENDING → RUNNING
   - Verify mission.status_changed event
   - Verify old_status and new_status in payload

3. ✅ `test_mission_log_appended`
   - Create mission
   - Append log entry
   - Verify mission.log_appended event
   - Verify log details in payload

4. ✅ `test_mission_status_transitions`
   - Test multiple status changes
   - Verify each transition emits event

5. ✅ `test_mission_charter_compliance`
   - Generate all events
   - Verify Charter v1.0 compliance

**Total Tests:** 5-6 tests

---

## Risks & Mitigations

### Risk 1: Complex Redis Operations
**Risk:** Missions module has complex Redis operations (sets, lists, JSON serialization)
**Impact:** Testing requires comprehensive Redis mocks
**Mitigation:**
- Create full MockRedis with all required operations
- Test each operation independently

### Risk 2: Import Path in Router
**Risk:** Router uses `app.core` instead of relative import
**Impact:** Tests will fail on import
**Mitigation:**
- Fix before testing: `app.core.security` → `...core.security`

### Risk 3: Statistics Update Logic
**Risk:** Statistics are updated in two places (_update_stats_on_create, _update_stats_on_status_change)
**Impact:** Need to ensure events don't duplicate statistics logic
**Mitigation:**
- Events are separate concern (emit after stats update)
- No changes to statistics logic

---

## Success Criteria

### Phase 0 (Analysis)
- ✅ Module structure documented
- ✅ Event opportunities identified (3 primary events)
- ✅ Integration strategy defined
- ✅ Testing strategy defined
- ✅ Time estimate calculated

### Phase 1 (Event Design)
- [ ] EVENTS.md created with 3 event types
- [ ] Event schemas documented
- [ ] Charter v1.0 compliance verified

### Phase 2 (Implementation)
- [ ] Module-level EventStream added (~74 lines)
- [ ] Import path fixed in router.py
- [ ] 3 events integrated into service functions
- [ ] Non-blocking event publishing implemented

### Phase 4 (Testing)
- [ ] 5-6 tests written and passing
- [ ] MockRedis with full operations
- [ ] Charter compliance automated

### Phase 5 (Documentation)
- [ ] Migration summary created
- [ ] Code changes documented
- [ ] Lessons learned captured
- [ ] Git commit and push

---

## Next Steps

1. **Phase 1:** Create EVENTS.md for Missions module
2. **Phase 2:** Implement EventStream integration + import fix
3. **Phase 4:** Write comprehensive test suite
4. **Phase 5:** Document and commit
5. **Sprint 5 Summary:** Create completion summary for all 4 modules

**Estimated Total Time:** 2.5 hours

---

## Notes

- **Largest Sprint 5 Module:** 164 lines (vs 46 Supervisor, 23 Hardware, 16 Credits)
- **Most Complex:** Redis CRUD operations, statistics tracking, logging
- **Most Valuable Events:** mission.created, mission.status_changed (critical lifecycle)
- **Import Fix Required:** router.py line 8 (app.core → ...core)
- **Pattern:** Module-level EventStream (consistent with all Sprint 5 modules)

---

**Analysis Completed:** December 29, 2025
**Status:** ✅ Ready for Phase 1 (Event Design)
