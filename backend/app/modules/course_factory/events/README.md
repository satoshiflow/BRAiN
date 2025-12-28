# Course ← PayCore Event Integration

## Overview

Course module listens to PayCore payment events and automatically grants/revokes course access based on payment outcomes. The integration is **idempotent**, **tenant-safe**, and **provider-agnostic** (Course module never touches Stripe/PayPal).

## Architecture

```
PayCore
  └─> Publishes Events to Redis Streams (brain.events.paycore)
       └─> EventConsumer reads with Consumer Groups
            └─> CoursePaymentSubscriber handles events
                 └─> Handlers grant/revoke course access
                      └─> IdempotencyGuard prevents duplicate processing
```

## Event Contract

### Payment Succeeded

```json
{
  "event_type": "paycore.payment_succeeded",
  "trace_id": "evt_abc123",
  "tenant_id": "tenant_456",
  "intent_id": "intent_xyz",
  "tx_id": "tx_def",
  "user_id": "user_789",
  "metadata": {
    "course_id": "course_012",
    "language": "de"
  },
  "timestamp": 1234567890.123
}
```

**Action**: Creates `CourseEnrollment` with `actor_id = "{tenant_id}:{user_id}"`.

### Payment Failed

```json
{
  "event_type": "paycore.payment_failed",
  "trace_id": "evt_fail123",
  "tenant_id": "tenant_456",
  "intent_id": "intent_xyz",
  "user_id": "user_789",
  "metadata": {
    "course_id": "course_012",
    "failure_reason": "card_declined"
  },
  "timestamp": 1234567890.123
}
```

**Action**: Logs failure (no access granted).

### Refund Succeeded

```json
{
  "event_type": "paycore.refund_succeeded",
  "trace_id": "evt_refund123",
  "tenant_id": "tenant_456",
  "intent_id": "intent_xyz",
  "refund_id": "ref_abc",
  "user_id": "user_789",
  "metadata": {
    "course_id": "course_012",
    "enrollment_id": "enr_ghi"
  },
  "timestamp": 1234567890.456
}
```

**Action**: Logs refund (MVP: no revocation, future: mark enrollment as refunded).

## Components

### 1. EventSubscriber Base Class

**Location**: `backend/app/core/events/base_subscriber.py`

Abstract base class for all event subscribers.

```python
class EventSubscriber(ABC):
    @property
    @abstractmethod
    def subscriber_name(self) -> str:
        pass

    @property
    @abstractmethod
    def event_types(self) -> List[str]:
        pass

    @abstractmethod
    async def handle(self, event: Dict[str, Any]) -> None:
        pass

    async def on_error(self, event: Dict[str, Any], error: Exception) -> bool:
        # Returns True if transient (retry), False if permanent (skip)
        pass
```

### 2. IdempotencyGuard

**Location**: `backend/app/core/events/idempotency.py`

Database-backed idempotency using `processed_events` table.

**Primary Key**: `(subscriber_name, trace_id)`

Ensures each subscriber processes each event exactly once.

```python
guard = IdempotencyGuard(db_session)

if await guard.should_process(subscriber_name, event):
    # Process event
    await handler(event)
```

### 3. CoursePaymentSubscriber

**Location**: `backend/app/modules/course_factory/events/subscribers.py`

Subscribes to PayCore events and dispatches to handlers.

```python
class CoursePaymentSubscriber(EventSubscriber):
    @property
    def subscriber_name(self) -> str:
        return "course_payment_subscriber"

    @property
    def event_types(self) -> List[str]:
        return [
            "paycore.payment_succeeded",
            "paycore.payment_failed",
            "paycore.refund_succeeded",
        ]

    async def handle(self, event: Dict[str, Any]) -> None:
        # Dispatch to appropriate handler
        pass
```

### 4. Event Handlers

**Location**: `backend/app/modules/course_factory/events/handlers.py`

Business logic for payment events.

- `handle_payment_succeeded()`: Grants course access via `MonetizationService.enroll_course()`
- `handle_payment_failed()`: Logs failure
- `handle_refund_succeeded()`: Logs refund (future: revoke access)

### 5. EventConsumer

**Location**: `backend/app/core/events/consumer.py`

Reads from Redis Streams using Consumer Groups (`XREADGROUP`).

- Polls `brain.events.paycore` and other streams
- Dispatches events to registered subscribers
- Handles ACK/NACK based on error type (transient vs permanent)

