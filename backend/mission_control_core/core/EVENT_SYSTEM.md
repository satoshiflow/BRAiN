# BRAiN Event System - Consolidated Architecture

## Overview

BRAiN uses a **single, unified Event System** based on Redis Streams + Pub/Sub for real-time, reliable event-driven communication across all agents and modules.

**Location:** `backend/mission_control_core/core/event_stream.py`

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    EventStream                          │
├─────────────────────────────────────────────────────────┤
│ Redis Infrastructure:                                   │
│  ├─ Streams (XADD/XREAD): Persistent audit trail       │
│  └─ Pub/Sub: Real-time message delivery                │
├─────────────────────────────────────────────────────────┤
│ Components:                                             │
│  ├─ Event Dataclass (id, type, source, target, ...)   │
│  ├─ EventType Enum (24 types: task.*, mission.*, ...)  │
│  ├─ Publisher (publish_event, send_message, broadcast)  │
│  ├─ Subscriber (subscribe_agent, register_handler)      │
│  ├─ Consumer (_event_listener loop)                    │
│  ├─ Router (_route_event to topic channels)            │
│  └─ Audit (get_event_history, get_stream_stats)        │
└─────────────────────────────────────────────────────────┘
```

## Redis Key Structure (Unified Naming)

All keys use **colon notation** (`brain:events:{type}`):

### Redis Streams (Persistent Audit Trail)
- `brain:events:stream` - Main event stream (all events, XADD)
- `brain:events:log:{date}` - Daily event logs (90 day retention)

### Redis Pub/Sub Channels (Real-time Delivery)
- `brain:events:broadcast` - Broadcast channel (all agents)
- `brain:events:system` - System events (`system.*`)
- `brain:events:ethics` - Ethics/KARMA events (`ethics.*`)
- `brain:events:missions` - Mission events (`mission.*`)
- `brain:events:tasks` - Task events (`task.*`)
- `brain:agent:{agent_id}:inbox` - Agent-specific message queues

## Event Types (24 Total)

```python
class EventType(str, Enum):
    # Task Events
    TASK_CREATED = "task.created"
    TASK_ASSIGNED = "task.assigned"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    TASK_RETRYING = "task.retrying"

    # Mission Events
    MISSION_CREATED = "mission.created"
    MISSION_STARTED = "mission.started"
    MISSION_COMPLETED = "mission.completed"
    MISSION_FAILED = "mission.failed"
    MISSION_CANCELLED = "mission.cancelled"

    # Agent Events
    AGENT_ONLINE = "agent.online"
    AGENT_OFFLINE = "agent.offline"
    AGENT_HEARTBEAT = "agent.heartbeat"
    AGENT_ERROR = "agent.error"
    AGENT_TASK_REQUEST = "agent.task_request"

    # System Events
    SYSTEM_HEALTH = "system.health"
    SYSTEM_ALERT = "system.alert"
    SYSTEM_MAINTENANCE = "system.maintenance"

    # Ethics Events
    ETHICS_REVIEW = "ethics.review"
    ETHICS_VIOLATION = "ethics.violation"
    ETHICS_APPROVAL = "ethics.approval"

    # Communication
    AGENT_MESSAGE = "agent.message"
    BROADCAST = "broadcast"
```

## Event Data Structure

```python
@dataclass
class Event:
    id: str                    # UUID v4 (unique event ID)
    type: EventType            # Event type from enum
    source: str                # Agent ID or system component
    target: Optional[str]      # Target agent (None = broadcast)
    payload: Dict[str, Any]    # Event-specific data
    timestamp: datetime        # Event creation timestamp
    mission_id: Optional[str]  # Associated mission ID
    task_id: Optional[str]     # Associated task ID
    correlation_id: Optional[str]  # Request correlation ID

    # Multi-tenancy & Audit fields (v1.1+)
    tenant_id: Optional[str] = None      # Tenant/organization ID
    actor_id: Optional[str] = None       # User/actor who triggered event
    severity: Optional[str] = None       # Event severity: INFO, WARNING, ERROR, CRITICAL
```

## Usage Examples

### 1. Publishing Events

```python
from backend.mission_control_core.core.event_stream import EventStream, Event, EventType
from datetime import datetime
import uuid

# Initialize EventStream
event_stream = EventStream(redis_url="redis://localhost:6379")
await event_stream.initialize()
await event_stream.start()

