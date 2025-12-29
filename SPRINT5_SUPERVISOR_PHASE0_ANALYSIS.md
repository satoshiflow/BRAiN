# Sprint 5 Phase 0: Supervisor Module Analysis

**Analysis Date:** December 29, 2025
**Module:** Supervisor
**Sprint:** Sprint 5 - Resource Management & Hardware (Module 3/4)
**Status:** Individual module (not combined)

---

## Executive Summary

Pre-migration analysis for the **Supervisor** module. This module coordinates mission execution and agent management, providing aggregated status information. Module is small-to-medium size (46 lines service + 36 lines router = 82 lines total). Estimated migration time: **1.5 hours**.

### Module Overview

| Aspect | Details |
|--------|---------|
| **Purpose** | Mission and agent supervision/coordination |
| **Files** | 3 (service.py, router.py, schemas.py) |
| **Total Lines** | 82 lines (service 46 + router 36) |
| **Complexity** | SMALL-MEDIUM |
| **Dependencies** | Missions module (imports get_stats) |

---

## Module Structure

### Location
`backend/app/modules/supervisor/`

### Files
```
supervisor/
├── __init__.py         # Module exports
├── schemas.py          # Pydantic models (32 lines)
├── service.py          # Business logic (46 lines)
└── router.py           # API endpoints (36 lines)
```

### Architecture Type
**Functional module** - No classes, function-based service layer

---

## Current Implementation

### service.py (46 lines)

```python
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from app.modules.missions.models import MissionStatus
from app.modules.missions.service import get_stats
from .schemas import AgentStatus, SupervisorHealth, SupervisorStatus


async def get_health() -> SupervisorHealth:
    return SupervisorHealth(status="ok", timestamp=datetime.now(timezone.utc))


async def get_status() -> SupervisorStatus:
    stats_response = await get_stats()
    stats = stats_response.stats

    def count(status: MissionStatus) -> int:
        return int(stats.by_status.get(status, 0))

    total = int(stats.total)
    running = count(MissionStatus.RUNNING)
    pending = count(MissionStatus.PENDING)
    completed = count(MissionStatus.COMPLETED)
    failed = count(MissionStatus.FAILED)
    cancelled = count(MissionStatus.CANCELLED)

    agents: List[AgentStatus] = []

    return SupervisorStatus(
        status="ok",
        timestamp=datetime.now(timezone.utc),
        total_missions=total,
        running_missions=running,
        pending_missions=pending,
        completed_missions=completed,
        failed_missions=failed,
        cancelled_missions=cancelled,
        agents=agents,
    )


async def list_agents() -> List[AgentStatus]:
    return []
```

**Analysis:**
- **Type:** Functional module (no classes)
- **Async:** Already fully async
- **External Dependencies:**
  - `app.modules.missions.models.MissionStatus`
  - `app.modules.missions.service.get_stats`
- **State:** Stateless (aggregates from missions module)
- **Complexity:** Medium (aggregates mission statistics)

### router.py (36 lines)

```python
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends

from app.core.security import Principal, get_current_principal
from .schemas import AgentStatus, SupervisorHealth, SupervisorStatus
from .service import get_health, get_status, list_agents

router = APIRouter(
    prefix="/api/supervisor",
    tags=["supervisor"],
)


@router.get("/health", response_model=SupervisorHealth)
async def supervisor_health(
    principal: Principal = Depends(get_current_principal),
) -> SupervisorHealth:
    return await get_health()


@router.get("/status", response_model=SupervisorStatus)
async def supervisor_status(
    principal: Principal = Depends(get_current_principal),
) -> SupervisorStatus:
    return await get_status()


@router.get("/agents", response_model=List[AgentStatus])
async def supervisor_agents(
    principal: Principal = Depends(get_current_principal),
) -> List[AgentStatus]:
    return await list_agents()
```