### 6. PayCoreSimulator

**Location**: `backend/app/core/events/paycore_simulator.py`

Testing utility to publish payment events.

```python
simulator = get_paycore_simulator()

await simulator.publish_payment_succeeded(
    tenant_id="tenant_demo",
    user_id="user_123",
    course_id="course_456",
    language="de",
)
```

## Database Migration

**File**: `backend/alembic/versions/002_processed_events_idempotency.py`

Creates `processed_events` table:

```sql
CREATE TABLE processed_events (
    subscriber_name VARCHAR(100) NOT NULL,
    trace_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    tenant_id VARCHAR(100),
    processed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (subscriber_name, trace_id)
);

CREATE INDEX idx_processed_events_tenant ON processed_events(tenant_id);
CREATE INDEX idx_processed_events_type ON processed_events(event_type);
```

**Apply migration**:

```bash
cd backend
alembic upgrade head
```

## Configuration

### Environment Variables

```bash
# Enable event consumer (default: true)
ENABLE_EVENT_CONSUMER=true

# Enable mission worker (default: true)
ENABLE_MISSION_WORKER=true
```

### Startup Registration

**Location**: `backend/main.py`

```python
# Register subscribers during startup
registry = get_subscriber_registry()
registry.register(CoursePaymentSubscriber())

# Start consumer
event_consumer = await start_event_consumer()
```

## Smoke Test Guide

### Prerequisites

1. **Database**: Run migration
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Redis**: Ensure Redis is running
   ```bash
   docker-compose up -d redis
   ```

3. **Backend**: Start backend
   ```bash
   cd backend
   python main.py
   ```

### Test 1: Publish Payment Event

```python
# Open Python shell
import asyncio
from app.core.events.paycore_simulator import get_paycore_simulator

simulator = get_paycore_simulator()

# Publish payment succeeded event
trace_id = await simulator.publish_payment_succeeded(
    tenant_id="tenant_smoke_test",
    user_id="user_smoke_123",
    course_id="course_test_001",
    language="de",
)

print(f"Published event: {trace_id}")
```

### Test 2: Verify Enrollment Created

Check logs:

```bash
# Look for:
# [CoursePayment] Granting course access
# [CoursePayment] Course access granted successfully
# [IdempotencyGuard] Event marked for processing
```

Check database:

```sql
-- Check enrollment created
SELECT * FROM course_enrollments
WHERE actor_id = 'tenant_smoke_test:user_smoke_123';

-- Check idempotency record
SELECT * FROM processed_events
WHERE subscriber_name = 'course_payment_subscriber'
AND trace_id = '<trace_id_from_step_1>';
```

### Test 3: Idempotency (Replay Event)

Publish same event again with same `trace_id`:

```python
# Manually publish event with same trace_id
import redis.asyncio as redis
import json

r = await redis.from_url("redis://localhost:6379/0", decode_responses=True)

event = {
    "event_type": "paycore.payment_succeeded",
    "trace_id": "<trace_id_from_test_1>",  # SAME trace_id
    "tenant_id": "tenant_smoke_test",
    "user_id": "user_smoke_123",
    "metadata": {
        "course_id": "course_test_001",
        "language": "de",
    },
}

await r.xadd("brain.events.paycore", {"data": json.dumps(event)})
```

**Expected Behavior**:
- Log: `[IdempotencyGuard] Event already processed (idempotent skip)`
- Enrollment count: **Still 1** (no duplicate)

### Test 4: Refund Event

```python
# Publish refund event
trace_id = await simulator.publish_refund_succeeded(
    tenant_id="tenant_smoke_test",
    user_id="user_smoke_123",
    course_id="course_test_001",
    intent_id="intent_original",
    enrollment_id="enr_from_test_2",
)

print(f"Published refund: {trace_id}")
```

**Expected Behavior**:
- Log: `[CoursePayment] Refund processed`
- Log: `[CoursePayment] Refund logged (access revocation not implemented)`

## Error Handling

### Permanent Errors (Skip Event)

- **ValidationError**: Missing required fields (tenant_id, course_id, etc.)
- **KeyError**: Malformed event structure
- **TypeError**: Invalid data types

**Behavior**: Log error, ACK event, **do not retry**.

### Transient Errors (Retry Event)

- **Database connection errors**
- **Redis timeouts**
- **Network errors**