# Publish mission event
event = Event(
    id=str(uuid.uuid4()),
    type=EventType.MISSION_CREATED,
    source="supervisor_agent",
    target=None,  # Broadcast
    payload={
        "mission_name": "Deploy Application",
        "priority": "high"
    },
    timestamp=datetime.utcnow(),
    mission_id="mission_123"
)

await event_stream.publish_event(event)
```

### 2. Subscribing to Events

```python
# Subscribe agent to specific event types
await event_stream.subscribe_agent(
    agent_id="ops_agent",
    event_types={
        EventType.MISSION_CREATED,
        EventType.TASK_ASSIGNED,
        EventType.SYSTEM_ALERT
    }
)

# Register event handler
async def handle_mission_created(event: Event):
    print(f"New mission: {event.payload['mission_name']}")

await event_stream.register_handler(
    EventType.MISSION_CREATED,
    handle_mission_created
)
```

### 3. Direct Messaging

```python
# Send message between agents
await event_stream.send_message(
    from_agent="supervisor_agent",
    to_agent="coder_agent",
    message={
        "action": "review_code",
        "pr_id": "123"
    },
    correlation_id="req_abc123"
)

# Broadcast to all agents
await event_stream.broadcast_message(
    source="supervisor_agent",
    message={"type": "shutdown", "reason": "maintenance"}
)
```

### 4. Audit & History

```python
# Get event history
events = await event_stream.get_event_history(
    agent_id="ops_agent",  # Filter by agent
    event_types={EventType.MISSION_COMPLETED},
    limit=100
)

# Get stream statistics
stats = await event_stream.get_stream_stats()
# {
#   "stream_length": 1234,
#   "active_subscriptions": 5,
#   "event_handlers": 12,
#   "event_type_counts": {...}
# }
```

### 5. Multi-Tenancy & User Attribution (v1.1+)

```python
# Publish event with tenant and actor information
event = Event(
    id=str(uuid.uuid4()),
    type=EventType.PAYMENT_COMPLETED,
    source="payment_service",
    target=None,
    payload={
        "amount": 99.99,
        "currency": "USD",
        "invoice_id": "INV-001"
    },
    timestamp=datetime.utcnow(),
    tenant_id="org_acme_corp",      # Organization identifier
    actor_id="user_alice",          # User who initiated payment
    severity="INFO"                 # Event severity level
)

await event_stream.publish_event(event)

# Filter events by tenant (multi-tenant isolation)
tenant_events = await event_stream.get_event_history(
    tenant_id="org_acme_corp",
    limit=100
)

# Filter events by actor (user audit trail)
user_events = await event_stream.get_event_history(
    actor_id="user_alice",
    limit=100
)

# Combine filters (tenant + actor + event type)
critical_events = await event_stream.get_event_history(
    tenant_id="org_acme_corp",
    actor_id="user_admin",
    event_types={EventType.SYSTEM_ALERT, EventType.ETHICS_VIOLATION},
    limit=50
)

# Filter by severity (useful for monitoring)
high_severity_events = [
    e for e in await event_stream.get_event_history(limit=1000)
    if e.severity in ["ERROR", "CRITICAL"]
]
```

**Use Cases:**
- **Multi-Tenancy:** Isolate events per organization/tenant
- **User Auditing:** Track which user performed which actions
- **Compliance:** Meet regulatory requirements for audit trails
- **Security:** Identify suspicious activity patterns per user
- **Billing:** Track resource usage per tenant for invoicing

## Integration with main.py

EventStream is **optionally** integrated into the main FastAPI app via environment variable:

```bash
# .env
ENABLE_EVENT_STREAM=true  # Set to enable EventStream in main.py
REDIS_URL=redis://localhost:6379
```

**Startup Flow:**
1. Check if `ENABLE_EVENT_STREAM=true`
2. Initialize EventStream
3. Start consumer loop (`_event_listener`)
4. Store in `app.state.event_stream` for access in routes

**Shutdown Flow:**
1. Stop consumer loop
2. Unsubscribe from all channels
3. Close Redis connection

## Event Routing Logic

Events are routed to specific Pub/Sub channels based on `event.type`:

```python
if event.target:
    # Direct message → agent inbox
    route_to("brain:agent:{target}:inbox")