**Analysis:**
- **Endpoints:** 3 (GET /health, GET /status, GET /agents)
- **Security:** Uses Principal authentication on all endpoints
- **Async:** Already fully async
- **Pattern:** Standard FastAPI router with dependency injection

### schemas.py (32 lines)

```python
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AgentStatus(BaseModel):
    id: str
    name: str
    role: Optional[str] = None
    state: str
    last_heartbeat: Optional[datetime] = None
    missions_running: int = 0


class SupervisorHealth(BaseModel):
    status: str
    timestamp: datetime


class SupervisorStatus(BaseModel):
    status: str
    timestamp: datetime
    total_missions: int
    running_missions: int
    pending_missions: int
    completed_missions: int
    failed_missions: int
    cancelled_missions: int
    agents: List[AgentStatus] = []
```

**Analysis:**
- Well-defined Pydantic models
- SupervisorStatus contains rich mission statistics
- AgentStatus prepared for future agent tracking

---

## Event Opportunities

### 1. supervisor.health_checked (OPTIONAL)
**When:** GET /api/supervisor/health
**Priority:** LOW (optional telemetry)
**Payload:**
```json
{
  "status": "ok",
  "checked_at": 1703001234.567
}
```

**Use Cases:**
- Monitor supervisor health check frequency
- Track supervisor availability
- Uptime metrics

---

### 2. supervisor.status_queried (MEDIUM PRIORITY)
**When:** GET /api/supervisor/status
**Priority:** MEDIUM (valuable operational insight)
**Payload:**
```json
{
  "total_missions": 150,
  "running_missions": 5,
  "pending_missions": 3,
  "completed_missions": 130,
  "failed_missions": 10,
  "cancelled_missions": 2,
  "agent_count": 0,
  "queried_at": 1703001234.567
}
```

**Use Cases:**
- **Dashboard updates** - Track when UI queries supervisor status
- **Load monitoring** - Detect high-frequency polling
- **Audit trail** - Who's monitoring the system
- **Performance analysis** - Query patterns and response times

**Why Important:**
- Aggregates mission statistics (expensive operation)
- Called frequently by monitoring dashboards
- Reveals system activity patterns

---

### 3. supervisor.agents_listed (OPTIONAL)
**When:** GET /api/supervisor/agents
**Priority:** LOW (stub implementation)
**Payload:**
```json
{
  "agent_count": 0,
  "queried_at": 1703001234.567
}
```

**Use Cases:**
- Track agent listing requests
- Monitor stub endpoint usage
- Prepare for future agent management

**Note:** Currently returns empty list - low priority until implemented

---

## Event Count Summary

| Event Type | Priority | Implementation Recommendation |
|------------|----------|-------------------------------|
| supervisor.health_checked | OPTIONAL | Skip or minimal |
| supervisor.status_queried | MEDIUM | **Implement** (valuable) |
| supervisor.agents_listed | OPTIONAL | Skip (stub) |

**Recommended:** Implement **1 primary event** (status_queried) + optionally health_checked

---

## Dependencies & Import Considerations

### External Dependencies

**Issue:** Supervisor imports from Missions module:
```python
from app.modules.missions.models import MissionStatus
from app.modules.missions.service import get_stats
```

**Import Path Pattern:**
- Uses `app.modules.missions` (absolute import)
- Should be changed to `backend.app.modules.missions` for consistency

**Fix Required:** Update import paths to match project structure:
```python
# Before:
from app.modules.missions.models import MissionStatus
from app.modules.missions.service import get_stats

# After (option 1 - relative from app):
from ..missions.models import MissionStatus
from ..missions.service import get_stats

# After (option 2 - absolute):
from backend.app.modules.missions.models import MissionStatus
from backend.app.modules.missions.service import get_stats
```

**Recommendation:** Use relative imports (option 1) for consistency with Credits/Hardware modules

---

## EventStream Integration Strategy

### Pattern Selection

Supervisor is **functional** (no classes), so we'll use the **Module-Level EventStream Pattern**:

```python
# Module-level state
_event_stream: Optional["EventStream"] = None

def set_event_stream(stream: "EventStream") -> None:
    """Initialize EventStream for this module"""
    global _event_stream
    _event_stream = stream

async def _emit_event_safe(event_type: str, payload: dict) -> None:
    """Emit event with error handling (non-blocking)"""
    global _event_stream
    if _event_stream is None or Event is None:
        logger.debug("[SupervisorService] EventStream not available, skipping event")
        return

    try:
        event = Event(type=event_type, source="supervisor_service",
                     target=None, payload=payload)
        await _event_stream.publish(event)
    except Exception as e:
        logger.error(f"[SupervisorService] Event publishing failed: {e}", exc_info=True)
```

Same pattern as Credits, Hardware, Metrics, Telemetry modules.

---

## Implementation Plan

### Integration Points

#### 1. service.py

**Add at module level (after imports):**
```python
import logging
import time

logger = logging.getLogger(__name__)

# Optional EventStream import (Sprint 5)
try:
    from backend.app.core.event_stream import EventStream, Event
except ImportError:
    EventStream = None
    Event = None

# Module-level EventStream
_event_stream: Optional["EventStream"] = None

def set_event_stream(stream: "EventStream") -> None:
    global _event_stream
    _event_stream = stream

async def _emit_event_safe(event_type: str, payload: dict) -> None:
    # ... implementation
```

**Modify get_health() (optional):**
```python
async def get_health() -> SupervisorHealth:
    result = SupervisorHealth(status="ok", timestamp=datetime.now(timezone.utc))

    # EVENT: supervisor.health_checked (optional)
    await _emit_event_safe("supervisor.health_checked", {
        "status": result.status,
        "checked_at": result.timestamp.timestamp(),
    })

    return result
```

**Modify get_status() (recommended):**
```python
async def get_status() -> SupervisorStatus:
    stats_response = await get_stats()
    stats = stats_response.stats

    # ... existing logic to build result ...

    result = SupervisorStatus(...)

    # EVENT: supervisor.status_queried (medium priority)
    await _emit_event_safe("supervisor.status_queried", {
        "total_missions": result.total_missions,
        "running_missions": result.running_missions,
        "pending_missions": result.pending_missions,
        "completed_missions": result.completed_missions,
        "failed_missions": result.failed_missions,
        "cancelled_missions": result.cancelled_missions,
        "agent_count": len(result.agents),
        "queried_at": time.time(),
    })

    return result
```

**Modify list_agents() (optional):**
```python
async def list_agents() -> List[AgentStatus]:
    result = []

    # EVENT: supervisor.agents_listed (optional)
    await _emit_event_safe("supervisor.agents_listed", {
        "agent_count": len(result),
        "queried_at": time.time(),
    })

    return result
```

**Lines Added:** ~70-80 lines

---

## Migration Complexity Assessment

### Complexity Breakdown

| Aspect | Complexity | Notes |
|--------|------------|-------|
| Code Size | SMALL-MEDIUM | 82 lines total |
| Async Conversion | NONE | Already fully async |
| Event Integration | MEDIUM | 1-3 events, mission stats |
| Import Fixes | LOW | Update app.modules → relative |
| Testing | MEDIUM | Mock missions.get_stats |
| **Overall** | **MEDIUM** | **~1.5 hours** |

### Time Estimate

| Phase | Time | Notes |
|-------|------|-------|
| 0 - Analysis | 15 min | ✅ Current phase |
| 1 - Event Design | 15 min | Define 1-3 event types |
| 2 - Implementation | 30 min | Add EventStream + events |
| 3 - Consumers | - | Skipped |
| 4 - Testing | 25 min | Mock missions dependency |
| 5 - Documentation | 15 min | Summary + commit |
| **Total** | **1.5 hours** | |

---

## Testing Strategy

### Test Requirements

