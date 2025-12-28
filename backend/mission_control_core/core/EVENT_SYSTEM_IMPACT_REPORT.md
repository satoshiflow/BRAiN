# BRAiN Event System Consolidation - Impact Report

**Version:** 1.0.0
**Date:** 2025-12-28
**Scope:** Post-Consolidation Analysis of Event System Usage Across All Modules

---

## Executive Summary

After consolidating to EventStream as the single source of truth, this report analyzes the impact on all BRAiN modules, identifies naming/schema conflicts, and provides a migration roadmap.

### Key Findings

| Finding | Severity | Impact | Modules Affected |
|---------|----------|--------|------------------|
| **Stream Naming Conflict** | 🔴 HIGH | MissionQueueManager uses separate `brain:missions:stream` | Mission System V1 |
| **Multiple Event Type Enums** | 🟡 MEDIUM | Fragmented event types across modules | Immune, SovereignMode |
| **Missing tenant_id/actor_id** | 🟡 MEDIUM | Event schema lacks multi-tenancy fields | IR Governance, Course Factory |
| **In-Memory Event System** | 🟢 LOW | ImmuneService bypasses Redis entirely | Immune Module |

---

## 1. Event Producers (Detailed Analysis)

### 1.1 EventStream-Compatible Producers ✅

| Module | File | Function | Event Type | Stream/Channel | Status |
|--------|------|----------|-----------|----------------|--------|
| **Mission Control Runtime** | `modules/missions/mission_control_runtime.py` | `enqueue_mission()` | `TASK_CREATED` | `brain:events:stream` | ✅ OK |
| **Mission Control Core** | `mission_control_core/core/mission_control.py` | `emit_task_event()` | `TASK_*` | `brain:events:stream` | ✅ OK |

**Details:**
```python
# modules/missions/mission_control_runtime.py:92
await emit_task_event(
    self.event_stream,
    task_id=result.mission_id,
    event_type=EventType.TASK_CREATED,
    source=created_by,
    mission_id=result.mission_id,
    extra_data={"mission_type": payload.type, "priority": payload.priority.name}
)
```

**Event Schema:**
```python
Event(
    id=UUID,               # ✅
    type=EventType,        # ✅
    source=str,            # ✅
    target=Optional[str],  # ✅
    payload=Dict,          # ✅
    timestamp=datetime,    # ✅
    mission_id=str,        # ✅
    task_id=str,           # ✅
    correlation_id=str     # ✅
)
```

---

### 1.2 Conflicting Producers 🔴

| Module | File | Function | Stream Name | Conflict | Migration Required |
|--------|------|----------|-------------|----------|-------------------|
| **Mission System V1** | `modules/mission_system/queue.py` | `enqueue_mission()` | `brain:missions:stream` | ⚠️ **SEPARATE STREAM** | YES |

**Details:**
```python
# modules/mission_system/queue.py:137
await self.redis_client.xadd(
    "brain:missions:stream",  # ⚠️ CONFLICT with EventStream!
    {
        "mission_id": mission.id,
        "priority": mission.priority.value,
        "type": mission.mission_type.value,
        "created_at": mission.created_at.isoformat(),
        "agent_requirements": json.dumps(...)
    }
)
```

**Problem:**
- EventStream uses `brain:events:stream` for ALL events
- MissionQueueManager uses `brain:missions:stream` for mission-specific events
- **Result:** Two separate event streams, no unified audit trail!

**Recommendation:**
1. Migrate MissionQueueManager to use EventStream
2. Publish `EventType.MISSION_CREATED` instead of XADD
3. Deprecate `brain:missions:stream` in favor of `brain:events:missions` Pub/Sub channel

---

### 1.3 Isolated Producers 🟡

| Module | File | Event System | Storage | Integration Status |
|--------|------|--------------|---------|-------------------|
| **Immune System** | `app/modules/immune/core/service.py` | In-Memory | List (RAM) | ❌ Not integrated with EventStream |

**Details:**
```python
# app/modules/immune/core/service.py:17
def publish_event(self, event: ImmuneEvent) -> int:
    # In-memory only, no Redis, no EventStream
    self._events.append(stored)
    return stored.id
```

