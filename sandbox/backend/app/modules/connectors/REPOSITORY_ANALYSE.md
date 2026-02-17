# Repository-Analyse: BRAIN Multi-Interface Connectors

**Datum:** 2026-02-01
**Branch:** `claude/brain-sprint-6a-analysis-JoTWa`
**Phase:** 0 - Repository-Analyse (vollstandig)

---

## 1. Bestehende Connector-Architektur

### 1.1 Legacy ConnectorHub (`modules/connector_hub/`)

**Status:** Aktiv, einfache Registry

| Datei | Zweck |
|-------|-------|
| `models.py` | ConnectorType (API/AXE/MCP/TCP/WS/CLI/INTERNAL_AGENT), ConnectorStatus, Connector dataclass |
| `services.py` | ConnectorRegistry mit `register()`, `get()`, `list_all()`, `get_gateway()` |

**Registrierte Connectors:**
1. `ollama_local` (LLM) - Auto-enabled wenn `OLLAMA_HOST` gesetzt
2. `openai_gateway` (LLM) - Disabled by default
3. `dummy_webhook` (WEBHOOK) - Test

**Wichtig:** `ConnectorType` hat bereits `CLI` als Typ definiert.

### 1.2 Modern BaseAPIClient (`app/modules/integrations/`)

**Status:** Aktiv, Enterprise-Grade HTTP Client

| Datei | Zweck |
|-------|-------|
| `base_client.py` | Abstract BaseAPIClient mit retry, circuit breaker, rate limiting |
| `auth.py` | Multi-Auth (API_KEY, OAUTH2, BASIC, BEARER, CUSTOM) |
| `retry.py` | Exponential backoff + jitter |
| `circuit_breaker.py` | CLOSED/OPEN/HALF_OPEN states |
| `rate_limit.py` | Token bucket algorithm |

**Bewertung:** Gut fur externe API-Aufrufe (Telegram API, WhatsApp API), aber NICHT als Basis fur Connector-Pattern geeignet (Connectors empfangen Nachrichten, BaseAPIClient sendet sie).

### 1.3 Bestehende Connector-Implementierungen

| Connector | Muster | Erbt von |
|-----------|--------|----------|
| `BuilderToolkitConnector` | Standalone | Nichts |
| `GitHubConnector` | Standalone mit `@with_retry` | Nichts |

**Ergebnis:** Es gibt KEIN einheitliches BaseConnector-Pattern. Jeder Connector ist standalone.

---

## 2. AXE Core API (Zentrale Schnittstelle)

### 2.1 Endpoints

| Method | Endpoint | Zweck |
|--------|----------|-------|
| GET | `/api/axe/info` | System-Info mit Governance |
| POST | `/api/axe/message` | Nachricht verarbeiten (Gateway oder LLM-Fallback) |
| GET | `/api/axe/config/{app_id}` | Widget-Konfiguration |
| WS | `/api/axe/ws/{session_id}` | Echtzeit-Kommunikation |
| POST | `/api/axe/events` | Telemetrie-Events (Batch) |
| GET | `/api/axe/events` | Events abfragen |

### 2.2 Sicherheits-Architektur (DMZ-Only)

**Trust Tier System:**
- `LOCAL` - localhost, immer erlaubt
- `DMZ` - Validierter Gateway mit HMAC Token
- `EXTERNAL` - Blockiert (403)

**DMZ Gateway Auth:**
```
Header: X-DMZ-Gateway-ID: telegram_gateway
Header: X-DMZ-Gateway-Token: sha256(gateway_id:shared_secret)
```

**Known DMZ Gateways:** `telegram_gateway`, `whatsapp_gateway`, `discord_gateway`, `email_gateway`

### 2.3 Message Routing

```
POST /api/axe/message
    |
    v
Trust Tier Validation
    |
    v
Try Gateway (ConnectorRegistry.get_gateway())
    |-- Gateway vorhanden? --> gateway.send_message()
    |-- Kein Gateway? --> LLM Fallback (simple_chat)
    v
Audit Event emittieren
    v
Response mit Governance-Metadata
```