elif event.type == BROADCAST:
    route_to("brain:events:broadcast")
elif event.type.startswith("mission."):
    route_to("brain:events:missions")
elif event.type.startswith("task."):
    route_to("brain:events:tasks")
elif event.type.startswith("ethics."):
    route_to("brain:events:ethics")
elif event.type.startswith("system."):
    route_to("brain:events:system")
else:
    route_to("brain:events:broadcast")  # Default
```

## Idempotency

**Event Deduplication Strategy:**
- **Event.id**: UUID v4 (unique per event)
- **correlation_id**: Request-level tracing (optional)
- **Redis XADD ID**: Stream-level position (e.g., `1234567890123-0`)

**No dedicated idempotency table** - relies on:
1. Consumer-side deduplication (check Event.id)
2. Redis Stream consumer groups (XREADGROUP with ACK)

## Consumer Lifecycle

**Single Consumer Loop:**
```python
async def _event_listener(self):
    """Main event listener loop"""
    async for message in self.pubsub.listen():
        if message['type'] != 'message':
            continue

        event_data = json.loads(message['data'])
        event = Event.from_dict(event_data)

        # Execute registered handlers
        await self._handle_event(event)
```

**No duplicate consumers** - only one `_event_listener` runs per EventStream instance.

## Removed Components (Consolidated)

The following components were **removed** as part of consolidation:

❌ **backend/app/core/event_bus.py** (unused, minimal)
- Only had XADD publishing
- No subscribers, consumers, or event types
- Functionality fully covered by EventStream

❌ **backend/app/workers/dlq_worker.py** (unused)
- Dead Letter Queue worker
- Not integrated anywhere
- DLQ logic can be added to EventStream if needed

## Migration Guide

If you were using the old `event_bus.py`:

**Before:**
```python
from app.core.event_bus import EventBus
event_bus = EventBus(redis_client)
event_bus.publish_mission({"status": "completed"})
```

**After:**
```python
from backend.mission_control_core.core.event_stream import EventStream, Event, EventType
import uuid
from datetime import datetime

event_stream = EventStream()
await event_stream.initialize()

event = Event(
    id=str(uuid.uuid4()),
    type=EventType.MISSION_COMPLETED,
    source="supervisor",
    target=None,
    payload={"status": "completed"},
    timestamp=datetime.utcnow()
)
await event_stream.publish_event(event)
```

## Testing

See `backend/tests/test_event_stream.py` for comprehensive test suite.

**Quick Test:**
```bash
# Start Redis
docker-compose up -d redis

# Run tests
pytest backend/tests/test_event_stream.py -v
```

## Troubleshooting

**Q: EventStream not starting in main.py?**
A: Check `ENABLE_EVENT_STREAM=true` in `.env`

**Q: Events not being delivered?**
A: Verify Redis connection and Pub/Sub subscriptions

**Q: Consumer not processing events?**
A: Check `_event_listener` is running (should auto-start with `event_stream.start()`)

**Q: Old event_bus imports failing?**
A: event_bus.py was removed - use EventStream instead (see Migration Guide)

## Architecture Philosophy

**Myzelkapitalismus Principles:**
- 🌐 **Transparent Communication**: All events stored in audit trail
- 🤝 **Cooperative Agents**: Pub/Sub enables agent collaboration
- 🔍 **Ethical Oversight**: Events logged for KARMA review
- ⚡ **Real-time Coordination**: Low-latency Pub/Sub delivery
- 📊 **Adaptive Learning**: Event history enables pattern recognition

---

## MissionQueueManager Integration (v1.2+)

The Mission System V1 (`backend/modules/mission_system/queue.py`) has been integrated with EventStream as part of the consolidation effort.

### Migration Overview

**Before (Legacy):**
- Used separate `brain:missions:stream` (XADD)
- No unified event trail
- No status change events

**After (v1.2+):**
- Uses unified EventStream
- Publishes MISSION_CREATED, MISSION_STARTED, MISSION_COMPLETED, MISSION_FAILED, MISSION_CANCELLED events
- Full audit trail in `brain:events:stream`
- Backward compatible with feature flag

### Feature Flag

Set environment variable to enable/disable EventStream integration:

```bash
# Enable EventStream (default)
USE_EVENT_STREAM=true