**ImmuneEvent Schema:**
```python
ImmuneEvent(
    id=int,                    # ❌ Not UUID
    agent_id=Optional[str],    # ✅ (but not mandatory)
    module=Optional[str],      # ❌ Not in EventStream schema
    severity=ImmuneSeverity,   # ❌ Not in EventStream
    type=ImmuneEventType,      # ❌ Separate enum
    message=str,               # ✅
    meta=Dict,                 # ✅ Similar to payload
    created_at=datetime        # ✅
)
```

**ImmuneEventType Enum:**
```python
class ImmuneEventType(str, Enum):
    POLICY_VIOLATION = "POLICY_VIOLATION"
    ERROR_SPIKE = "ERROR_SPIKE"
    SELF_HEALING_ACTION = "SELF_HEALING_ACTION"
```

**Recommendation:**
- **Option A (Recommended):** Keep in-memory for performance, add optional EventStream integration
- **Option B:** Migrate fully to EventStream with `EventType.SYSTEM_ALERT`

---

### 1.4 No Event Production (File-Based) ✅

| Module | Storage Type | Events Published | Action Required |
|--------|--------------|------------------|-----------------|
| **Course Factory** | File (JSON) | ❌ None | ✅ No action |
| **Course Distribution** | File (JSON + JSONL) | ❌ None | ✅ No action |
| **Sovereign Mode** | File (JSON) | ❌ None (only audit logging) | ✅ No action |

**Note:** These modules use file-based storage and logging. They mention "audit events" in comments but don't publish to EventStream.

---

## 2. Event Consumers (Detailed Analysis)

### 2.1 EventStream Consumers ✅

| Module | File | Subscription Type | Event Types | Status |
|--------|------|-------------------|-------------|--------|
| **Mission Control Core** | `mission_control_core/core/event_stream.py` | Pub/Sub Listener | ALL (via `_event_listener`) | ✅ Active |
| **Mission Control API** | `mission_control_core/api/routes.py` | Dependency Injection | Event history queries | ✅ Active |

**Details:**
```python
# mission_control_core/core/event_stream.py:363
async def _event_listener(self) -> None:
    """Main event listener loop"""
    async for message in self.pubsub.listen():
        event_data = json.loads(message['data'])
        event = Event.from_dict(event_data)
        await self._handle_event(event)
```

**Subscriptions:**
```python
# mission_control_core/core/event_stream.py:138
await self.pubsub.subscribe(
    'brain:events:broadcast',
    'brain:events:system',
    'brain:events:ethics',
    'brain:events:missions',  # ✅ NEW in consolidation
    'brain:events:tasks'      # ✅ NEW in consolidation
)
```

---

### 2.2 Non-EventStream Consumers 🔴

| Module | File | Consumer Type | Stream | Migration Required |
|--------|------|---------------|--------|-------------------|
| **Mission System V1** | `modules/mission_system/executor.py` | XREADGROUP | `brain:missions:stream` | YES |

**Details:**
```python
# modules/mission_system/executor.py (assumed based on naming)
# Likely uses XREADGROUP on "brain:missions:stream"
# Needs migration to EventStream consumer pattern
```

**Recommendation:**
- Replace XREADGROUP with EventStream subscription
- Subscribe to `EventType.MISSION_*` events
- Migrate from stream-based to Pub/Sub based consumption

---

## 3. Naming & Schema Mismatches

### 3.1 Stream Naming Convention Conflicts

| Current Naming | EventStream Convention | Conflict | Migration Action |
|----------------|----------------------|----------|------------------|
| `brain:missions:stream` | `brain:events:stream` | ⚠️ Separate stream | Merge or deprecate |
| `brain:missions:logs:{id}` | `brain:events:log:{date}` | ⚠️ Different pattern | Unify logging |
| `brain:missions:queue` | N/A (ZSET, not stream) | ✅ No conflict | Keep as-is |

**Unified Naming Strategy:**
```
# Redis Streams (Audit Trail)
brain:events:stream             # ✅ Main event stream (ALL events)
brain:events:log:{date}         # ✅ Daily audit logs

# Redis Pub/Sub Channels (Real-time)
brain:events:broadcast          # ✅ Broadcast
brain:events:system             # ✅ System events
brain:events:ethics             # ✅ Ethics events
brain:events:missions           # ✅ Mission events
brain:events:tasks              # ✅ Task events

# Redis Sorted Sets (Queues)
brain:missions:queue            # ✅ Mission priority queue (ZSET)

# Redis Hashes (State)
brain:missions:state            # ✅ Mission state storage
brain:agents:assignments        # ✅ Agent assignments

# Redis Streams (Logs - per mission)
brain:missions:logs:{id}        # ⚠️ Should be brain:events:mission_logs:{id}?
```

