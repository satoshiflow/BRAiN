# AXE Core API - Connector Author Guide

**Version:** 1.0.0
**Audience:** Developers building new BRAIN connectors
**Prerequisite:** Read `REPOSITORY_ANALYSE.md` for architecture overview

---

## Overview

All BRAIN connectors are **dumb clients** that route messages through the AXE Core API.
Connectors handle platform-specific I/O (Telegram, WhatsApp, CLI, Voice) but delegate
all intelligence to BRAIN via AXE.

```
User -> [Connector] -> POST /api/axe/message -> [AXE Core] -> [BRAIN/LLM]
                                                     |
User <- [Connector] <- JSON Response <---------------+
```

---

## Authentication: DMZ Gateway Headers

AXE uses a **fail-closed** Trust Tier system. Connectors must authenticate as DMZ gateways.

### Required Headers

```http
X-DMZ-Gateway-ID: telegram_gateway
X-DMZ-Gateway-Token: <sha256_hash>
```

### Token Generation

```python
import hashlib

gateway_id = "telegram_gateway"
shared_secret = "YOUR_SHARED_SECRET"  # From env: AXE_DMZ_SHARED_SECRET
token = hashlib.sha256(f"{gateway_id}:{shared_secret}".encode()).hexdigest()
```

### Trust Tiers

| Tier | Condition | Access |
|------|-----------|--------|
| `LOCAL` | Request from 127.0.0.1 / ::1 | Allowed |
| `DMZ` | Valid gateway ID + token | Allowed |
| `EXTERNAL` | Everything else | **403 Forbidden** |

### Known Gateway IDs

Pre-registered in `axe_governance/__init__.py`:

- `telegram_gateway`
- `whatsapp_gateway`
- `discord_gateway`
- `email_gateway`

To add a new gateway, add to `KNOWN_DMZ_GATEWAYS` set.

---

## Endpoints

### POST /api/axe/message

**The primary endpoint for all connector communication.**

#### Request

```json
{
  "message": "User's message text",
  "metadata": {
    "connector_id": "telegram_connector",
    "connector_type": "telegram",
    "user_id": "user_123",
    "username": "alice",
    "message_id": "msg_abc123",
    "content_type": "text",
    "session_id": "session_xyz"
  }
}
```

#### Response (Gateway Mode)

```json
{
  "mode": "gateway",
  "gateway": "openai_gateway",
  "input_message": "User's message text",
  "reply": "BRAIN's response",
  "result": { "original_gateway_response": {} },
  "governance": {
    "trust_tier": "dmz",
    "source_service": "telegram_gateway",
    "request_id": "uuid"
  }
}
```

#### Response (LLM Fallback)

```json
{
  "mode": "llm-fallback",
  "gateway": "none",
  "input_message": "User's message text",
  "reply": "LLM response text",
  "result": { "raw_llm": { "response": "...", "model": "llama3.2:latest" } },
  "governance": {
    "trust_tier": "local",
    "request_id": "uuid"
  }
}
```

#### Error Response (403)

```json
{
  "error": "Forbidden",
  "message": "AXE is only accessible via DMZ gateways",
  "trust_tier": "external",
  "request_id": "uuid"
}
```

### GET /api/axe/info

System info with governance context. Use for health checks.

```json
{
  "name": "AXE",
  "version": "2.0-governance",
  "status": "online",
  "gateway": "openai_gateway or none",
  "governance": {
    "trust_tier": "dmz",
    "source_service": "telegram_gateway",
    "authenticated": true,
    "request_id": "uuid"
  }
}
```

### GET /api/axe/config/{app_id}

Widget configuration for app-specific deployments.

### WebSocket /api/axe/ws/{session_id}

Real-time bidirectional communication. Protocol:

| Direction | Type | Payload |
|-----------|------|---------|
| Client->Server | `chat` | `{ message: string }` |
| Client->Server | `ping` | `{}` |
| Client->Server | `diff_applied` | `{ diff_id: string }` |
| Client->Server | `diff_rejected` | `{ diff_id: string, reason?: string }` |
| Server->Client | `chat_response` | `{ message: string, metadata: {} }` |
| Server->Client | `pong` | `{}` |
| Server->Client | `diff` | `{ file_id, old_content, new_content }` |
| Server->Client | `error` | `{ message: string }` |

### POST /api/axe/events

Telemetry event submission (single or batch).

---

## Using BaseConnector

All connectors should extend `BaseConnector`. The `send_to_brain()` method handles
AXE Core communication, DMZ headers, error handling, and stats tracking.

```python
from app.modules.connectors.base_connector import BaseConnector
from app.modules.connectors.schemas import (
    ConnectorCapability, ConnectorHealth, ConnectorStatus,
    ConnectorType, IncomingMessage, OutgoingMessage, UserInfo,
)

class MyConnector(BaseConnector):
    def __init__(self):
        super().__init__(
            connector_id="my_connector",
            connector_type=ConnectorType.API,
            display_name="My Connector",
            capabilities=[ConnectorCapability.TEXT],
            axe_base_url="http://localhost:8000",
            dmz_gateway_id="my_gateway",          # Must be in KNOWN_DMZ_GATEWAYS
            dmz_shared_secret="shared_secret",     # From environment
        )

    async def start(self) -> None:
        await self._on_start()
        # Your initialization logic
        self._set_status(ConnectorStatus.CONNECTED)

    async def stop(self) -> None:
        # Your cleanup logic
        await self._on_stop()

    async def send_to_user(self, user_id: str, message: OutgoingMessage) -> bool:
        # Platform-specific message delivery
        return True

    async def health_check(self) -> ConnectorHealth:
        return ConnectorHealth(
            connector_id=self.connector_id,
            status=self._status,
        )
```

### Message Flow

```python
# 1. Receive platform message (your code)
# 2. Create IncomingMessage
msg = IncomingMessage(
    connector_id=self.connector_id,
    connector_type=self.connector_type,
    user=UserInfo(user_id="123", username="alice"),
    content="Hello BRAIN",
    session_id="session_abc",
)

# 3. Route through AXE Core (BaseConnector handles everything)
response = await self.process_message(msg)
# response is an OutgoingMessage with BRAIN's reply

# 4. Deliver to user (your code)
await self.send_to_user("123", response)
```

---

## Registration

Register your connector with ConnectorService:

```python
from app.modules.connectors.service import get_connector_service

service = get_connector_service()
service.register(MyConnector())
await service.start_connector("my_connector")
```

The REST API at `/api/connectors/v2/` exposes lifecycle management.

---

## Checklist for New Connectors

- [ ] Extend `BaseConnector`
- [ ] Implement `start()`, `stop()`, `send_to_user()`, `health_check()`
- [ ] Add gateway ID to `KNOWN_DMZ_GATEWAYS` in `axe_governance/__init__.py`
- [ ] Set `dmz_shared_secret` from environment variable
- [ ] Register with `ConnectorService`
- [ ] Add tests (30+ recommended)
- [ ] Add events to `EVENTS.md`