# Disable EventStream (use legacy MISSION_STREAM)
USE_EVENT_STREAM=false
```

### Published Events

| Trigger | Event Type | Payload |
|---------|------------|---------|
| `enqueue_mission()` | `MISSION_CREATED` | mission_id, mission_name, priority, type, agent_requirements |
| Status → RUNNING | `MISSION_STARTED` | mission_id, old_status, new_status |
| Status → COMPLETED | `MISSION_COMPLETED` | mission_id, result |
| Status → FAILED | `MISSION_FAILED` | mission_id, error_message |
| Status → CANCELLED | `MISSION_CANCELLED` | mission_id, old_status |

### Code Example

```python
from backend.modules.mission_system.queue import MissionQueueManager

# MissionQueueManager automatically uses EventStream if enabled
queue_manager = MissionQueueManager(redis_url="redis://localhost:6379")
await queue_manager.connect()  # Initializes EventStream

# Enqueue mission → publishes MISSION_CREATED event
await queue_manager.enqueue_mission(mission)

# Status updates → publish lifecycle events
await queue_manager.update_mission_status(mission.id, MissionStatus.RUNNING)  # MISSION_STARTED
await queue_manager.update_mission_status(mission.id, MissionStatus.COMPLETED)  # MISSION_COMPLETED

# Statistics include EventStream metrics
stats = await queue_manager.get_queue_statistics()
# {
#   "event_stream_enabled": true,
#   "event_stream_stats": {...},
#   "queue_lengths": {...}
# }
```

### Testing

Comprehensive test suite: `backend/tests/test_mission_queue_eventstream.py`

```bash
# Run MissionQueueManager integration tests
pytest backend/tests/test_mission_queue_eventstream.py -v
```

**Test Coverage:**
- ✅ EventStream initialization
- ✅ MISSION_CREATED event publishing
- ✅ All lifecycle events (STARTED, COMPLETED, FAILED, CANCELLED)
- ✅ Statistics integration
- ✅ Backward compatibility with legacy mode
- ✅ Fallback on EventStream failure

### Deprecation Notice

**DEPRECATED:** Direct usage of `brain:missions:stream` is deprecated as of v1.2. All mission events are now published to the unified `brain:events:stream` via EventStream.

For legacy mode (not recommended), set `USE_EVENT_STREAM=false`.

---

## Idempotent Event Consumption (v1.3+ Charter Compliant)

### Charter v1.0: Primary Dedup Key = Stream Message ID

**CRITICAL:** event.id is **NOT** the primary dedup key. Redis Stream Message ID is.

**Why?**
- event.id (UUID v4) is regenerated on retry → non-idempotent
- Redis Stream Message ID is stable across retries → idempotent

### EventConsumer Architecture

```python
from backend.mission_control_core.core.event_stream import EventConsumer, EventType

# Initialize consumer
consumer = EventConsumer(
    subscriber_name="course_access_handler",
    event_stream=event_stream,
    db_session_factory=get_db_session,  # SQLAlchemy session factory
    stream_name="brain:events:stream",
    consumer_group="group_course_access"
)

# Register event handlers
async def handle_payment_completed(event: Event):
    # Grant course access
    course_id = event.payload["course_id"]
    user_id = event.payload["user_id"]
    await grant_access(course_id, user_id)

consumer.register_handler(EventType.PAYMENT_COMPLETED, handle_payment_completed)

# Start consumer
await consumer.start()
```

### Dedup Mechanism

**Primary Key:** `(subscriber_name, stream_message_id)`

**DB Table:** `processed_events`
- `subscriber_name`: Unique consumer name
- `stream_message_id`: Redis Stream Message ID (e.g. `1735390000000-0`)
- `event_id`: UUID (SECONDARY, audit/trace only)
- `processed_at`: Timestamp for TTL enforcement

**Replay Behavior:**
```python
# First delivery
stream_message_id = "1735390000000-0"
event.id = "abc-123-def"
→ Processed, stored in DB

# Retry/Replay (same stream_message_id)
stream_message_id = "1735390000000-0"  # SAME
event.id = "xyz-456-ghi"  # DIFFERENT (regenerated)
→ Skipped (duplicate detected by stream_message_id)
```

### Error Handling (Charter Compliant)

**Permanent Errors** (ACK + Log):
- `ValueError`, `TypeError`, `KeyError`
- Validation failures
- Business logic violations

**Transient Errors** (NO ACK, will retry):
- `ConnectionError`, `TimeoutError`
- DB connection failures
- External API timeouts

**Example:**
```python
try:
    await handler(event)
