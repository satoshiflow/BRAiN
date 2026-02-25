# BRAiN Connectors - Synapse Layer Architecture

**Version:** 2.0 - Synapse Enhancement Design
**Date:** 2026-02-25
**Status:** Design Document (Enhancement Roadmap)

---

## EXECUTIVE SUMMARY

The **Connectors module** implements a **Synapse-like layer** that acts as a universal bridge between external platforms (Telegram, WhatsApp, Voice, CLI) and the core BRAiN intelligence system (via AXE Core). This document outlines the current architecture, integration patterns, security posture, and enhancement opportunities aligned with a "Universal Connector / Synapse Layer" vision.

---

## SECTION 1: CURRENT ARCHITECTURE

### 1.1 Module Position in BRAiN System

```
┌─────────────────────────────────────────────────────────────┐
│                    CONNECTORS LAYER                          │
│          (Synapse: Platform-Agnostic Integration)            │
└──────────────┬────────────────────────────────────┬──────────┘
               │                                    │
      [External Platforms]              [BRAIN Core]
      ├─ Telegram                      ├─ AXE Core
      ├─ WhatsApp                      ├─ LLM Routers
      ├─ Voice (STT/TTS)               ├─ Mission Control
      └─ CLI (Local)                   └─ Governance
```

**Key Principle:** Connectors are "dumb clients" that:
- Handle **platform-specific I/O only** (receive from user, send to user)
- Delegate **all business logic to AXE Core** (message routing, governance, auth)
- Enforce **fail-closed security** (DMZ Gateway authentication)
- Maintain **state-minimalism** (stateless request/response pairs)

### 1.2 Integration Points

#### Integration with AXE Core
- **Endpoint:** `POST /api/axe/message`
- **Auth:** DMZ Gateway headers (X-DMZ-Gateway-ID, X-DMZ-Gateway-Token)
- **Flow:**
  1. Connector receives external message
  2. Converts to standard format → `IncomingMessage`
  3. POST to AXE Core with DMZ gateway auth
  4. Receives `BrainResponse` JSON
  5. Converts back to platform format
  6. Sends via `send_to_user()`

#### Integration with Governance (DMZ + Threat Detection)
- **Current:** Basic auth via DMZ gateway token
- **Path:** AXE Core validates connector source in trust tier system
- **Missing:** Audit trail for connector-originated requests (enhancement)

#### Integration with Missions/Workflows
- **Current:** Connector messages flow through AXE Core to Mission system
- **Path:** Not directly coupled (decoupled via AXE)
- **Enhancement:** Event emission for connector actions (see Section 4)

#### Integration with Memory/Context
- **Current:** None (stateless)
- **Session ID:** Included in metadata for correlation
- **Enhancement:** Persistent session context (see Section 4)

#### Integration with Events/Observability
- **Current:** Basic logging via loguru
- **Missing:** Structured event stream for connector lifecycle (enhancement)

---

## SECTION 2: ADAPTER/DRIVER PATTERN

### 2.1 Driver vs Adapter Distinction

**Recommendation:** Clarify the boundary between "drivers" (platform technology) and "adapters" (connector implementations).

```
┌─────────────────────────────────────────┐
│      CONNECTOR LAYER COMPONENTS         │
├─────────────────────────────────────────┤
│                                         │
│  DRIVERS (Platform-Specific Tech)       │
│  ├─ Telegram Bot API SDK                │
│  ├─ WhatsApp Cloud API                  │
│  ├─ Voice: STT (Whisper), TTS (TTS API) │
│  └─ CLI: stdin/stdout                   │
│                                         │
│  ADAPTERS (Connector Implementations)   │
│  ├─ TelegramConnector(BaseConnector)    │
│  ├─ WhatsAppConnector(BaseConnector)    │
│  ├─ VoiceConnector(BaseConnector)       │
│  └─ CLIConnector(BaseConnector)         │
│                                         │
│  REGISTRY (Connector Management)        │
│  └─ ConnectorService                    │
│                                         │
│  SCHEMAS (Message Contracts)            │
│  ├─ IncomingMessage                     │
│  ├─ OutgoingMessage                     │
│  └─ Attachment, etc.                    │
│                                         │
└─────────────────────────────────────────┘
```

