# Sentry Error Tracking Setup

**Version:** Phase 2 - Monitoring & Observability  
**Status:** COMPLETE  
**Last Updated:** 2025-12-20

---

## Overview

BRAiN Core now includes comprehensive error tracking and performance monitoring via Sentry:

- **Automatic Error Tracking**: All unhandled exceptions are automatically captured
- **Performance Monitoring (APM)**: Transaction and span tracking for performance insights
- **Breadcrumbs**: Debug trail leading up to errors
- **User Context**: Associate errors with specific users
- **Custom Tags & Context**: Enrich errors with business context
- **Release Tracking**: Track errors by deployment version
- **Alerting**: Real-time notifications for critical errors

---

## Quick Start

### 1. Get Sentry DSN

1. Sign up at [sentry.io](https://sentry.io)
2. Create a new project (select "FastAPI" or "Python")
3. Copy your DSN from project settings

### 2. Configure Environment

Add to `.env`:

```bash
# Sentry Configuration
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% of transactions
SENTRY_PROFILES_SAMPLE_RATE=0.1  # 10% profiling
```

### 3. Start Application

Sentry is automatically initialized on startup:

```bash
docker compose up -d
```

Check logs for confirmation:
```
2025-12-20 13:30:45 | INFO | Sentry initialized | environment=production, traces_sample_rate=0.1
```

---

## Configuration

### Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `SENTRY_DSN` | Sentry project DSN (required) | - | `https://xxx@sentry.io/123` |
| `SENTRY_ENVIRONMENT` | Environment name | Value of `ENVIRONMENT` | `production`, `staging`, `development` |
| `SENTRY_TRACES_SAMPLE_RATE` | % of transactions to track (0.0-1.0) | `0.1` (10%) | `0.5` (50%), `1.0` (100%) |
| `SENTRY_PROFILES_SAMPLE_RATE` | % of transactions to profile (0.0-1.0) | `0.1` (10%) | `0.2` (20%) |
| `SENTRY_SEND_DEFAULT_PII` | Send personally identifiable information | `false` | `true`, `false` |
| `SENTRY_DEBUG` | Enable Sentry debug logging | `false` | `true`, `false` |
| `SENTRY_RELEASE` | Release version | Git commit or `0.3.0` | `1.2.3`, `abc123` |

### Sampling Rates

**Traces Sample Rate** controls what percentage of transactions are sent to Sentry for performance monitoring:

- `1.0` (100%) - All transactions (use in development)
- `0.1` (10%) - 1 in 10 transactions (good for production)
- `0.01` (1%) - 1 in 100 transactions (high-traffic production)

**Profiles Sample Rate** controls profiling (CPU/memory analysis):

- Usually set same as or lower than traces sample rate
- Profiling adds more overhead than simple transaction tracking

**Environment-specific Defaults:**
- Development: 100% (1.0) - capture everything for debugging
- Production: 10% (0.1) - balance between insight and quota

---

## Features

### Automatic Error Tracking

All unhandled exceptions are automatically captured:

```python
# No code needed - happens automatically
@router.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await db.get_user(user_id)  # If this raises, Sentry captures it
    return user
```

### Manual Error Capture

Capture exceptions manually with context:

```python
from app.core.sentry import capture_exception

try:
    risky_operation()
except Exception as e:
    event_id = capture_exception(
        e,
        mission_id="mission_123",
        agent_type="ops_agent",
        environment="production"
    )
    logger.error(f"Error captured in Sentry: {event_id}")
```

### Message Capture

Send messages (warnings, info) to Sentry:

```python
from app.core.sentry import capture_message

capture_message(
    "Unusual activity detected",
    level="warning",
    activity_type="multiple_failed_logins",
    user_id="user_123",
    ip_address="192.168.1.1"
)
```

### User Context

Associate errors with users:

```python
from app.core.sentry import set_user_context

# In authentication middleware or endpoint
set_user_context(
    user_id="user_123",
    email="user@example.com",
    username="john_doe",
    subscription_tier="premium"
)

# All subsequent errors will include this user info
```

### Custom Tags

Add searchable tags to errors:

```python
from app.core.sentry import set_tag

set_tag("mission_type", "deployment")
set_tag("agent_type", "ops_agent")
set_tag("priority", "HIGH")

# Tags appear in Sentry UI and are searchable
```

### Custom Context

Add structured context to errors:

```python
from app.core.sentry import set_context

set_context("mission", {
    "id": "mission_123",
    "priority": "HIGH",
    "status": "running",
    "agent_id": "ops_agent_1"
})

set_context("request_data", {
    "endpoint": "/api/missions/enqueue",
    "payload_size": 1024,
    "client_ip": "192.168.1.1"
})
```

### Breadcrumbs

Add breadcrumbs for debugging trail:

```python
from app.core.sentry import add_breadcrumb

# Before database query
add_breadcrumb(
    message="Executing database query",
    category="database",
    level="info",
    data={"query_type": "SELECT", "table": "users"}
)

# Before external API call
add_breadcrumb(
    message="Calling external API",
    category="http",
    level="info",
    data={"url": "https://api.example.com", "method": "POST"}
)

# If error occurs, breadcrumbs show what led up to it
```

### Performance Monitoring

Track custom transactions and spans:

```python
from app.core.sentry import start_transaction, start_span

# Track entire operation
with start_transaction(name="process_mission", op="task.run") as transaction:
    transaction.set_tag("mission_id", "mission_123")

    # Track database query
    with start_span(op="db.query", description="Fetch mission data"):
        mission = await db.get_mission(mission_id)

    # Track external API call
    with start_span(op="http.client", description="Call LLM API"):
        response = await llm.generate(prompt)

    # Track cache operation
    with start_span(op="cache.set", description="Cache results"):
        await redis.set(f"mission:{mission_id}", result)
```

---

## Integrations

Sentry automatically integrates with:

1. **FastAPI** - HTTP requests, endpoints, status codes
2. **Starlette** - ASGI middleware
3. **Asyncio** - Async exceptions
4. **Redis** - Redis operations
5. **SQLAlchemy** - Database queries
6. **HTTPX** - HTTP client calls
7. **Logging** - Log messages (INFO+ as breadcrumbs, ERROR+ as events)

No additional code needed - these integrations work automatically!

---

## Filtering & Privacy

### Filter Sensitive Data

The `_before_send()` function filters sensitive data:

```python
# In app/core/sentry.py
def _before_send(event, hint):
    # Remove password fields from request data
    if "request" in event and "data" in event["request"]:
        data = event["request"]["data"]
        for key in list(data.keys()):
            if "password" in key.lower() or "secret" in key.lower():
                data[key] = "[FILTERED]"
    return event
```

### Skip Certain Errors

```python
def _before_send(event, hint):
    # Skip HTTP 4xx errors (client errors)
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        if exc_type.__name__ == "HTTPException":
            if exc_value.status_code < 500:
                return None  # Don't send to Sentry
    return event
```

### Skip Health Check Transactions

```python
def _before_send_transaction(event, hint):
    # Skip /health endpoints (reduce noise)
    if event.get("transaction") in ["/health", "/health/live", "/health/ready"]:
        return None
    return event
```

---

## Sentry Dashboard

### Issues View

Group errors by:
- Error type
- Message
- Stack trace fingerprint

**Sort by:**
- Frequency (most common errors)
- Users affected
- First seen / Last seen

### Performance View

**Transactions:**
- P50, P95, P99 latency
- Throughput (requests per minute)
- Apdex score (user satisfaction)

**Spans:**
- Database query duration
- External API call duration
- Cache operation duration

### Releases

Track errors by deployment:
- Compare error rate between releases
- See which commit introduced an issue
- Track improvement over time

### Alerts

Configure alerts for:
- Error rate threshold exceeded
- New error type detected
- Performance regression
- User feedback submitted

---

## Example Use Cases

### Mission System Monitoring

```python
from app.core.sentry import (
    set_user_context,
    set_tag,
    set_context,
    add_breadcrumb,
    start_transaction,
    capture_exception
)

async def process_mission(mission_id: str, user_id: str):
    # Set user context
    set_user_context(user_id=user_id)

    # Set mission tags
    set_tag("mission_id", mission_id)
    set_tag("mission_type", "deployment")

    # Add context
    set_context("mission", {
        "id": mission_id,
        "priority": "HIGH",
        "agent": "ops_agent"
    })

    # Track performance
    with start_transaction(name="process_mission", op="task.run"):
        try:
            # Breadcrumb before validation
            add_breadcrumb("Validating mission parameters", category="validation")
            validate_mission(mission)

            # Breadcrumb before execution
            add_breadcrumb("Executing mission", category="execution")
            result = await execute_mission(mission)

            return result

        except Exception as e:
            # Capture with full context
            event_id = capture_exception(e)
            logger.error(f"Mission failed - Sentry event: {event_id}")
            raise
```

### API Error Tracking

```python
@router.post("/api/missions/enqueue")
async def enqueue_mission(
    payload: MissionPayload,
    request: Request,
    user: User = Depends(get_current_user)
):
    # Set user context
    set_user_context(
        user_id=user.id,
        email=user.email,
        username=user.username
    )

    # Set request context
    set_context("request", {
        "endpoint": "/api/missions/enqueue",
        "method": "POST",
        "client_ip": request.client.host,
        "user_agent": request.headers.get("user-agent")
    })

    # This endpoint is automatically tracked by FastAPI integration
    # If error occurs, Sentry gets full context
    mission = await mission_service.enqueue(payload)
    return mission
```

---

## Production Recommendations

1. **Sampling Rates:**
   - Start with 10% (0.1) for traces
   - Adjust based on traffic and quota
   - Use 100% in development

2. **PII Handling:**
   - Keep `SEND_DEFAULT_PII=false` unless required
   - Filter sensitive data in `_before_send()`
   - Review captured data regularly

3. **Alerting:**
   - Set up alerts for error rate spikes
   - Alert on new error types
   - Integrate with Slack/PagerDuty

4. **Release Tracking:**
   - Set `SENTRY_RELEASE` to git commit hash
   - Use semantic versioning (1.2.3)
   - Tag releases in Sentry UI

5. **Performance Budget:**
   - Set performance thresholds (P95 < 200ms)
   - Alert on regressions
   - Track improvement over time

6. **Quota Management:**
   - Monitor event quota usage
   - Adjust sampling rates if needed
   - Filter noisy errors

---

## Troubleshooting

**Events not appearing in Sentry:**
- Verify `SENTRY_DSN` is set correctly
- Check application logs for Sentry init message
- Check Sentry debug mode: `SENTRY_DEBUG=true`
- Verify internet connectivity from container

**Too many events (quota exceeded):**
- Reduce `SENTRY_TRACES_SAMPLE_RATE` (e.g., 0.05 = 5%)
- Filter out noisy errors in `_before_send()`
- Increase ignored errors list

**PII concerns:**
- Ensure `SENTRY_SEND_DEFAULT_PII=false`
- Review `_before_send()` filters
- Use data scrubbing rules in Sentry project settings

**Performance impact:**
- Sentry SDK adds <5ms overhead per request
- Use lower sampling rates for high-traffic services
- Enable async event sending (automatic with FastAPI integration)

---

## Testing Sentry Integration

### Test Error Capture

```bash
# Trigger a test error
curl http://localhost:8000/api/test-error

# Or add a test endpoint
@router.get("/test-error")
async def test_error():
    from app.core.sentry import capture_message
    capture_message("Test error from BRAiN", level="error")
    raise ValueError("This is a test error")
```

### Test Performance Tracking

```bash
# Make requests and check Sentry Performance dashboard
curl http://localhost:8000/api/missions/info

# View in Sentry:
# Performance → Transactions → /api/missions/info
```

---

## Resources

- [Sentry Documentation](https://docs.sentry.io/)
- [Python SDK](https://docs.sentry.io/platforms/python/)
- [FastAPI Integration](https://docs.sentry.io/platforms/python/guides/fastapi/)
- [Performance Monitoring](https://docs.sentry.io/product/performance/)
- [Error Tracking Best Practices](https://docs.sentry.io/product/issues/)

---

## Next Steps

Phase 2 continues with:
- **Application Performance Monitoring (APM)** - Extended transaction tracking
- **Alerting System** - Webhook-based alerts for critical events
- **Phase 2 Testing** - Comprehensive test suite