**Behavior**: Log warning, **do not ACK**, consumer will retry.

### Error Classification

Implemented in `EventSubscriber.on_error()`:

```python
async def on_error(self, event: Dict[str, Any], error: Exception) -> bool:
    if isinstance(error, (ValueError, KeyError, TypeError)):
        return False  # Permanent: skip
    else:
        return True  # Transient: retry
```

## Multi-Tenant Safety

All operations are tenant-scoped:

- `actor_id` format: `"{tenant_id}:{user_id}"`
- Enrollment records include pseudonymous `actor_id`
- No cross-tenant access possible

## Future Enhancements

### Phase 2: Refund Handling

Add `status` field to `CourseEnrollment`:

```python
class EnrollmentStatus(str, Enum):
    ACTIVE = "active"
    REFUNDED = "refunded"
    SUSPENDED = "suspended"
```

Update `handle_refund_succeeded()`:

```python
# Mark enrollment as refunded
enrollment = await service.get_enrollment(enrollment_id)
enrollment.status = EnrollmentStatus.REFUNDED
await service.update_enrollment(enrollment)
```

### Phase 3: Dead Letter Queue (DLQ)

For events that fail permanently:

- After N retries, move to DLQ stream: `brain.events.dlq`
- Expose DLQ inspection endpoint: `GET /api/events/dlq`
- Manual replay: `POST /api/events/dlq/{id}/replay`

### Phase 4: Auto-Discovery

Auto-discover and register subscribers:

```python
# Scan modules for subscribers
for module in discover_modules("backend/app/modules/*/events"):
    for subscriber_class in module.subscribers:
        registry.register(subscriber_class())
```

## Testing

Run tests:

```bash
cd backend
pytest tests/test_course_payment_events.py -v
```

**Test Coverage**:

- ✅ Subscriber properties and dispatch
- ✅ Handler creates enrollment with correct parameters
- ✅ Handler validates required fields
- ✅ Idempotency prevents duplicate enrollments
- ✅ Different subscribers can process same event
- ✅ PayCore simulator publishes events correctly
- ✅ End-to-end payment flow (mocked)

## Troubleshooting

### Event Not Consumed

**Check consumer is running**:

```bash
# Logs should show:
# ✅ Event consumer started
```

**Check subscriber registered**:

```bash
# Logs should show:
# ✅ Event subscribers registered
# [SubscriberRegistry] Registered subscriber: course_payment_subscriber
```

### Enrollment Not Created

**Check event structure**:

```python
# Ensure event has:
# - event_type
# - trace_id
# - tenant_id
# - user_id
# - metadata.course_id
```

**Check logs for errors**:

```bash
# Look for:
# [CoursePayment] Failed to grant course access
# [EventConsumer] Permanent error, skipping event
```

### Database Migration Issues

```bash
# Check current version
alembic current

# Check pending migrations
alembic history

# Force upgrade
alembic upgrade head
```

## Security Considerations

1. **No PII in Logs**: Never log `user_id` directly (use `actor_id` or hash)
2. **Tenant Isolation**: Always validate `tenant_id` in multi-tenant systems
3. **Provider Abstraction**: Course module never imports Stripe/PayPal SDKs
4. **Audit Trail**: `processed_events` table provides complete event audit

## Performance

- **Batch Processing**: Consumer reads up to 10 events per poll
- **Consumer Groups**: Multiple consumers can run concurrently
- **Idempotency Index**: Primary key on `(subscriber_name, trace_id)` is fast
- **Non-blocking**: Async/await throughout the stack

## Metrics (Future)

```python
# Expose Prometheus metrics
event_consumer_processed_total{subscriber="course_payment_subscriber", event_type="paycore.payment_succeeded"} 1234
event_consumer_errors_total{subscriber="course_payment_subscriber", error_type="transient"} 5
idempotency_skips_total{subscriber="course_payment_subscriber"} 10
```

## Conclusion

The Course ← PayCore event integration provides:

✅ **Idempotent** course access granting
✅ **Tenant-safe** multi-tenant isolation
✅ **Provider-agnostic** abstraction from payment providers
✅ **Resilient** error handling (transient vs permanent)
✅ **Auditable** complete event trail in `processed_events`
✅ **Testable** comprehensive test suite + simulator

No Stripe/PayPal logic in Course module. Clean event-driven architecture.