### 2.2 Current Adapters

| Adapter | Driver | Status | Capabilities |
|---------|--------|--------|--------------|
| **TelegramConnector** | `python-telegram-bot` | ✅ Implemented | Text, Photos, Inline Keyboards |
| **WhatsAppConnector** | WhatsApp Cloud API | ✅ Implemented | Text, Media, Templates |
| **VoiceConnector** | Whisper (STT), TTS API | ✅ Implemented | Audio Input/Output |
| **CLIConnector** | stdin/stdout | ✅ Implemented | Text (dev/testing) |

### 2.3 Registry & Target Catalog

**Current Status:** Service-based registry in `ConnectorService`

```python
# Current approach (working)
service = get_connector_service()
connector = service.get(connector_id)  # In-memory registry
```

**Enhancement Recommendation:**
- Introduce `ConnectorRegistry` with configuration source options
- Support loading from: environment variables, YAML files, database
- Enable connector auto-discovery and hot-reloading

**Example Proposal (YAML-based registry):**
```yaml
# storage/connectors/registry.yaml
connectors:
  telegram:
    adapter: TelegramConnector
    driver_config:
      api_token: ${TELEGRAM_BOT_TOKEN}
      polling: true
    capabilities: [TEXT, PHOTOS, AUDIO]
    trusted: true

  whatsapp:
    adapter: WhatsAppConnector
    driver_config:
      api_url: https://graph.instagram.com/v18.0
      access_token: ${WHATSAPP_ACCESS_TOKEN}
    capabilities: [TEXT, MEDIA]
    trusted: true
```

---

## SECTION 3: SECURITY ASSESSMENT

### 3.1 Authentication & Authorization Status

| Component | Status | Details |
|-----------|--------|---------|
| **Router** | ✅ Protected | `Depends(require_auth)` on all endpoints |
| **AXE Core Comm** | ✅ Protected | DMZ Gateway header auth |
| **Connector Execution** | ✅ Protected | Role-based (implicit via router) |
| **Message Input** | ✅ Validated | Pydantic schemas validate structure |
| **Attachment Handling** | 🟡 Partial | Size limits exist, but format validation weak |

### 3.2 Input Validation

**Current strengths:**
- ✅ Pydantic models enforce message structure
- ✅ Size limits on text fields (max_length constraints needed in schemas - see enhancement section 4)
- ✅ Attachment types validated

**Gaps:**
- ❌ No rate limiting per connector
- ❌ No payload size limits (total message size unconstrained)
- ❌ Attachment MIME type validation weak

### 3.3 Secret/Token Handling

**Current status:**
```python
# ✅ CORRECT: Loaded from environment
telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
whatsapp_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
```

**Security:** ✅ No hardcoded secrets detected

### 3.4 Threat Assessment

| Threat | Current Risk | Mitigation |
|--------|--------------|-----------|
| **Unauthenticated Requests** | ✅ Low | Router-level auth |
| **Malformed Input** | ✅ Low | Pydantic validation |
| **Large Payload Attack** | 🟡 Medium | No size limit on entire message |
| **Rate Limiting Bypass** | 🔴 High | No per-user rate limits |
| **Attachment Injection** | 🟡 Medium | Format validation exists but weak |
| **DMZ Spoofing** | ✅ Low | SHA256-hashed gateway tokens |
| **Session Hijacking** | ✅ Low | Stateless architecture |

---

## SECTION 4: ENHANCEMENT PROPOSALS

### 4.1 MCP Server Integration

**Current State:** No MCP (Model Context Protocol) integration

