# Course Payment Events — Quick Start

## 30-Second Setup

```bash
# 1. Apply migration
cd backend && alembic upgrade head

# 2. Start backend (consumer auto-starts)
python main.py

# Expected: ✅ Event consumer started
```

## Test Payment Event (2 minutes)

```python
# Python shell
import asyncio
from app.core.events.paycore_simulator import get_paycore_simulator

async def test():
    sim = get_paycore_simulator()
    trace_id = await sim.publish_payment_succeeded(
        tenant_id="test_tenant",
        user_id="test_user",
        course_id="course_001",
    )
    print(f"✅ Event published: {trace_id}")

asyncio.run(test())
```

## Verify

**Logs** (should show):
```
[CoursePayment] Granting course access
[CoursePayment] Course access granted successfully
```

**Database**:
```sql
SELECT * FROM course_enrollments WHERE actor_id LIKE 'test_tenant%';
SELECT * FROM processed_events WHERE subscriber_name = 'course_payment_subscriber';
```

## Event Contract (What PayCore Sends)

```json
{
  "event_type": "paycore.payment_succeeded",
  "trace_id": "evt_...",
  "tenant_id": "tenant_123",
  "user_id": "user_456",
  "metadata": {
    "course_id": "course_789",
    "language": "de"
  }
}
```

## What Happens

1. Event published to `brain.events.paycore` (Redis Stream)
2. EventConsumer reads it (consumer group)
3. CoursePaymentSubscriber handles it (with idempotency guard)
4. Handler creates `CourseEnrollment` via `MonetizationService`
5. Enrollment saved to DB
6. Event ACKed (won't be processed again)

## Idempotency

Same `trace_id` → Same event → Only processed **once**.

Replay same event = Skip (logged, no duplicate enrollment).

## Troubleshooting

**Consumer not running?**
```bash
# Check env var
echo $ENABLE_EVENT_CONSUMER  # Should be "true"

# Check logs for:
✅ Event consumer started
```

**Event not processed?**
```bash
# Check Redis stream
redis-cli
> XLEN brain.events.paycore

# Check consumer group
> XINFO GROUPS brain.events.paycore
```

**Enrollment not created?**
- Check logs for errors
- Verify event has `tenant_id`, `user_id`, `metadata.course_id`
- Check `processed_events` table for idempotency skips

## Full Documentation

📖 See `README.md` in this directory for complete documentation.

## Files Changed

```
backend/
├── alembic/versions/002_processed_events_idempotency.py  [NEW]
├── app/core/events/                                       [NEW]
│   ├── __init__.py
│   ├── base_subscriber.py
│   ├── idempotency.py
│   ├── registry.py
│   ├── consumer.py
│   └── paycore_simulator.py
├── app/modules/course_factory/events/                     [NEW]
│   ├── __init__.py
│   ├── subscribers.py
│   ├── handlers.py
│   ├── README.md
│   └── QUICK_START.md
├── main.py                                                [MODIFIED]
└── tests/test_course_payment_events.py                    [NEW]
```

## Run Tests

```bash
cd backend
pytest tests/test_course_payment_events.py -v

# Expected: 13 passed
```

---

**Done!** 🎉

Course module now listens to PayCore payment events and automatically grants course access.