except ValueError as e:
    # PERMANENT: ACK message, log error, optional DLQ
    logger.error(f"Validation failed: {e}")
    await ack_message()
except ConnectionError as e:
    # TRANSIENT: DO NOT ACK, will retry
    logger.warning(f"Connection failed, retrying: {e}")
    # No ACK → Redis will redeliver
```

### Database Migration

**Run migration:**
```bash
cd backend
alembic upgrade head
```

**Creates table:**
```sql
CREATE TABLE processed_events (
    id SERIAL PRIMARY KEY,
    subscriber_name VARCHAR(255) NOT NULL,
    stream_name VARCHAR(255) NOT NULL,
    stream_message_id VARCHAR(50) NOT NULL,  -- PRIMARY dedup key
    event_id VARCHAR(50),                     -- SECONDARY (audit)
    event_type VARCHAR(100),
    processed_at TIMESTAMPTZ DEFAULT NOW(),
    tenant_id VARCHAR(100),
    metadata JSONB,
    UNIQUE (subscriber_name, stream_message_id)
);
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BRAIN_EVENTSTREAM_MODE` | `required` | `required` or `degraded` (dev/CI only) |
| `DATABASE_URL` | - | PostgreSQL connection string (for dedup store) |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection string |

### Testing Idempotency

```bash
# Run idempotency tests
pytest backend/tests/test_event_consumer_idempotency.py -v
```

**Key Tests:**
- ✅ Dedup key is stream_message_id (NOT event.id)
- ✅ Replay same message → no duplicate effect
- ✅ New message with same payload → processed
- ✅ Permanent error → ACK
- ✅ Transient error → NO ACK (retry)

---

## Changelog

### v1.3.0 (2025-12-28) - Charter v1.0 Idempotency
- ✅ **EventConsumer with Charter-compliant idempotency**
- ✅ Primary dedup key: `(subscriber_name, stream_message_id)`
- ✅ event.id demoted to SECONDARY (audit/trace only)
- ✅ DB-based dedup store (`processed_events` table)
- ✅ Alembic migration: `002_event_dedup_stream_message_id.py`
- ✅ Error handling: permanent → ACK, transient → NO ACK
- ✅ Consumer group pattern (Redis Streams XREADGROUP)
- ✅ Comprehensive test suite (7 tests)
- ✅ Documentation: Idempotency section added

### v1.2.0 (2025-12-28) - Mission System Integration
- ✅ **MissionQueueManager integrated with EventStream**
- ✅ Migrated from separate `brain:missions:stream` to unified `brain:events:stream`
- ✅ Added mission lifecycle events: MISSION_CREATED, MISSION_STARTED, MISSION_COMPLETED, MISSION_FAILED, MISSION_CANCELLED
- ✅ Feature flag `USE_EVENT_STREAM` for backward compatibility
- ✅ Fallback to legacy MISSION_STREAM if EventStream fails
- ✅ Updated statistics to include EventStream metrics
- ✅ Comprehensive test suite (9 tests)
- ✅ Full backward compatibility maintained

### v1.1.0 (2025-12-28) - Multi-Tenancy & Audit Extensions
- ✅ Added `tenant_id` field for multi-tenant event isolation
- ✅ Added `actor_id` field for user attribution and audit trails
- ✅ Added `severity` field for event severity levels (INFO/WARNING/ERROR/CRITICAL)
- ✅ Extended `get_event_history()` with tenant_id and actor_id filtering
- ✅ Comprehensive test suite for new schema fields (7 new tests)
- ✅ Backward compatibility maintained (all fields optional)

### v1.0.0 (2025-12-28) - Consolidated Event System
- ✅ EventStream as single source of truth
- ✅ Removed duplicate event_bus.py and dlq_worker.py
- ✅ Unified stream naming convention (brain:events:{type})
- ✅ Extended event routing (mission.*, task.* channels)
- ✅ 24 event types across all domains

---

**Version:** 1.3.0 (Charter v1.0 Compliant - Idempotent Consumers)
**Last Updated:** 2025-12-28
**Maintainer:** BRAiN Core Team
