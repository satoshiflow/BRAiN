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

**Version:** 1.0.0 (Consolidated)
**Last Updated:** 2025-12-28
**Maintainer:** BRAiN Core Team