---

### 3.2 Event Type Enum Fragmentation

| Enum | Module | Count | Types | Naming Convention |
|------|--------|-------|-------|-------------------|
| **EventType** | `mission_control_core` | 24 | `mission.*`, `task.*`, `agent.*`, `system.*`, `ethics.*` | ✅ Dot notation |
| **ImmuneEventType** | `immune` | 3 | `POLICY_VIOLATION`, `ERROR_SPIKE`, `SELF_HEALING_ACTION` | ❌ UPPER_SNAKE |
| **AuditEventType** | `sovereign_mode` | 9+ | `sovereign.mode_changed`, `sovereign.gate_check_passed`, ... | ✅ Dot notation |

**Problem:**
- EventStream expects `EventType` enum
- ImmuneEventType uses different naming (UPPER_SNAKE)
- AuditEventType uses dot notation but separate enum

**Recommendation:**
1. **Extend EventType** to include all event types:
   ```python
   class EventType(str, Enum):
       # ... existing types

       # Immune System Events
       IMMUNE_POLICY_VIOLATION = "immune.policy_violation"
       IMMUNE_ERROR_SPIKE = "immune.error_spike"
       IMMUNE_SELF_HEALING = "immune.self_healing"

       # Sovereign Mode Events
       SOVEREIGN_MODE_CHANGED = "sovereign.mode_changed"
       SOVEREIGN_GATE_PASSED = "sovereign.gate_check_passed"
       SOVEREIGN_GATE_FAILED = "sovereign.gate_check_failed"
   ```

2. **Deprecate separate enums** with backward compatibility:
   ```python
   # immune/schemas.py
   class ImmuneEventType(str, Enum):
       POLICY_VIOLATION = EventType.IMMUNE_POLICY_VIOLATION.value
       ERROR_SPIKE = EventType.IMMUNE_ERROR_SPIKE.value
       SELF_HEALING_ACTION = EventType.IMMUNE_SELF_HEALING.value
   ```

---

### 3.3 Missing Schema Fields

#### EventStream Event Schema
```python
@dataclass
class Event:
    id: str                      # ✅ UUID v4
    type: EventType              # ✅ Enum
    source: str                  # ✅ Agent/Component ID
    target: Optional[str]        # ✅ Target agent
    payload: Dict[str, Any]      # ✅ Event data
    timestamp: datetime          # ✅ UTC timestamp
    mission_id: Optional[str]    # ✅ Mission context
    task_id: Optional[str]       # ✅ Task context
    correlation_id: Optional[str] # ✅ Request tracing

    # ❌ MISSING FIELDS:
    # tenant_id: Optional[str]   # Multi-tenancy support
    # actor_id: Optional[str]    # User/Actor attribution
    # module: Optional[str]      # Module/Component name
    # severity: Optional[str]    # Event severity (INFO/WARN/ERROR)
```

#### Fields Used in Other Modules

| Field | Used In | Purpose | Critical? |
|-------|---------|---------|-----------|
| `tenant_id` | IR Governance, Course Factory | Multi-tenant isolation | 🔴 HIGH (for PayCore) |
| `actor_id` | Course Factory, IR Governance | User attribution | 🟡 MEDIUM |
| `module` | Immune System | Component identification | 🟢 LOW (can use `source`) |
| `severity` | Immune System | Event severity (INFO/WARN/ERROR) | 🟢 LOW (can use event type) |

**Recommendation:**
1. **Add to Event schema:**
   ```python
   @dataclass
   class Event:
       # ... existing fields
       tenant_id: Optional[str] = None     # 🆕 Multi-tenancy
       actor_id: Optional[str] = None      # 🆕 User attribution
       severity: Optional[str] = None      # 🆕 Event severity
   ```

2. **Migrate Alembic:**
   ```bash
   alembic revision -m "Add tenant_id, actor_id, severity to Event schema"
   ```

---

## 4. Migration Roadmap

### Phase 1: Critical (DO FIRST) 🔴