**Mock Dependencies:**
1. **MockEventStream** - Capture events
2. **MockEvent** - Charter v1.0 compliant
3. **Mock missions.get_stats** - Return fake mission stats

**Example Mock:**
```python
class MockMissionStats:
    def __init__(self):
        self.total = 150
        self.by_status = {
            MissionStatus.PENDING: 3,
            MissionStatus.RUNNING: 5,
            MissionStatus.COMPLETED: 130,
            MissionStatus.FAILED: 10,
            MissionStatus.CANCELLED: 2,
        }
        self.last_updated = time.time()

class MockStatsResponse:
    def __init__(self):
        self.stats = MockMissionStats()

async def mock_get_stats():
    return MockStatsResponse()
```

### Test Cases

1. ✅ `test_supervisor_health_checked` (if implemented)
   - Call get_health()
   - Verify supervisor.health_checked event

2. ✅ `test_supervisor_status_queried`
   - Mock missions.get_stats
   - Call get_status()
   - Verify supervisor.status_queried event
   - Verify mission counts in payload

3. ✅ `test_supervisor_agents_listed` (if implemented)
   - Call list_agents()
   - Verify supervisor.agents_listed event

4. ✅ `test_supervisor_charter_compliance`
   - Generate all events
   - Verify Charter v1.0 compliance

**Total Tests:** 3-4 tests

---

## Risks & Mitigations

### Risk 1: Missions Module Dependency
**Risk:** Supervisor imports from Missions module (not yet migrated in Sprint 5)
**Impact:** Tests need to mock missions.get_stats
**Mitigation:**
- Use pytest monkeypatch to mock get_stats
- Independent of Missions migration status

### Risk 2: Import Path Inconsistency
**Risk:** Uses `app.modules.missions` instead of relative imports
**Impact:** May cause import errors in tests
**Mitigation:**
- Update to relative imports: `from ..missions.models import MissionStatus`
- Or update to `backend.app.modules.missions`

### Risk 3: Agent Management Stub
**Risk:** list_agents() returns empty list (not implemented)
**Impact:** Event has minimal value
**Mitigation:**
- Make supervisor.agents_listed OPTIONAL
- Document as future-ready

---

## Success Criteria

### Phase 0 (Analysis)
- ✅ Module structure documented
- ✅ Event opportunities identified (1-3 events)
- ✅ Integration strategy defined
- ✅ Dependencies analyzed
- ✅ Time estimate calculated

### Phase 1 (Event Design)
- [ ] EVENTS.md created with 1-3 event types
- [ ] Event schemas documented
- [ ] Charter v1.0 compliance verified

### Phase 2 (Implementation)
- [ ] Module-level EventStream added (~80 lines)
- [ ] Import paths fixed (relative imports)
- [ ] Events integrated into service functions
- [ ] Non-blocking event publishing implemented

### Phase 4 (Testing)
- [ ] 3-4 tests written and passing
- [ ] missions.get_stats mocked
- [ ] Charter compliance automated

### Phase 5 (Documentation)
- [ ] Migration summary created
- [ ] Code changes documented
- [ ] Lessons learned captured
- [ ] Git commit and push

---

## Next Steps

1. **Phase 1:** Create EVENTS.md for Supervisor module
2. **Phase 2:** Implement EventStream integration
3. **Phase 4:** Write test suite with mocked dependencies
4. **Phase 5:** Document and commit

**Estimated Total Time:** 1.5 hours

---

## Notes

- **Primary Event:** `supervisor.status_queried` - Most valuable for monitoring
- **Optional Events:** health_checked, agents_listed (low priority)
- **Import Fix Required:** Change `app.modules.missions` to relative imports
- **Missions Dependency:** Mock in tests, no impact on implementation
- **Pattern:** Module-level EventStream (consistent with Sprint 4 & 5)

---

**Analysis Completed:** December 29, 2025
**Status:** ✅ Ready for Phase 1 (Event Design)
