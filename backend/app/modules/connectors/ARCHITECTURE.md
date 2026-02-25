# Connectors Module Architecture - Synapse Layer

**Version:** 2.0
**Status:** Active Implementation
**Last Updated:** 2026-02-25

---

## Overview

The Connectors Module implements a **Synapse Layer** - the neural bridge connecting BRAIN Core to external systems and users. Like biological synapses that transmit signals between neurons, this module:

- **Receives** signals from external platforms (Telegram, Voice, WhatsApp, CLI)
- **Processes** those signals through a unified interface
- **Routes** them to BRAIN Core (AXE) for intelligence
- **Returns** responses back to the originating platform

**Key Principle:** All connectors are "dumb clients" - they handle platform-specific I/O but delegate all intelligence to AXE Core.

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│ EXTERNAL PLATFORMS                                      │
│ (Telegram, Voice, WhatsApp, CLI, etc.)                 │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│ CONNECTOR ADAPTERS (Platform-Specific I/O)             │
│ ┌──────────────┐  ┌────────────┐  ┌─────────────────┐  │
│ │   Telegram   │  │    Voice   │  │    WhatsApp     │  │
│ │  Connector   │  │  Connector │  │    Connector    │  │
│ └──────┬───────┘  └────┬───────┘  └────────┬────────┘  │
│        │               │                   │            │
│        └───────────────┼───────────────────┘            │
│                        │                                │
└────────────────────────┼────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ SYNAPSE INTERFACE (BaseConnector)                      │
│ - Unified message format                               │
│ - Lifecycle management (start/stop)                    │
│ - Health checking                                      │
│ - Status & stats tracking                              │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ ROUTER (REST API)                                      │
│ - /list (list connectors)                              │
│ - /{id}/action (start/stop/restart)                    │
│ - /{id}/health (health check)                          │
│ - /send (send message to user)                         │
│ - /stats (aggregate stats)                             │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ AXE CORE / MISSION CONTROL                             │
│ (Intelligence & Decision Making)                       │
└──────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Base Connector Interface

The abstract foundation that all connectors implement.

**Key Methods:**
- `async start()` - Start the connector  
- `async stop()` - Graceful shutdown
- `async send_to_user()` - Platform-specific delivery
- `async health_check()` - Health status check
- `async send_to_brain()` - Route to AXE Core (provided by base class)

**Status Lifecycle:**
```
STOPPED → CONNECTING → CONNECTED → ERROR (→ RECONNECTING)
```

**Capabilities:**
- TEXT: Send/receive text messages
- VOICE: Audio communication  
- FILE: File transfer support
- BUTTONS: Interactive UI elements

### 2. Current Connector Implementations

**Telegram** - Telegram Bot API integration
- Capabilities: TEXT, FILE, BUTTONS
- Features: Webhook/polling, inline keyboards, file upload

**Voice** - Audio I/O (STT/TTS)
- Capabilities: VOICE, TEXT
- Providers: OpenAI, Google (pluggable)

**WhatsApp** - WhatsApp Business API
- Capabilities: TEXT, FILE, BUTTONS
- Features: Media handling, templates

**CLI** - Command-line interface
- Capabilities: TEXT
- Purpose: Local testing/development

---

## Security Model

### Authentication & Authorization
- All endpoints require `require_auth` dependency
- HMAC-SHA256 message signing for AXE Core communication
- DMZ gateway ID & shared secret per connector

### Input Validation
- Pydantic schemas with max_length constraints
- Content max 10,000 characters
- Type validation (text, binary)
- Sanitization of control characters

### Secret Management  
Platform secrets loaded from environment variables (never hardcoded):
- `BRAIN_TELEGRAM_TOKEN`
- `BRAIN_WHATSAPP_API_KEY`
- `BRAIN_DMZ_SHARED_SECRET`

### Rate Limiting
- Per-connector quotas (100 msgs/min default)
- Backpressure handling with message queues
- Premium tier support

---

## Integration with BRAIN Core

### Message Flow
```
User → Connector.receive() 
  → IncomingMessage validation
  → BaseConnector.send_to_brain() [HMAC signed]
  → AXE Core processes  
  → Connector.send_to_user()
  → User response
```

### AXE Core API Endpoints Required
- `POST /api/axe/mission/process` - Process message
- `GET /api/axe/health` - Availability check
- `POST /api/axe/context/{session_id}` - Context storage

### Event Publishing
Connectors publish events to event stream:
- `connector.message.received` - User sent message
- `connector.message.sent` - BRAIN sent response
- `connector.connected` / `connector.disconnected`
- `connector.error` - Errors occurred

---

## REST API Endpoints

**List Connectors:**
```
GET /api/connectors/v2/list
  ?connector_type=TELEGRAM&active_only=false
```

**Get Connector Info:**
```
GET /api/connectors/v2/{connector_id}
```

**Connector Actions:**
```
POST /api/connectors/v2/{connector_id}/action
Body: {"action": "start|stop|restart"}
```

**Health Check:**
```
GET /api/connectors/v2/{connector_id}/health
GET /api/connectors/v2/health/all
```

**Send Message:**
```
POST /api/connectors/v2/send
Body: {
  "connector_id": "telegram_prod",
  "user_id": "alice",
  "content": "Hello",
  "content_type": "text"
}
```

**Statistics:**
```
GET /api/connectors/v2/stats/aggregate
GET /api/connectors/v2/{connector_id}/stats
```

---

## Roadmap & Enhancements

### Phase 1: Persistent Registry (Q1 2026)
- [ ] PostgreSQL connector registry
- [ ] Dynamic connector discovery
- [ ] No-restart connector updates

### Phase 2: MCP Server Integration (Q2 2026)
- [ ] Wrap connectors as MCP servers
- [ ] Direct Claude API integration
- [ ] Self-service connector wrapping

### Phase 3: Event Streaming (Q2 2026)
- [ ] Real-time event publishing
- [ ] Reactive workflow triggers
- [ ] Live dashboard updates

### Phase 4: Advanced Routing (Q3 2026)
- [ ] User connector preferences
- [ ] Smart routing by context
- [ ] Fallback chains

### Phase 5: Conversation Memory (Q3 2026)
- [ ] Persistent history storage
- [ ] Context-aware responses
- [ ] Conversation search

---

## Known Limitations

1. **In-Memory Registry** - Connectors lost on restart (Phase 1 fix)
2. **No User Preferences** - All users get same connector (Phase 4 fix)
3. **Session-Only Context** - No persistent memory (Phase 5 fix)
4. **No Auto-Reconnection** - Messages dropped if AXE unavailable (Phase 2 fix)

---

## Security Checklist

- [x] All endpoints authenticated (require_auth)
- [x] Platform secrets from environment variables
- [x] HMAC message signing for AXE communication
- [x] Input validation with schema constraints
- [x] Error sanitization
- [x] Rate limiting per connector
- [ ] Audit logging for sensitive operations (TODO)
- [ ] Conversation history encryption (TODO)
- [ ] Fine-grained RBAC per connector (TODO)

---

## Testing

**Unit tests:** `pytest tests/test_connectors.py -v`
**Integration tests:** `pytest tests/test_[platform].py -v`
**Manual testing:** Use CLI connector for development

---

**Maintained By:** BRAIN Security Team
**Last Updated:** 2026-02-25