### 2.4 Gateway Interface Contract

```python
class Gateway:
    name: str
    async def send_message(message: str, metadata: Dict) -> Dict[str, Any]:
        # Return: {reply: str} oder {message: str} oder {text: str}
```

---

## 3. Frontend AXE UI Contract

### 3.1 Architektur

- **Framework:** Next.js 14 + React 18 + TypeScript
- **State:** Zustand (axeStore, diffStore) mit localStorage Persistence
- **Kommunikation:** WebSocket-first, HTTP-Fallback
- **Telemetrie:** Batch-Upload alle 30s, max 100 Events

### 3.2 FloatingAxe Props (Embedding API)

```typescript
{
  appId: string;           // Required
  backendUrl: string;      // Required
  mode?: 'assistant' | 'builder' | 'support' | 'debug';
  theme?: 'dark' | 'light';
  position?: { bottom?, right?, top?, left? };
  userId?: string;
  sessionId?: string;
  extraContext?: Record<string, any>;
  onEvent?: (event: AxeEvent) => void;
}
```

### 3.3 WebSocket Protocol

**Client -> Server:** `{ type: 'chat'|'ping'|'diff_applied'|'diff_rejected'|'file_updated', payload }`
**Server -> Client:** `{ type: 'chat_response'|'pong'|'diff'|'file_update'|'error', payload }`

### 3.4 Message Types

```typescript
interface AxeMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: { model?: string; tokens?: number; duration_ms?: number };
}
```

---

## 4. Event/Message System

### 4.1 EventStream (`mission_control_core/core/event_stream.py`)

- Redis Stream + Pub/Sub basiert
- 50+ Event Types (TASK_*, MISSION_*, AGENT_*, SYSTEM_*, ETHICS_*)
- Consumer Groups fur exactly-once Processing
- Per-Agent Inbox: `brain:agent:{id}:inbox`

### 4.2 Mission System

```
Enqueue -> Redis ZSET (Priority) -> MissionWorker (Poll 2s) -> Execute -> EventStream
```

---

## 5. Architektur-Entscheidungen

### 5.1 BaseConnector Pattern (NEU zu erstellen)

Es existiert kein BaseConnector. Empfohlenes Design:

```python
class BaseConnector(ABC):
    """Basis fur alle BRAIN-Connectors."""

    connector_id: str
    connector_type: ConnectorType

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def send_to_user(self, user_id: str, message: ConnectorMessage) -> bool: ...

    async def send_to_brain(self, message: IncomingMessage) -> BrainResponse:
        """Alle Connectors senden uber AXE Core."""
        # POST /api/axe/message mit DMZ-Auth
        ...

    @abstractmethod
    async def health_check(self) -> ConnectorHealth: ...
```

### 5.2 Connector -> BRAIN Flow

```
User Input (Telegram/CLI/WhatsApp/Voice)
    |
    v
Connector.receive_message()
    |
    v
BaseConnector.send_to_brain()  -- HTTP POST /api/axe/message mit DMZ-Headers
    |
    v
AXE Core (Trust Tier Validation -> Gateway/LLM -> Response)
    |
    v
Connector.send_to_user()  -- Platform-spezifische Antwort
```

### 5.3 Modul-Struktur (Empfehlung)

```
backend/app/modules/connectors/
    __init__.py
    base_connector.py          # BaseConnector ABC
    schemas.py                 # Shared models
    service.py                 # ConnectorService (Registry + Lifecycle)
    router.py                  # /api/connectors/* REST endpoints
    EVENTS.md                  # Event Charter
    cli/
        connector.py           # CLIConnector
        shell.py               # Interactive Shell (rich)
    telegram/
        connector.py           # TelegramConnector
        bot.py                 # python-telegram-bot Integration
        handlers.py            # Message/Command Handlers
    whatsapp/
        connector.py           # WhatsAppConnector
        webhook.py             # Twilio Webhook Handler
    voice/
        service.py             # VoiceService (STT/TTS)
        stt_providers.py       # Whisper, Google, Azure
        tts_providers.py       # ElevenLabs, OpenAI TTS
```