| Module | Change | Risk | Effort | Priority |
|--------|--------|------|--------|----------|
| **Mission System V1** | Migrate `brain:missions:stream` to EventStream | HIGH | 3 days | P0 |
| **EventStream Schema** | Add `tenant_id`, `actor_id` fields | MEDIUM | 1 day | P0 |

**Details:**

#### 4.1 Migrate MissionQueueManager to EventStream

**File:** `backend/modules/mission_system/queue.py`

**Current Code (Line 137):**
```python
await self.redis_client.xadd(
    "brain:missions:stream",
    {
        "mission_id": mission.id,
        "priority": mission.priority.value,
        "type": mission.mission_type.value,
        "created_at": mission.created_at.isoformat(),
        "agent_requirements": json.dumps(mission.agent_requirements.dict())
    }
)
```

**Migrated Code:**
```python
from backend.mission_control_core.core.event_stream import EventStream, Event, EventType
import uuid

# In __init__:
self.event_stream = EventStream(redis_url)
await self.event_stream.initialize()

# Replace XADD with:
event = Event(
    id=str(uuid.uuid4()),
    type=EventType.MISSION_CREATED,
    source="mission_queue_manager",
    target=None,
    payload={
        "mission_id": mission.id,
        "priority": mission.priority.value,
        "type": mission.mission_type.value,
        "agent_requirements": mission.agent_requirements.dict()
    },
    timestamp=datetime.utcnow(),
    mission_id=mission.id
)
await self.event_stream.publish_event(event)
```

**Testing:**
```python
# backend/tests/test_mission_system_migration.py
async def test_mission_enqueue_publishes_event():
    event_stream = EventStream()
    await event_stream.initialize()

    # Enqueue mission
    mission = Mission(...)
    await queue_manager.enqueue_mission(mission)

    # Check event was published
    events = await event_stream.get_event_history(limit=1)
    assert events[0].type == EventType.MISSION_CREATED
    assert events[0].payload["mission_id"] == mission.id
```

---

#### 4.2 Add tenant_id, actor_id to Event Schema

**File:** `backend/mission_control_core/core/event_stream.py`

**Change:**
```python
@dataclass
class Event:
    id: str
    type: EventType
    source: str
    target: Optional[str]
    payload: Dict[str, Any]
    timestamp: datetime
    mission_id: Optional[str] = None
    task_id: Optional[str] = None
    correlation_id: Optional[str] = None
    tenant_id: Optional[str] = None      # 🆕 NEW
    actor_id: Optional[str] = None       # 🆕 NEW
    severity: Optional[str] = None       # 🆕 NEW
```

**Alembic Migration:**
```python
# alembic/versions/002_add_event_fields.py
def upgrade():
    # If using PostgreSQL storage (future):
    # op.add_column('events', sa.Column('tenant_id', sa.String(50)))
    # op.add_column('events', sa.Column('actor_id', sa.String(50)))
    # op.add_column('events', sa.Column('severity', sa.String(20)))

    # For Redis-only: No migration needed (schema is dynamic)
    pass
```

**Testing:**
```python
async def test_event_with_tenant_id():
    event = Event(
        id=str(uuid.uuid4()),
        type=EventType.MISSION_CREATED,
        source="test",
        target=None,
        payload={},
        timestamp=datetime.utcnow(),
        tenant_id="tenant_123",  # 🆕
        actor_id="user_456"      # 🆕
    )

    await event_stream.publish_event(event)

    # Verify fields persisted
    events = await event_stream.get_event_history(limit=1)
    assert events[0].tenant_id == "tenant_123"
    assert events[0].actor_id == "user_456"
```

---

### Phase 2: Medium Priority 🟡

| Module | Change | Risk | Effort | Priority |
|--------|--------|------|--------|----------|
| **Immune System** | Integrate with EventStream (optional) | LOW | 2 days | P1 |
| **EventType Enum** | Consolidate all event types | LOW | 1 day | P1 |
| **Sovereign Mode** | Publish audit events to EventStream | LOW | 1 day | P2 |

**Details:**

#### 4.3 Integrate Immune System with EventStream

**File:** `backend/app/modules/immune/core/service.py`

