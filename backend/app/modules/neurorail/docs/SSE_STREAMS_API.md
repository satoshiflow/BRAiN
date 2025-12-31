# NeuroRail SSE Streams API Documentation

**Version:** 1.0.0
**Sprint:** 4 (Phase 3)
**Status:** Production Ready

---

## Overview

The NeuroRail SSE (Server-Sent Events) Streams API provides **real-time event streaming** for all NeuroRail subsystems with:

- ✅ **7 dedicated channels** for different event types
- ✅ **Publisher-Subscriber pattern** with automatic cleanup
- ✅ **Event buffering** with configurable replay for late subscribers
- ✅ **Multi-criteria filtering** (channels, event types, entity IDs)
- ✅ **RBAC authorization** with 3 roles and 13 permissions
- ✅ **Type-safe TypeScript client** for frontend integration

---

## Table of Contents

1. [Event Channels](#event-channels)
2. [API Endpoints](#api-endpoints)
3. [Event Format](#event-format)
4. [Filtering](#filtering)
5. [RBAC Authorization](#rbac-authorization)
6. [Client Integration](#client-integration)
7. [Examples](#examples)
8. [Error Handling](#error-handling)

---

## Event Channels

NeuroRail provides **7 event channels** for different subsystem events:

| Channel | Purpose | Event Types |
|---------|---------|-------------|
| `audit` | Audit trail events | `execution_start`, `execution_success`, `execution_failure`, `decision_logged` |
| `lifecycle` | State machine transitions | `state_changed`, `transition_executed`, `orphan_detected` |
| `metrics` | Telemetry and performance | `metrics_recorded`, `snapshot_created`, `tt_first_signal` |
| `reflex` | Reflex system actions | `circuit_state_changed`, `trigger_activated`, `reflex_action`, `cooldown_activated` |
| `governor` | Governor decisions | `mode_decided`, `manifest_activated`, `rule_matched` |
| `enforcement` | Budget enforcement | `timeout_triggered`, `budget_exceeded`, `retry_exhausted` |
| `all` | All events (broadcast) | All event types from all channels |

**Note:** Subscribing to `all` receives events from all channels. Individual channel subscriptions are recommended for performance.

---

## API Endpoints

### 1. Stream Events (SSE)

**Endpoint:** `GET /api/neurorail/v1/stream/events`

**Description:** Real-time event streaming via Server-Sent Events (SSE)

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `channels` | `string[]` | No | Event channels to subscribe (default: `all`) |
| `event_types` | `string[]` | No | Filter by event types |
| `entity_ids` | `string[]` | No | Filter by entity IDs (mission, plan, job, attempt) |
| `replay_buffer` | `boolean` | No | Replay buffered events (default: `true`) |

**Response:**
- **Content-Type:** `text/event-stream`
- **Format:** SSE (id, event, data fields)

**Example Request:**
```bash
curl -N "http://localhost:8000/api/neurorail/v1/stream/events?channels=audit&channels=lifecycle&event_types=execution_start"
```

**Example Response:**
```
id: evt_abc123def456
event: execution_start
data: {"channel":"audit","event_type":"execution_start","data":{"attempt_id":"a_xyz789","job_type":"llm_call"},"timestamp":1703001234.56}

id: evt_ghi789jkl012
event: state_changed
data: {"channel":"lifecycle","event_type":"state_changed","data":{"entity_type":"attempt","entity_id":"a_xyz789","from_state":"pending","to_state":"running"},"timestamp":1703001235.12}
```

**RBAC Permissions Required:**
- `stream:events` (all roles)
- Plus channel-specific read permissions:
  - `read:audit` for `audit` channel
  - `read:lifecycle` for `lifecycle` channel
  - `read:metrics` for `metrics` channel

---

### 2. Stream Statistics

**Endpoint:** `GET /api/neurorail/v1/stream/stats`

**Description:** Get current SSE stream statistics

**Response:**
```json
{
  "total_subscribers": 5,
  "subscribers_by_channel": {
    "audit": 2,
    "lifecycle": 1,
    "all": 2
  },
  "buffer_sizes": {
    "audit": 100,
    "lifecycle": 100,
    "metrics": 100,
    "reflex": 100,
    "governor": 100,
    "enforcement": 100,
    "all": 100
  },
  "total_events_published": 1523
}
```

**RBAC Permissions Required:**
- `read:metrics`

---

## Event Format

All SSE events follow this structure:

### SSE Message Format

```
id: <event_id>
event: <event_type>
data: <json_payload>

```

**Fields:**
- `id`: Unique event identifier (e.g., `evt_abc123def456`)
- `event`: Event type (e.g., `execution_start`, `state_changed`)
- `data`: JSON payload with event details

### Event Payload Structure

```typescript
{
  "channel": "audit" | "lifecycle" | "metrics" | "reflex" | "governor" | "enforcement" | "all",
  "event_type": string,
  "data": {
    // Event-specific fields
  },
  "timestamp": number  // Unix timestamp with milliseconds
}
```

### Common Event Types

**Audit Channel:**
```json
{
  "channel": "audit",
  "event_type": "execution_start",
  "data": {
    "audit_id": "aud_abc123",
    "mission_id": "m_xyz789",
    "attempt_id": "a_qwe456",
    "message": "Execution started for attempt a_qwe456",
    "severity": "info"
  },
  "timestamp": 1703001234.56
}
```

**Lifecycle Channel:**
```json
{
  "channel": "lifecycle",
  "event_type": "state_changed",
  "data": {
    "transition_id": "tr_abc123",
    "entity_type": "job",
    "entity_id": "j_xyz789",
    "from_state": "queued",
    "to_state": "running",
    "transition_type": "start"
  },
  "timestamp": 1703001234.56
}
```

**Metrics Channel:**
```json
{
  "channel": "metrics",
  "event_type": "metrics_recorded",
  "data": {
    "attempt_id": "a_abc123",
    "duration_ms": 2345.67,
    "tokens_used": 1500,
    "cost": 0.05,
    "status": "succeeded"
  },
  "timestamp": 1703001234.56
}
```

**Reflex Channel:**
```json
{
  "channel": "reflex",
  "event_type": "circuit_state_changed",
  "data": {
    "circuit_id": "circuit_timeout_llm_call",
    "from_state": "closed",
    "to_state": "open",
    "failure_count": 5,
    "reason": "Timeout threshold exceeded"
  },
  "timestamp": 1703001234.56
}
```

---

## Filtering

### Channel Filtering

Subscribe to specific channels:

```bash
# Single channel
curl -N "http://localhost:8000/api/neurorail/v1/stream/events?channels=audit"

# Multiple channels
curl -N "http://localhost:8000/api/neurorail/v1/stream/events?channels=audit&channels=lifecycle"

# All channels (default)
curl -N "http://localhost:8000/api/neurorail/v1/stream/events?channels=all"
```

### Event Type Filtering

Filter by specific event types:

```bash
curl -N "http://localhost:8000/api/neurorail/v1/stream/events?event_types=execution_start&event_types=execution_success"
```

### Entity ID Filtering

Filter by entity IDs (mission, plan, job, attempt):

```bash
curl -N "http://localhost:8000/api/neurorail/v1/stream/events?entity_ids=a_abc123&entity_ids=j_xyz789"
```

### Combined Filtering

Combine multiple filters:

```bash
curl -N "http://localhost:8000/api/neurorail/v1/stream/events?channels=audit&event_types=execution_start&entity_ids=a_abc123"
```

### Replay Buffer

Control whether to replay buffered events (default: `true`):

```bash
# Replay last 100 events
curl -N "http://localhost:8000/api/neurorail/v1/stream/events?replay_buffer=true"

# Only receive new events
curl -N "http://localhost:8000/api/neurorail/v1/stream/events?replay_buffer=false"
```

---

## RBAC Authorization

### Roles and Permissions

| Role | Permissions | Description |
|------|-------------|-------------|
| **ADMIN** | All 13 permissions | Full access to all operations |
| **OPERATOR** | 11 permissions | Can read/write, execute operations (no RBAC management) |
| **VIEWER** | 6 permissions | Read-only access |

### Permission List

| Permission | Description | ADMIN | OPERATOR | VIEWER |
|------------|-------------|-------|----------|--------|
| `read:audit` | Read audit events | ✅ | ✅ | ✅ |
| `write:audit` | Write audit events | ✅ | ✅ | ❌ |
| `read:lifecycle` | Read lifecycle states | ✅ | ✅ | ✅ |
| `write:lifecycle` | Modify lifecycle states | ✅ | ✅ | ❌ |
| `read:metrics` | Read telemetry metrics | ✅ | ✅ | ✅ |
| `write:metrics` | Write telemetry metrics | ✅ | ✅ | ❌ |
| `execute:reflex` | Execute reflex actions | ✅ | ✅ | ❌ |
| `manage:governor` | Manage governor rules | ✅ | ✅ | ❌ |
| `manage:enforcement` | Manage budget enforcement | ✅ | ✅ | ❌ |
| `stream:events` | Subscribe to SSE streams | ✅ | ✅ | ✅ |
| `manage:rbac` | Manage RBAC policies | ✅ | ❌ | ❌ |
| `emergency:override` | Emergency overrides | ✅ | ❌ | ❌ |
| `system:admin` | System administration | ✅ | ❌ | ❌ |

### Authorization Endpoints

**Check Authorization:**

```bash
curl -X POST "http://localhost:8000/api/neurorail/v1/rbac/authorize" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "role": "operator",
    "required_permissions": ["read:audit", "stream:events"],
    "require_all": true
  }'
```

**Response:**
```json
{
  "allowed": true,
  "user_id": "user_123",
  "role": "operator",
  "required_permissions": ["read:audit", "stream:events"],
  "granted_permissions": ["read:audit", "stream:events"],
  "missing_permissions": []
}
```

**Get Role Permissions:**

```bash
curl "http://localhost:8000/api/neurorail/v1/rbac/permissions/operator"
```

**Response:**
```json
{
  "role": "operator",
  "permissions": [
    "read:audit",
    "write:audit",
    "read:lifecycle",
    "write:lifecycle",
    "read:metrics",
    "write:metrics",
    "execute:reflex",
    "manage:governor",
    "manage:enforcement",
    "stream:events",
    "emergency:override"
  ]
}
```

---

## Client Integration

### JavaScript/TypeScript (Browser)

```typescript
// Using native EventSource API
const eventSource = new EventSource(
  'http://localhost:8000/api/neurorail/v1/stream/events?channels=audit&channels=lifecycle'
);

eventSource.addEventListener('execution_start', (event) => {
  const data = JSON.parse(event.data);
  console.log('Execution started:', data);
});

eventSource.addEventListener('state_changed', (event) => {
  const data = JSON.parse(event.data);
  console.log('State changed:', data);
});

eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  eventSource.close();
};

// Auto-reconnect
eventSource.addEventListener('error', () => {
  setTimeout(() => {
    // Reconnect logic
  }, 3000);
});
```

### React Hook

```typescript
import { useState, useEffect, useCallback } from 'react';

export function useSSE(options: {
  channels?: string[];
  eventTypes?: string[];
  entityIds?: string[];
  autoReconnect?: boolean;
  reconnectDelay?: number;
}) {
  const [events, setEvents] = useState<any[]>([]);
  const [latestEvent, setLatestEvent] = useState<any | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const connect = useCallback(() => {
    const params = new URLSearchParams();
    options.channels?.forEach(c => params.append('channels', c));
    options.eventTypes?.forEach(t => params.append('event_types', t));
    options.entityIds?.forEach(id => params.append('entity_ids', id));

    const url = `/api/neurorail/v1/stream/events?${params.toString()}`;
    const eventSource = new EventSource(url);

    eventSource.onopen = () => setIsConnected(true);
    eventSource.onmessage = (event) => {
      const eventData = JSON.parse(event.data);
      setLatestEvent(eventData);
      setEvents(prev => [...prev, eventData]);
    };
    eventSource.onerror = () => {
      setIsConnected(false);
      eventSource.close();
      if (options.autoReconnect) {
        setTimeout(connect, options.reconnectDelay || 3000);
      }
    };

    return eventSource;
  }, [options]);

  useEffect(() => {
    const eventSource = connect();
    return () => eventSource.close();
  }, [connect]);

  return { events, latestEvent, isConnected };
}
```

### Python (Backend/Testing)

```python
import httpx
import json

async def stream_events():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            'GET',
            'http://localhost:8000/api/neurorail/v1/stream/events',
            params={'channels': ['audit', 'lifecycle']},
            timeout=None
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith('data:'):
                    data = json.loads(line[5:])
                    print(f"Event: {data['event_type']}, Data: {data['data']}")
```

---

## Examples

### Example 1: Monitor Execution Events

```bash
curl -N "http://localhost:8000/api/neurorail/v1/stream/events?channels=audit&event_types=execution_start&event_types=execution_success&event_types=execution_failure"
```

### Example 2: Track Job Lifecycle

```bash
curl -N "http://localhost:8000/api/neurorail/v1/stream/events?channels=lifecycle&entity_ids=j_abc123"
```

### Example 3: Monitor Circuit Breakers

```bash
curl -N "http://localhost:8000/api/neurorail/v1/stream/events?channels=reflex&event_types=circuit_state_changed"
```

### Example 4: Budget Violations

```bash
curl -N "http://localhost:8000/api/neurorail/v1/stream/events?channels=enforcement&event_types=timeout_triggered&event_types=budget_exceeded"
```

### Example 5: Multi-Entity Monitoring

```bash
curl -N "http://localhost:8000/api/neurorail/v1/stream/events?channels=all&entity_ids=a_abc123&entity_ids=a_def456&entity_ids=a_ghi789"
```

---

## Error Handling

### Connection Errors

**Symptom:** EventSource fires `error` event

**Causes:**
- Network disconnection
- Server restart
- Invalid query parameters

**Solution:**
```typescript
eventSource.onerror = (error) => {
  console.error('SSE connection error:', error);
  eventSource.close();

  // Auto-reconnect with exponential backoff
  setTimeout(() => {
    connectToSSE();
  }, 3000);
};
```

### Invalid Channel Error

**Request:**
```bash
curl -N "http://localhost:8000/api/neurorail/v1/stream/events?channels=invalid_channel"
```

**Response:**
```json
{
  "detail": [
    {
      "loc": ["query", "channels", 0],
      "msg": "value is not a valid enumeration member; permitted: 'audit', 'lifecycle', 'metrics', 'reflex', 'governor', 'enforcement', 'all'",
      "type": "type_error.enum"
    }
  ]
}
```

### Authorization Error

**Symptom:** 403 Forbidden

**Cause:** Insufficient permissions for requested channels

**Solution:** Check user role and required permissions using `/api/neurorail/v1/rbac/authorize`

### Buffer Overflow

**Symptom:** Missed events during high throughput

**Cause:** Subscriber queue full (default: 100 events)

**Solution:**
- Increase `queue_size` in subscriber configuration
- Process events faster
- Use `replay_buffer=false` to skip old events

---

## Performance Considerations

### Buffer Size

Default buffer size: **100 events per channel**

Configure via `SSEPublisher(buffer_size=N)` in backend.

### Subscriber Limits

No hard limit on concurrent subscribers, but consider:
- Each subscriber consumes memory for queue
- High subscriber count increases CPU for event broadcasting

**Recommended:** < 100 concurrent subscribers per channel

### Event Rate

Tested throughput: **500+ events/second** with 20 concurrent subscribers

### Auto-Cleanup

Dead subscribers (queue full, disconnected) are automatically removed.

---

## Security

### CORS

Configured CORS origins in `.env`:
```bash
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001","https://brain.falklabs.de"]
```

### Authentication

**Phase 1:** Development mode - auto ADMIN user
**Phase 2:** JWT-based authentication (planned)

### Rate Limiting

**Phase 1:** No rate limiting
**Phase 2:** Token bucket algorithm (planned)

---

## Troubleshooting

### Events Not Received

1. **Check connection:**
   ```bash
   curl -N "http://localhost:8000/api/neurorail/v1/stream/events?channels=all"
   ```

2. **Verify filters:**
   - Remove filters to see all events
   - Check channel names (case-sensitive)

3. **Check buffer replay:**
   - Set `replay_buffer=true` to receive recent events

### Connection Drops

1. **Check network:**
   - SSE requires persistent HTTP connection
   - Firewalls/proxies may close long-lived connections

2. **Implement auto-reconnect:**
   ```typescript
   eventSource.onerror = () => {
     setTimeout(() => reconnect(), 3000);
   };
   ```

### High Memory Usage

1. **Reduce buffer size:**
   ```python
   publisher = SSEPublisher(buffer_size=50)
   ```

2. **Limit subscriber count:**
   - Use shared SSE connection in frontend (React Context)

---

## API Reference Summary

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/neurorail/v1/stream/events` | GET | SSE event streaming | `stream:events` |
| `/api/neurorail/v1/stream/stats` | GET | Stream statistics | `read:metrics` |
| `/api/neurorail/v1/rbac/authorize` | POST | Check authorization | None |
| `/api/neurorail/v1/rbac/permissions/{role}` | GET | Get role permissions | None |

---

## Changelog

**1.0.0** (2025-12-31)
- Initial release
- 7 event channels
- RBAC authorization
- Multi-criteria filtering
- Auto-reconnect support
- Buffer replay
- Complete TypeScript client

---

## Support

For issues or questions:
- GitHub: https://github.com/satoshiflow/BRAiN/issues
- Documentation: `/backend/app/modules/neurorail/README.md`