**Enhancement Option 1: Connectors as MCP Client** (Recommended)
- Connectors could use MCP to fetch tools/capabilities from AXE
- Enables dynamic capability discovery
- **Risk:** Added latency per message
- **Benefit:** Connectors auto-discover new features

```
Connector ──MCP Query──> AXE Core (MCP Server)
  │                           │
  │                    Returns: tools, prompts
  │                           │
  └──────────────────────────┘
```

**Enhancement Option 2: Connectors as MCP Server** (Less Likely)
- Expose connector capabilities as MCP tools to other BRAiN modules
- Example: Missions could directly invoke connector actions
- **Risk:** Tighter coupling
- **Benefit:** Mission system can send via multiple connectors

### 4.2 Event Emission & Contracts

**Current State:** Minimal event emission (only logging)

**Recommended Enhancement:** Structured event stream

```python
# Proposed event types
event_stream.publish({
    "event_type": "connector.message_received",
    "connector_id": "telegram",
    "user_id": "user_123",
    "timestamp": datetime.utcnow(),
    "metadata": {
        "message_id": "msg_abc",
        "session_id": "session_xyz",
        "trace_id": "trace_id_123"  # For distributed tracing
    }
})
```

**Benefits:**
- Audit trail for regulatory compliance
- Observability (Prometheus metrics)
- Integration with event-driven architectures (missions, workflows)
- Distributed tracing support

### 4.3 Persistent Session Context

**Current State:** Stateless (no session context preserved)

**Enhancement Proposal:** Optional session persistence
- Store conversation context in database/Redis
- Enable stateful conversations across connector restarts
- Example: "Remember that I told you my name is Alice" (even after disconnect)

**Implementation approach:**
- Add `session_id` correlation (already in metadata)
- Create optional `SessionStore` service (Redis backend)
- Lazy-load context if session_id present

### 4.4 Rate Limiting & Resource Protection

**Current State:** No rate limiting

**Recommended Enhancement:** Multi-level rate limiting
```python
# Rate limit options
limiter = RateLimiter(
    per_user_per_minute=20,        # Max 20 messages per user per minute
    per_connector_per_second=100,   # Max 100 messages per connector
    per_ip_per_minute=50,          # Max 50 from single IP
    daily_user_limit=1000           # Max 1000 per user per day
)
```

### 4.5 Payload Size Limits & Content Validation

**Current State:** Text max_length in schemas, but no attachment limits

**Recommended Enhancement:**
```python
class MessageSizePolicy(BaseModel):
    max_text_length: int = 10000          # 10KB text
    max_attachment_count: int = 5         # Max 5 files per message
    max_attachment_size: int = 50 * 1024 * 1024  # 50MB per file
    max_total_message_size: int = 100 * 1024 * 1024  # 100MB total
    allowed_mime_types: List[str] = [
        "image/jpeg", "image/png", "audio/mpeg",
        "application/pdf", "video/mp4"
    ]
```

### 4.6 Least Privilege Access Control

**Current State:** All connectors have same permissions

**Enhancement Proposal:** Per-connector capability allowlist
```python
# Configure which capabilities each connector can access
telegram_capabilities = {
    "send_text": True,
    "send_media": True,
    "request_location": False,        # Telegram has this, disable for privacy
    "call_external_apis": False,      # Sandboxed
    "access_user_memory": True,
    "trigger_missions": False         # Cannot directly trigger workflows
}
```

### 4.7 Connection to Governance & KARMA

**Current State:** Basic DMZ authentication, no governance integration

**Recommended Enhancement:** Governance audit trail
```python
# Proposed governance event emission
governance_event = {
    "event_type": "connector_message_processed",
    "connector_id": "telegram",
    "user_id": "user_123",
    "decision": "ALLOWED",  # or BLOCKED, QUARANTINED
    "policies_checked": [
        "rate_limit_check: PASS",
        "content_policy: PASS",
        "source_trust: PASS (DMZ)"
    ],
    "timestamp": datetime.utcnow()
}
```

---

## SECTION 5: PROPOSED MODULE STRUCTURE