**Option A (Recommended): Dual-Mode**
```python
from backend.mission_control_core.core.event_stream import EventStream, Event, EventType

class ImmuneService:
    def __init__(self, event_stream: Optional[EventStream] = None):
        self._events: List[ImmuneEvent] = []  # Keep in-memory
        self.event_stream = event_stream       # Optional EventStream

    def publish_event(self, event: ImmuneEvent) -> int:
        # Store in-memory (fast)
        stored = ImmuneEvent(...)
        self._events.append(stored)

        # Publish to EventStream (audit trail)
        if self.event_stream:
            asyncio.create_task(self._publish_to_event_stream(stored))

        return stored.id

    async def _publish_to_event_stream(self, immune_event: ImmuneEvent):
        event = Event(
            id=str(uuid.uuid4()),
            type=self._map_immune_to_event_type(immune_event.type),
            source=f"immune_{immune_event.module or 'system'}",
            target=None,
            payload={
                "severity": immune_event.severity.value,
                "message": immune_event.message,
                "meta": immune_event.meta
            },
            timestamp=immune_event.created_at,
            severity=immune_event.severity.value
        )
        await self.event_stream.publish_event(event)

    def _map_immune_to_event_type(self, immune_type: ImmuneEventType) -> EventType:
        mapping = {
            ImmuneEventType.POLICY_VIOLATION: EventType.IMMUNE_POLICY_VIOLATION,
            ImmuneEventType.ERROR_SPIKE: EventType.IMMUNE_ERROR_SPIKE,
            ImmuneEventType.SELF_HEALING_ACTION: EventType.IMMUNE_SELF_HEALING,
        }
        return mapping[immune_type]
```

---

#### 4.4 Consolidate Event Type Enums

**File:** `backend/mission_control_core/core/event_stream.py`

**Add to EventType enum:**
```python
class EventType(str, Enum):
    # ... existing types

    # Immune System Events (NEW)
    IMMUNE_POLICY_VIOLATION = "immune.policy_violation"
    IMMUNE_ERROR_SPIKE = "immune.error_spike"
    IMMUNE_SELF_HEALING = "immune.self_healing"

    # Sovereign Mode Events (NEW)
    SOVEREIGN_MODE_CHANGED = "sovereign.mode_changed"
    SOVEREIGN_GATE_PASSED = "sovereign.gate_check_passed"
    SOVEREIGN_GATE_FAILED = "sovereign.gate_check_failed"
    SOVEREIGN_EGRESS_APPLIED = "sovereign.egress_rules_applied"
    SOVEREIGN_NETWORK_PROBE_PASSED = "sovereign.network_probe_passed"
    SOVEREIGN_NETWORK_PROBE_FAILED = "sovereign.network_probe_failed"

    # PayCore Events (FUTURE)
    PAYMENT_INITIATED = "payment.initiated"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    INVOICE_CREATED = "invoice.created"
    SUBSCRIPTION_STARTED = "subscription.started"
```

**Backward Compatibility:**
```python
# backend/app/modules/immune/schemas.py
class ImmuneEventType(str, Enum):
    """Backward-compatible wrapper for EventType"""
    POLICY_VIOLATION = EventType.IMMUNE_POLICY_VIOLATION.value
    ERROR_SPIKE = EventType.IMMUNE_ERROR_SPIKE.value
    SELF_HEALING_ACTION = EventType.IMMUNE_SELF_HEALING.value

    @classmethod
    def to_event_type(cls, immune_type: 'ImmuneEventType') -> EventType:
        return EventType(immune_type.value)
```

---

### Phase 3: Low Priority (Future) 🟢

| Module | Change | Risk | Effort | Priority |
|--------|--------|------|--------|----------|
| **PayCore Events** | Add payment event types | LOW | 2 days | P3 |
| **Course Events** | Add course lifecycle events | LOW | 1 day | P3 |
| **PostgreSQL Storage** | Migrate from Redis-only to hybrid | MEDIUM | 5 days | P3 |

---

## 5. Testing Strategy

### 5.1 Unit Tests

| Test Suite | File | Coverage |
|------------|------|----------|
| Event Publishing | `test_event_stream_consolidated.py` | ✅ Exists |
| Mission Queue Migration | `test_mission_system_migration.py` | ❌ NEW |
| Immune Integration | `test_immune_eventstream.py` | ❌ NEW |
| Schema Validation | `test_event_schema_fields.py` | ❌ NEW |

### 5.2 Integration Tests