---

## 6. Abhangigkeiten & Risiken

### 6.1 Externe Abhangigkeiten

| Connector | Dependencies | Risiko |
|-----------|-------------|--------|
| CLI | `rich`, `prompt_toolkit` | Niedrig |
| Telegram | `python-telegram-bot` | Niedrig (stabile API) |
| WhatsApp | `twilio` | Mittel (Kosten, Business API Zugang) |
| Voice STT | `openai` (Whisper API) | Mittel (Kosten) |
| Voice TTS | `elevenlabs` oder `openai` | Mittel (Kosten) |

### 6.2 Risiken

1. **DMZ Secret Management** - Aktuell hardcoded, muss in ENV
2. **Rate Limiting** - AXE hat noch kein Rate Limiting implementiert
3. **Session Management** - Telegram/WhatsApp brauchen persistente Sessions (aktuell nur in-memory)
4. **Voice Latency** - STT + LLM + TTS Chain kann >3s dauern

---

## 7. Implementierungs-Plan

### Phase 1: Foundation + CLI Connector
1. `BaseConnector` ABC erstellen
2. `ConnectorMessage` / `IncomingMessage` / `BrainResponse` Schemas
3. `ConnectorService` (Registry, Lifecycle, Health)
4. `CLIConnector` mit `rich` Terminal UI
5. Tests (30+)

### Phase 2: AXE Core API Documentation
1. OpenAPI Schema validieren
2. Connector-spezifische Auth-Endpoints dokumentieren
3. WebSocket Protocol dokumentieren

### Phase 3: Telegram Connector
1. `TelegramConnector` mit python-telegram-bot
2. Webhook + Polling Mode
3. /start, /help, /status Commands
4. Voice Message -> STT Pipeline
5. File Upload Handling
6. Approval Flow (Inline Keyboards)
7. Tests (30+)

### Phase 4: Voice Services
1. `VoiceService` mit Provider-Abstraktion
2. STT: Whisper API, Google Speech (optional)
3. TTS: ElevenLabs, OpenAI TTS
4. Audio Format Conversion (ffmpeg)
5. Streaming Support
6. Tests (20+)

### Phase 5: WhatsApp Connector
1. `WhatsAppConnector` mit Twilio
2. Webhook Handler
3. Media Message Support
4. Template Messages
5. Tests (20+)

---

## 8. MoltBot Analyse

**Referenz:** https://molt.bot - Multi-Channel AI Bot Platform

**Relevante Features fur BRAIN:**
- Multi-Channel (Telegram, WhatsApp, Web Widget) - genau unser Ziel
- Conversation Context uber Channels hinweg
- Rich Media Support (Bilder, Dokumente, Audio)
- Approval Workflows

**Unterschied zu BRAIN:**
- MoltBot ist SaaS, BRAIN ist Self-Hosted
- BRAIN hat KARMA Scoring, Constitution, Policy Engine
- BRAIN hat DMZ-Security Architektur

---

## Fazit

Die Codebasis ist bereit fur Multi-Interface Connectors. Die AXE Core API bietet bereits:
- DMZ-Gateway Authentifizierung (telegram_gateway ist vorregistriert)
- Gateway Interface Contract (`send_message()`)
- WebSocket Support
- Telemetrie Pipeline
- Audit Trail

Es fehlt:
- **BaseConnector ABC** (muss erstellt werden)
- **Connector Lifecycle Management** (start/stop/health)
- **Session Persistence** (fur Telegram/WhatsApp)
- **Voice Pipeline** (STT/TTS)

**Empfehlung:** Phase 1 (BaseConnector + CLI) kann sofort starten. Die AXE Core API muss nicht modifiziert werden - Connectors nutzen sie als DMZ-Gateways.