**Current structure** (working well):
```
connectors/
├── __init__.py
├── base_connector.py      # Abstract base
├── router.py              # FastAPI endpoints
├── service.py             # Connector registry/management
├── schemas.py             # Pydantic models
├── telegram/              # Telegram adapter
├── whatsapp/              # WhatsApp adapter
├── voice/                 # Voice adapter (STT/TTS)
├── cli/                   # CLI adapter
└── tests/                 # Unit tests
```

**Enhancement proposal** (optional, for larger scope):
```
connectors/
├── __init__.py
├── core/
│   ├── base_connector.py        # ← Move here
│   ├── registry.py               # ← New: connector registry
│   └── message_contracts.py      # ← Extract message schemas
├── adapters/                     # ← Rename platform dirs
│   ├── telegram/
│   ├── whatsapp/
│   ├── voice/
│   └── cli/
├── drivers/                      # ← New: driver configs
│   ├── telegram_driver.yaml
│   ├── whatsapp_driver.yaml
│   └── voice_driver.yaml
├── schemas.py                    # Pydantic models
├── router.py                     # FastAPI endpoints
├── service.py                    # Service layer
├── governance.py                 # ← New: governance integration
├── events.py                     # ← New: event emission
├── rate_limiter.py              # ← New: rate limiting
├── session_store.py             # ← New: session persistence
├── tests/
│   ├── test_base_connector.py
│   ├── test_telegram_adapter.py
│   └── ...
└── docs/
    ├── ARCHITECTURE.md           # ← This document
    ├── DEVELOPER_GUIDE.md        # ← New: how to add connectors
    └── MCP_INTEGRATION.md        # ← New: MCP patterns
```

---

## SECTION 6: MVP ROADMAP

### Phase 1: Current State (✅ Already Implemented)
- [x] Base connector abstraction
- [x] Multiple adapters (Telegram, WhatsApp, Voice, CLI)
- [x] Router with authentication
- [x] DMZ gateway security
- [x] Basic schema validation
- [x] Unit tests

### Phase 2: Immediate Enhancements (Recommended - Low Effort)
- [ ] Add max_length constraints to message schemas
- [ ] Add rate limiting middleware
- [ ] Add structured event emission
- [ ] Add governance audit trail
- [ ] Documentation: Developer guide for new connectors

### Phase 3: Medium-term Enhancements (Medium Effort)
- [ ] Persistent session context (Redis backend)
- [ ] Per-connector capability allowlist
- [ ] Attachment validation strengthening
- [ ] Registry-based connector configuration (YAML/DB)
- [ ] MCP Server integration (connectors query AXE for tools)

### Phase 4: Advanced Features (High Effort, Future)
- [ ] Multi-connector workflows (route request to multiple platforms)
- [ ] Connector federation (multiple BRAiN instances)
- [ ] Plug-and-play driver loading (dynamic driver management)
- [ ] Advanced observability (Jaeger tracing, Prometheus metrics)

---

## SECTION 7: QUESTIONS FOR IMPLEMENTATION

1. **MCP Integration Priority:** Should connectors actively query AXE for capabilities, or is the current passive approach sufficient?

2. **Session Persistence:** Is conversation memory across connector restarts valuable for users, or is stateless better?

3. **Rate Limiting:** Should rate limits be global per user, per connector, or per (user, connector) pair?

4. **Governance Coupling:** How tightly should connectors be integrated with the governance/KARMA system?

5. **New Adapter Pattern:** What's the bar for adding new connectors (Slack, Discord, Email, etc.)?

---

## REFERENCES

- `AXE_CORE_API.md` - Connector authentication & message format
- `REPOSITORY_ANALYSE.md` - Existing architecture deep dive
- `BaseConnector` - Abstract interface for all adapters
- `ConnectorService` - Registry and lifecycle management

---

**Status:** Architecture document for review and enhancement planning
**Last Updated:** 2026-02-25
**Next Review:** After Phase 2 enhancements