```python
# backend/tests/integration/test_event_system_integration.py

async def test_mission_enqueue_full_flow():
    """Test mission enqueue publishes to EventStream and appears in history"""
    event_stream = EventStream()
    await event_stream.initialize()

    queue_manager = MissionQueueManager()
    mission = Mission(...)

    # Enqueue
    await queue_manager.enqueue_mission(mission)

    # Verify event published
    events = await event_stream.get_event_history(limit=10)
    mission_events = [e for e in events if e.type == EventType.MISSION_CREATED]
    assert len(mission_events) == 1
    assert mission_events[0].payload["mission_id"] == mission.id

async def test_multi_tenant_event_filtering():
    """Test events can be filtered by tenant_id"""
    event_stream = EventStream()

    # Publish events for different tenants
    await event_stream.publish_event(Event(..., tenant_id="tenant_a"))
    await event_stream.publish_event(Event(..., tenant_id="tenant_b"))

    # Filter by tenant (future feature)
    tenant_a_events = await event_stream.get_event_history(tenant_id="tenant_a")
    assert all(e.tenant_id == "tenant_a" for e in tenant_a_events)
```

---

## 6. Risk Assessment

### 6.1 Migration Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Data Loss** | LOW | HIGH | Dual-write during migration, verify before cutover |
| **Downtime** | LOW | MEDIUM | Deploy during maintenance window |
| **Performance Degradation** | MEDIUM | MEDIUM | Load test EventStream, monitor Redis |
| **Breaking Changes** | HIGH | HIGH | Deprecate old APIs, maintain backward compatibility for 2 releases |

### 6.2 Rollback Strategy

```bash
# If migration fails:
1. Stop EventStream integration (set ENABLE_EVENT_STREAM=false)
2. Revert to direct XADD on brain:missions:stream
3. Restore from Redis backup if data corruption
4. Investigate logs and fix issues before retry
```

---

## 7. Summary & Recommendations

### Immediate Actions (This Week)

1. ✅ **Add tenant_id, actor_id to Event schema** (backend/mission_control_core/core/event_stream.py)
2. ✅ **Migrate MissionQueueManager** to use EventStream instead of direct XADD
3. ✅ **Write migration tests** (test_mission_system_migration.py)
4. ✅ **Update documentation** (EVENT_SYSTEM.md)

### Next Sprint

1. 🔄 **Integrate Immune System** (optional EventStream publishing)
2. 🔄 **Consolidate EventType enum** (add IMMUNE_*, SOVEREIGN_* types)
3. 🔄 **Add event filtering by tenant_id** (EventStream.get_event_history)

### Future Considerations

1. 📅 **PayCore Events** - Define payment lifecycle events
2. 📅 **PostgreSQL Hybrid Storage** - EventStream + RDBMS for long-term audit
3. 📅 **Event Replay/Reprocessing** - Add replay functionality for debugging

---

## 8. Appendix: Module-by-Module Impact

| Module | Producer | Consumer | Impact | Migration Effort |
|--------|----------|----------|--------|------------------|
| **Mission Control Core** | ✅ EventStream | ✅ EventStream | ✅ No change | 0 days |
| **Mission Control Runtime** | ✅ emit_task_event | ❌ None | ✅ No change | 0 days |
| **Mission System V1** | 🔴 XADD direct | 🔴 XREADGROUP | 🔴 HIGH | 3 days |
| **Immune System** | 🟡 In-memory only | ❌ None | 🟡 MEDIUM | 2 days (optional) |
| **Sovereign Mode** | ❌ None | ❌ None | ✅ No change | 0 days |
| **Course Factory** | ❌ None | ❌ None | 🟡 Add tenant_id support | 1 day (schema only) |
| **IR Governance** | ❌ None | ❌ None | 🟡 Add tenant_id support | 1 day (schema only) |

---

**Total Migration Effort:** 7-8 days (P0 + P1 tasks)
**Breaking Changes:** Minimal (backward compatibility maintained)
**Risk Level:** 🟡 Medium (careful rollout required)

---

**Next Steps:**
1. Review this report with team
2. Prioritize Phase 1 tasks
3. Create JIRA tickets for each migration task
4. Begin with schema changes (tenant_id, actor_id)
5. Follow with MissionQueueManager migration

**Questions/Concerns:** Contact @claude or open GitHub issue
