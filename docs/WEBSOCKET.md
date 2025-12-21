# **BRAiN WebSocket System**

**Version:** 1.0.0
**Created:** 2025-12-20
**Phase:** 5 - Developer Experience & Advanced Features

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Connection Management](#connection-management)
4. [Channel System](#channel-system)
5. [Event Broadcasting](#event-broadcasting)
6. [API Reference](#api-reference)
7. [Client Integration](#client-integration)
8. [Testing](#testing)
9. [Best Practices](#best-practices)

---

## Overview

BRAiN's WebSocket system provides real-time, bidirectional communication between the server and clients with advanced features:

**Features:**
- **Connection Pooling** - Manage multiple concurrent connections
- **Channel Subscriptions** - Pub/sub pattern for targeted messaging
- **User-based Messaging** - Send messages to specific users
- **Broadcast Messaging** - Broadcast to channels or all connections
- **Heartbeat/Keepalive** - Automatic connection health monitoring
- **Authentication** - Optional token-based authentication
- **Event System** - Type-safe event emitters for common operations

**Technology:**
- **FastAPI WebSockets** - Built on Starlette WebSocket support
- **Async/Await** - Full async support for high concurrency
- **Pydantic Models** - Type-safe message validation

---

## Architecture

### Components

```
┌─────────────────┐
│   WebSocket     │
│   Client        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   WebSocket     │  /ws/connect
│   Endpoint      │  /ws/channel/{name}
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   WebSocket     │  Connection Management
│   Manager       │  Channel Subscriptions
└────────┬────────┘
         │
         ├──────────┬──────────┬──────────┐
         ▼          ▼          ▼          ▼
    [Channel 1] [Channel 2] [Channel 3] [...]
         │          │          │          │
         ▼          ▼          ▼          ▼
    [Clients]  [Clients]  [Clients]  [Clients]
```

### Standard Channels

| Channel | Purpose | Events |
|---------|---------|--------|
| `missions` | Mission updates | created, started, completed, failed |
| `agents` | Agent status | started, stopped, heartbeat, error |
| `system` | System events | startup, shutdown, health, alerts |
| `tasks` | Background tasks | queued, started, completed, failed |
| `audit` | Audit logs | audit_log |
| `metrics` | Performance metrics | metrics_update |

---

## Connection Management

### Connecting

**WebSocket URL:**
```
ws://localhost:8000/ws/connect
ws://localhost:8000/ws/connect?token=<auth_token>
```

**JavaScript Example:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/connect');

ws.onopen = () => {
    console.log('Connected');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.onerror = (error) => {
    console.error('Error:', error);
};

ws.onclose = () => {
    console.log('Disconnected');
};
```

**Welcome Message:**
```json
{
    "type": "connected",
    "connection_id": "uuid-here",
    "timestamp": 1703001234.56
}
```

### Heartbeat

The server sends periodic **ping** messages every 30 seconds:

```json
{
    "type": "ping",
    "timestamp": 1703001234.56
}
```

**Client Response:**
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong' }));
    }
};
```

### Disconnecting

```javascript
ws.close();
```

---

## Channel System

### Subscribing to Channels

**Subscribe Message:**
```javascript
ws.send(JSON.stringify({
    type: 'subscribe',
    channel: 'missions'
}));
```

**Confirmation:**
```json
{
    "type": "subscribed",
    "channel": "missions",
    "timestamp": 1703001234.56
}
```

### Unsubscribing

**Unsubscribe Message:**
```javascript
ws.send(JSON.stringify({
    type: 'unsubscribe',
    channel: 'missions'
}));
```

**Confirmation:**
```json
{
    "type": "unsubscribed",
    "channel": "missions",
    "timestamp": 1703001234.56
}
```

### Channel-Specific Connection

Connect directly to a specific channel:

```
ws://localhost:8000/ws/channel/missions
```

This automatically subscribes you to the channel on connection.

---

## Event Broadcasting

### Backend Event Emitters

**Import:**
```python
from backend.app.core.events import (
    emit_mission_created,
    emit_mission_completed,
    emit_agent_started,
    emit_system_alert
)
```

**Mission Events:**
```python
# Mission created
await emit_mission_created(
    mission_id="mission_123",
    mission_data={
        "name": "Deploy Application",
        "priority": "high"
    }
)

# Mission completed
await emit_mission_completed(
    mission_id="mission_123",
    result={"status": "success"}
)

# Mission failed
await emit_mission_failed(
    mission_id="mission_123",
    error="Deployment failed: timeout"
)
```

**Agent Events:**
```python
# Agent started
await emit_agent_started(agent_id="ops_agent")

# Agent heartbeat
await emit_agent_heartbeat(
    agent_id="ops_agent",
    status={"health": "good", "tasks": 5}
)

# Agent error
await emit_agent_error(
    agent_id="ops_agent",
    error="Task execution failed"
)
```

**System Events:**
```python
# System alert
await emit_system_alert(
    level="warning",
    message="High memory usage detected",
    details={"memory_percent": 92.5}
)

# System health
await emit_system_health({
    "status": "healthy",
    "checks": {...}
})
```

**Task Events:**
```python
# Task started
await emit_task_started(
    task_id="task_abc123",
    task_name="send_email"
)

# Task completed
await emit_task_completed(
    task_id="task_abc123",
    task_name="send_email",
    result={"sent": True}
)
```

### Custom Events

```python
from backend.app.core.events import emit_event, EventChannel

await emit_event(
    channel=EventChannel.SYSTEM,
    event_type="custom_event",
    data={
        "custom_field": "value",
        "timestamp": time.time()
    }
)
```

---

## API Reference

### WebSocket Endpoints

**Main Connection:**
```
WS /ws/connect?token={optional_token}
```

**Channel Connection:**
```
WS /ws/channel/{channel}?token={optional_token}
```

### HTTP API Endpoints

**Broadcast to Channel:**
```http
POST /api/ws/broadcast
```

Request:
```json
{
    "channel": "missions",
    "message": {
        "mission_id": "mission_123",
        "status": "completed"
    },
    "type": "mission_update"
}
```

Response:
```json
{
    "status": "broadcasted",
    "channel": "missions",
    "subscribers": 15
}
```

**Broadcast to All:**
```http
POST /api/ws/broadcast/all
```

Request:
```json
{
    "type": "system_announcement",
    "data": {
        "message": "System maintenance in 5 minutes"
    }
}
```

**Get Statistics:**
```http
GET /api/ws/stats
```

Response:
```json
{
    "total_connections": 42,
    "total_users": 15,
    "total_channels": 5,
    "channels": {
        "missions": 20,
        "agents": 12,
        "system": 42
    }
}
```

**Get Channel Subscribers:**
```http
GET /api/ws/channels/{channel}
```

Response:
```json
{
    "channel": "missions",
    "subscribers": 20,
    "connection_ids": ["uuid1", "uuid2", ...]
}
```

---

## Client Integration

### React Hook Example

```typescript
// hooks/useWebSocket.ts
import { useEffect, useState, useCallback } from 'react';

interface WebSocketMessage {
    type: string;
    data?: any;
    channel?: string;
    timestamp?: number;
}

export function useWebSocket(url: string) {
    const [ws, setWs] = useState<WebSocket | null>(null);
    const [connected, setConnected] = useState(false);
    const [messages, setMessages] = useState<WebSocketMessage[]>([]);

    useEffect(() => {
        const websocket = new WebSocket(url);

        websocket.onopen = () => {
            setConnected(true);
            console.log('WebSocket connected');
        };

        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);

            // Auto-respond to ping
            if (data.type === 'ping') {
                websocket.send(JSON.stringify({ type: 'pong' }));
            }

            setMessages((prev) => [...prev, data]);
        };

        websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        websocket.onclose = () => {
            setConnected(false);
            console.log('WebSocket disconnected');
        };

        setWs(websocket);

        return () => {
            websocket.close();
        };
    }, [url]);

    const subscribe = useCallback((channel: string) => {
        if (ws && connected) {
            ws.send(JSON.stringify({ type: 'subscribe', channel }));
        }
    }, [ws, connected]);

    const unsubscribe = useCallback((channel: string) => {
        if (ws && connected) {
            ws.send(JSON.stringify({ type: 'unsubscribe', channel }));
        }
    }, [ws, connected]);

    const sendMessage = useCallback((message: any) => {
        if (ws && connected) {
            ws.send(JSON.stringify(message));
        }
    }, [ws, connected]);

    return {
        connected,
        messages,
        subscribe,
        unsubscribe,
        sendMessage,
    };
}
```

**Usage:**
```typescript
function MissionDashboard() {
    const { connected, messages, subscribe } = useWebSocket(
        'ws://localhost:8000/ws/connect'
    );

    useEffect(() => {
        if (connected) {
            subscribe('missions');
        }
    }, [connected, subscribe]);

    // Filter mission messages
    const missionMessages = messages.filter(
        (msg) => msg.channel === 'missions'
    );

    return (
        <div>
            <h2>Status: {connected ? 'Connected' : 'Disconnected'}</h2>
            <ul>
                {missionMessages.map((msg, i) => (
                    <li key={i}>{msg.type}: {JSON.stringify(msg.data)}</li>
                ))}
            </ul>
        </div>
    );
}
```

### Vue 3 Example

```typescript
// composables/useWebSocket.ts
import { ref, onMounted, onUnmounted } from 'vue';

export function useWebSocket(url: string) {
    const ws = ref<WebSocket | null>(null);
    const connected = ref(false);
    const messages = ref<any[]>([]);

    onMounted(() => {
        ws.value = new WebSocket(url);

        ws.value.onopen = () => {
            connected.value = true;
        };

        ws.value.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'ping') {
                ws.value?.send(JSON.stringify({ type: 'pong' }));
            }

            messages.value.push(data);
        };

        ws.value.onclose = () => {
            connected.value = false;
        };
    });

    onUnmounted(() => {
        ws.value?.close();
    });

    const subscribe = (channel: string) => {
        ws.value?.send(JSON.stringify({ type: 'subscribe', channel }));
    };

    return {
        connected,
        messages,
        subscribe,
    };
}
```

---

## Testing

### Test Client

BRAiN includes a web-based test client:

**URL:** http://localhost:8000/static/websocket_test.html

**Features:**
- Connect/disconnect
- Subscribe to channels
- Send custom messages
- View all messages
- Auto-respond to pings

### Manual Testing

**Using `wscat`:**
```bash
npm install -g wscat

# Connect
wscat -c ws://localhost:8000/ws/connect

# Subscribe to channel
> {"type": "subscribe", "channel": "missions"}

# Send pong
> {"type": "pong"}
```

**Using Python:**
```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/connect"

    async with websockets.connect(uri) as websocket:
        # Receive welcome message
        message = await websocket.recv()
        print(f"Received: {message}")

        # Subscribe to channel
        await websocket.send(json.dumps({
            "type": "subscribe",
            "channel": "missions"
        }))

        # Listen for messages
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"Received: {data}")

            # Respond to ping
            if data.get("type") == "ping":
                await websocket.send(json.dumps({"type": "pong"}))

asyncio.run(test_websocket())
```

---

## Best Practices

### Client-Side

✅ **DO:**
- Handle reconnection on disconnect
- Respond to ping messages
- Use try-catch for JSON parsing
- Implement exponential backoff for reconnects
- Unsubscribe when no longer needed

❌ **DON'T:**
- Ignore ping messages (connection will timeout)
- Send large payloads (>64KB)
- Subscribe to unused channels
- Open multiple connections per client

**Reconnection Pattern:**
```javascript
class WebSocketClient {
    constructor(url) {
        this.url = url;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.connect();
    }

    connect() {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log('Connected');
            this.reconnectDelay = 1000; // Reset delay
        };

        this.ws.onclose = () => {
            console.log('Disconnected, reconnecting...');
            setTimeout(() => {
                this.reconnectDelay = Math.min(
                    this.reconnectDelay * 2,
                    this.maxReconnectDelay
                );
                this.connect();
            }, this.reconnectDelay);
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'ping') {
                this.ws.send(JSON.stringify({ type: 'pong' }));
            }

            this.handleMessage(data);
        };
    }

    handleMessage(data) {
        // Override in subclass
    }
}
```

### Server-Side

✅ **DO:**
- Use event emitters for broadcasting
- Clean up on disconnect
- Validate message types
- Use channels for targeted messages
- Monitor connection counts

❌ **DON'T:**
- Block in WebSocket handlers
- Store state in connection objects
- Send messages to disconnected clients
- Create circular event loops

**Event Emission Pattern:**
```python
# ✅ GOOD - Use event emitters
from backend.app.core.events import emit_mission_completed

await emit_mission_completed(
    mission_id="mission_123",
    result={"status": "success"}
)

# ❌ BAD - Manual broadcast
from backend.app.core.websocket import get_websocket_manager

manager = get_websocket_manager()
await manager.broadcast_to_channel("missions", {
    "type": "mission_completed",
    "mission_id": "mission_123"
})  # Use event emitters instead!
```

---

## Performance Considerations

**Connection Limits:**
- Default: 1000 concurrent connections per server
- Scale horizontally with multiple servers + Redis pub/sub

**Message Size:**
- Recommended: <16KB per message
- Maximum: 64KB (WebSocket frame limit)

**Broadcast Performance:**
- 1000 connections: <10ms
- 10,000 connections: <100ms
- Use channels to reduce unnecessary broadcasts

**Memory Usage:**
- ~1MB per 100 connections
- Heartbeat overhead: ~10 bytes per connection per 30s

---

## Troubleshooting

### Connection Refused

**Check:**
```bash
# Verify server is running
curl http://localhost:8000/api/ws/info

# Check WebSocket stats
curl http://localhost:8000/api/ws/stats
```

### Messages Not Received

**Check subscription:**
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'subscribed') {
        console.log('Successfully subscribed to:', data.channel);
    }
};
```

### Connection Timeout

**Cause:** Not responding to ping messages

**Fix:**
```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong' }));
    }
};
```

---

## References

- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [WebSocket MDN](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [BRAiN CLAUDE.md](../CLAUDE.md)

---

**Last Updated:** 2025-12-20
**Maintainer:** BRAiN Development Team
**Phase:** 5 - Developer Experience & Advanced Features
