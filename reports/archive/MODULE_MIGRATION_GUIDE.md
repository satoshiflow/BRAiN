# MODULE_MIGRATION_GUIDE.md

**Version:** 1.0.0
**Status:** Normative (Binding)
**Last Updated:** 2025-12-28
**Owner:** BRAiN Core Team

---

## 1. Zweck & Geltungsbereich

### 1.1 Zweck

Dieses Dokument definiert **das einzige zulässige Verfahren** zur Migration bestehender BRAiN-Module auf das zentrale EventStream-System gemäß ADR-001 und BRAiN Event Charter v1.0.

### 1.2 Geltungsbereich

Dieses Dokument gilt für:
- Alle Module in `backend/modules/*`
- Alle Module in `backend/app/modules/*`
- Alle custom agents in `backend/brain/agents/*`
- Jedes Modul, das Zustandsänderungen publik macht oder auf Events reagiert

### 1.3 Normative Referenzen

- **ADR-001:** EventStream als Kerninfrastruktur (required mode)
- **BRAiN Event Charter v1.0:** Event Envelope, Idempotency, Error Handling
- **EVENT_SYSTEM.md:** Technische Referenz (`backend/mission_control_core/core/EVENT_SYSTEM.md`)

### 1.4 Feature-Freeze

❌ Keine neuen Features während der Migration
❌ Keine Architektur-Experimente
❌ Keine „Verbesserungen" außerhalb des Scopes
✅ Nur charter-konforme Migration bestehender Funktionalität

---

## 2. Vorbedingungen (HARD GATE)

Eine Migration darf **NUR** begonnen werden, wenn alle folgenden Bedingungen erfüllt sind:

### 2.1 Systemvoraussetzungen

- [ ] **EventStream läuft im `required` Mode**
  ```bash
  # Verify in .env or environment
  BRAIN_EVENTSTREAM_MODE=required  # MUST be set (default)
  ```

- [ ] **Alembic Migration `002_event_dedup_stream_message_id` angewendet**
  ```bash
  cd backend
  alembic current
  # Expected output: 002 (head)
  ```

- [ ] **PostgreSQL `processed_events` Tabelle existiert**
  ```bash
  psql -U brain -d brain -c "\d processed_events"
  # Expected: Table structure with stream_message_id unique constraint
  ```

- [ ] **Redis verfügbar und EventStream initialisiert**
  ```bash
  curl http://localhost:8000/api/health
  # Expected: {"status": "healthy", "event_stream": true}
  ```

### 2.2 Modul-Identifikation

- [ ] **Modul-Name klar definiert** (z.B. `course_factory`)
- [ ] **Modul-Pfad dokumentiert** (z.B. `backend/app/modules/course_factory`)
- [ ] **Modul-Owner festgelegt** (Person/Team verantwortlich)
- [ ] **Modul-Abhängigkeiten bekannt** (externe APIs, andere Module)

### 2.3 Go/No-Go Entscheidung

**GO**, wenn:
- Alle obigen Checkboxen ✅
- Modul produziert relevante Business Events
- Modul ist aktiv in Nutzung

**NO-GO**, wenn:
- Modul ist deprecated/unused
- EventStream nicht im `required` Mode
- Migration 002 nicht angewendet

---

## 3. Modul-Analyse (Phase 0 – Pflicht)

Phase 0 ist **Informationsbeschaffung ohne Code-Änderungen**.

### 3.1 Fachliche Analyse

**Fragen zu beantworten:**

1. **Was macht das Modul fachlich?**
   - Einzeiler-Beschreibung (z.B. „Generiert KI-Kurse aus Themen")
   - Hauptverantwortung (z.B. „Course Factory erstellt Kurse")

2. **Welche Zustandsänderungen sind relevant?**
   - Wann ändert sich etwas, das andere Module interessiert?
   - Beispiele: Kurs erstellt, Zahlung abgeschlossen, Robot Position geändert

3. **Welche externen Abhängigkeiten?**
   - Andere Module (synchron aufgerufen)?
   - Externe APIs (z.B. Stripe, Ollama)?
   - Datenbank-Tabellen (gelesen/geschrieben)?

### 3.2 Code-Analyse

**Schritt-für-Schritt:**

```bash
# 1. Service-Dateien identifizieren
find backend/app/modules/MY_MODULE -name "service.py" -o -name "router.py"

# 2. Zustandsänderungen finden
grep -n "def create\|def update\|def complete\|def cancel" backend/app/modules/MY_MODULE/service.py

# 3. Externe Aufrufe identifizieren
grep -n "await.*\." backend/app/modules/MY_MODULE/service.py | grep -v "self\."
```

### 3.3 Output: Event Liste (Planung)

**Format:**
```markdown
## Geplante Events für Modul: MY_MODULE

1. **Event:** `my_module.resource.created`
   - **Wann:** Nach erfolgreicher Ressourcen-Erstellung
   - **Payload:** resource_id, resource_name, creator_id
   - **Consumers:** (TBD, z.B. notification_service)

2. **Event:** `my_module.resource.completed`
   - **Wann:** Ressource erreicht finalen Zustand
   - **Payload:** resource_id, result, duration
   - **Consumers:** (TBD, z.B. metrics_service)

3. **Event:** `my_module.resource.failed`
   - **Wann:** Ressourcen-Erstellung schlägt fehl
   - **Payload:** resource_id, error_message, retry_count
   - **Consumers:** (TBD, z.B. alerting_service)
```

**Keine Implementierung in Phase 0** – nur Planung!

---

## 4. Event Design (Phase 1)

Phase 1 ist **Event-Spezifikation ohne Implementierung**.

### 4.1 Event Type Naming

**Regel:** `<domain>.<resource>.<action>`

- **domain:** Modul-Name (singular, lowercase, z.B. `course`, `payment`, `robot`)
- **resource:** Business Object (singular, z.B. `generation`, `transaction`, `position`)
- **action:** Past tense verb (z.B. `created`, `completed`, `failed`, `cancelled`)

**Beispiele:**

✅ RICHTIG:
- `course.generation.started`
- `payment.transaction.completed`
- `robot.position.updated`

❌ FALSCH:
- `CourseGenerated` (nicht PascalCase)
- `course_created` (nicht snake_case, kein Ressourcen-Name)
- `course.create` (nicht past tense)

### 4.2 Wann Events publishen

**Regel:** Events werden **nach erfolgreicher Zustandsänderung** publiziert.

```python
# ✅ RICHTIG
async def create_resource(self, data: dict):
    # 1. Zustandsänderung durchführen
    resource = await self.db.create(data)
    await self.db.commit()  # Transaction abschließen

    # 2. Event publishen (NACH commit)
    event = Event(
        id=str(uuid.uuid4()),
        type=EventType.MY_MODULE_RESOURCE_CREATED,
        source="my_module",
        target=None,
        payload={"resource_id": resource.id},
        timestamp=datetime.utcnow(),
        meta={
            "schema_version": 1,
            "producer": "my_module_service",
            "source_module": "my_module"
        }
    )
    await self.event_stream.publish_event(event)

    return resource

# ❌ FALSCH (Event vor commit)
async def create_resource(self, data: dict):
    resource = await self.db.create(data)
    await self.event_stream.publish_event(event)  # FALSCH: vor commit!
    await self.db.commit()
```

**Lifecycle Events:**
- **Start:** `<resource>.started` (optional, bei langen Operationen)
- **Success:** `<resource>.completed` (immer)
- **Failure:** `<resource>.failed` (immer)

### 4.3 Event Envelope Pflichtfelder

**Gemäß Charter v1.0:**

```python
event = Event(
    # PFLICHT (required)
    id=str(uuid.uuid4()),                 # UUID v4 (SECONDARY dedup key)
    type=EventType.MY_EVENT,              # EventType enum
    source="my_producer",                 # Producer identifier
    target=None,                          # None = broadcast, str = specific agent
    payload={...},                        # Event-specific data (siehe 4.4)
    timestamp=datetime.utcnow(),          # UTC timestamp

    # PFLICHT (meta)
    meta={
        "schema_version": 1,              # Integer (aktuell: 1)
        "producer": "my_service",         # Service/Producer Name
        "source_module": "my_module"      # BRAiN Modul-Name
    },

    # OPTIONAL
    mission_id=None,                      # Nur wenn Teil einer Mission
    task_id=None,                         # Nur wenn Teil eines Tasks
    tenant_id=None,                       # Nur bei Multi-Tenancy
    actor_id=None,                        # Nur wenn User-Action
    correlation_id=None                   # Request-Tracing ID
)
```

### 4.4 Payload Design

**Was gehört in `payload`:**

✅ **Business-relevante Daten:**
- IDs (resource_id, user_id, NOT internal DB IDs)
- Status (string, z.B. "active", "completed")
- Metadata (created_at, updated_at)
- Ergebnisse (result, output_url)

❌ **Nicht in payload:**
- PII (Personally Identifiable Information) – nur IDs verwenden
- Provider-IDs (z.B. Stripe Customer ID) – nur in internen Logs
- Vollständige Objekte – nur referenzieren
- Sensible Daten (Passwörter, Tokens, API Keys)

**Beispiel:**

```python
# ✅ RICHTIG
payload = {
    "course_id": "course_abc123",
    "course_title": "Python Basics",  # OK: public data
    "status": "published",
    "lesson_count": 10,
    "created_by": "user_xyz456"  # User ID, NOT email/name
}

# ❌ FALSCH
payload = {
    "course_id": 42,  # FALSCH: internal DB ID
    "user_email": "user@example.com",  # FALSCH: PII
    "stripe_customer_id": "cus_abc",  # FALSCH: Provider ID
    "full_course_object": {...}  # FALSCH: zu groß
}
```

### 4.5 EventType Registration

**Schritt 1:** Event Type zum Enum hinzufügen

```python
# backend/mission_control_core/core/event_stream.py

class EventType(str, Enum):
    # ... existing types ...

    # My Module Events
    MY_MODULE_RESOURCE_CREATED = "my_module.resource.created"
    MY_MODULE_RESOURCE_COMPLETED = "my_module.resource.completed"
    MY_MODULE_RESOURCE_FAILED = "my_module.resource.failed"
```

**Schritt 2:** Event Type dokumentieren

```markdown
# backend/app/modules/my_module/EVENTS.md

## Events Published by my_module

### 1. my_module.resource.created

**When:** Resource successfully created in database
**Payload:**
- `resource_id` (str): Unique resource identifier
- `resource_name` (str): Human-readable name
- `creator_id` (str): User who created resource

**Consumers:**
- `notification_service`: Send creation notification
- `metrics_service`: Track resource creation rate
```

---

## 5. Producer-Implementierung (Phase 2)

Phase 2 ist **Producer-Code schreiben**.

### 5.1 EventStream Dependency Injection

**In service.py:**

```python
# backend/app/modules/my_module/service.py

from backend.mission_control_core.core.event_stream import EventStream, Event, EventType
from datetime import datetime
import uuid

class MyModuleService:
    def __init__(self, event_stream: EventStream):
        self.event_stream = event_stream

    async def create_resource(self, data: dict) -> dict:
        # Business logic
        resource = await self._create_in_db(data)

        # Publish event (AFTER successful DB operation)
        await self._publish_created_event(resource)

        return resource

    async def _publish_created_event(self, resource: dict):
        """Publish resource.created event (Charter compliant)"""
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.MY_MODULE_RESOURCE_CREATED,
            source="my_module_service",
            target=None,  # Broadcast
            payload={
                "resource_id": resource["id"],
                "resource_name": resource["name"],
                "creator_id": resource["creator_id"]
            },
            timestamp=datetime.utcnow(),
            meta={
                "schema_version": 1,
                "producer": "my_module_service",
                "source_module": "my_module"
            }
        )

        try:
            await self.event_stream.publish_event(event)
        except Exception as e:
            # Event publishing failure MUST NOT fail business operation
            logger.error(f"Failed to publish event {event.id}: {e}")
            # DO NOT raise – business operation succeeded
```

### 5.2 EventStream Initialisierung in main.py

**EventStream wird zentral initialisiert:**

```python
# backend/main.py (bereits vorhanden)

# EventStream wird beim Startup initialisiert
@app.on_event("startup")
async def startup_event():
    event_stream = EventStream(redis_url=settings.REDIS_URL)
    await event_stream.initialize()
    await event_stream.start()
    app.state.event_stream = event_stream

# Module greifen auf app.state.event_stream zu
```

**In router.py (Dependency Injection):**

```python
# backend/app/modules/my_module/router.py

from fastapi import APIRouter, Depends, Request

router = APIRouter(prefix="/api/my-module", tags=["my-module"])

def get_event_stream(request: Request):
    return request.app.state.event_stream

@router.post("/resources")
async def create_resource(
    data: dict,
    event_stream = Depends(get_event_stream)
):
    service = MyModuleService(event_stream)
    result = await service.create_resource(data)
    return result
```

### 5.3 Fehlerbehandlung beim Publish

**Regel:** Event-Fehler dürfen Business-Operation NICHT fehlschlagen lassen.

```python
async def _publish_event_safe(self, event: Event):
    """Publish event with error handling (non-blocking)"""
    try:
        await self.event_stream.publish_event(event)
        logger.info(f"Event published: {event.type.value} ({event.id})")
    except Exception as e:
        # Log error, but DO NOT raise
        logger.error(
            f"Event publishing failed: {event.type.value} ({event.id})",
            exc_info=True,
            extra={"event_id": event.id, "event_type": event.type.value}
        )
        # Optionally: increment metrics counter for failed publishes
        # metrics.increment("eventstream.publish.failed")
```

### 5.4 event.id ist sekundär

**Wichtig:** `event.id` (UUID) ist **NICHT** der Primary Dedup Key.

```python
# ✅ RICHTIG: event.id generieren (für Audit/Trace)
event_id = str(uuid.uuid4())

event = Event(
    id=event_id,  # SECONDARY dedup key (audit only)
    type=EventType.MY_EVENT,
    # ...
)

# ❌ FALSCH: event.id als Dedup-Schlüssel verwenden
# Consumer MUST use stream_message_id, NOT event.id!
```

**Warum?**
Bei Retry wird `event.id` neu generiert → nicht idempotent.
`stream_message_id` (Redis Stream ID) bleibt stabil → idempotent.

---

## 6. Consumer-Implementierung (Phase 3)

Phase 3 ist **Consumer-Code schreiben** (falls erforderlich).

### 6.1 Wann braucht ein Modul einen Consumer?

**Consumer erforderlich, wenn:**
- Modul reagiert auf Events anderer Module
- Modul führt asynchrone Nachbearbeitung aus (z.B. Benachrichtigungen)
- Modul synchronisiert externen Zustand (z.B. Cache-Invalidierung)

**Consumer NICHT erforderlich, wenn:**
- Modul publiziert nur Events (reine Producer)
- Modul arbeitet rein synchron (Request/Response)

### 6.2 EventConsumer Nutzung

**Zentrale Infrastruktur:**

```python
# backend/app/modules/my_module/consumer.py

from backend.mission_control_core.core.event_stream import (
    EventConsumer, Event, EventType, EventStream
)
from typing import Callable
import logging

logger = logging.getLogger(__name__)

class MyModuleConsumer:
    """Consumer for my_module events (Charter compliant)"""

    def __init__(
        self,
        event_stream: EventStream,
        db_session_factory: Callable
    ):
        self.consumer = EventConsumer(
            subscriber_name="my_module_consumer",  # UNIQUE name
            event_stream=event_stream,
            db_session_factory=db_session_factory,
            stream_name="brain:events:stream",
            consumer_group="group_my_module",
            batch_size=10,
            block_ms=5000
        )

        # Register handlers
        self.consumer.register_handler(
            EventType.PAYMENT_COMPLETED,
            self.handle_payment_completed
        )
        self.consumer.register_handler(
            EventType.COURSE_GENERATION_COMPLETED,
            self.handle_course_completed
        )

    async def start(self):
        """Start consuming events"""
        await self.consumer.start()

    async def stop(self):
        """Stop consuming events gracefully"""
        await self.consumer.stop()

    async def handle_payment_completed(self, event: Event):
        """
        Handle payment.completed event (IDEMPOTENT)

        Idempotency guaranteed by EventConsumer (stream_message_id dedup)
        """
        payload = event.payload
        course_id = payload.get("course_id")
        user_id = payload.get("user_id")

        logger.info(f"Granting access: user={user_id}, course={course_id}")

        # Business logic (safe to run multiple times)
        await self._grant_course_access(user_id, course_id)

    async def handle_course_completed(self, event: Event):
        """Handle course.generation.completed event"""
        course_id = event.payload.get("course_id")
        logger.info(f"Course {course_id} completed, sending notifications")

        await self._send_course_ready_notification(course_id)

    async def _grant_course_access(self, user_id: str, course_id: str):
        """Idempotent access grant (INSERT ... ON CONFLICT DO NOTHING)"""
        # Implementation: Idempotent DB operation
        pass

    async def _send_course_ready_notification(self, course_id: str):
        """Send notification (idempotent via external_id)"""
        # Implementation: Idempotent notification (check if already sent)
        pass
```

### 6.3 Idempotency: stream_message_id ist PRIMARY

**Automatisch durch EventConsumer:**

```python
# EventConsumer macht AUTOMATISCH:

# 1. Check dedup (PRIMARY key)
query = text("""
    SELECT 1 FROM processed_events
    WHERE subscriber_name = :subscriber
    AND stream_message_id = :stream_msg_id  -- PRIMARY!
    LIMIT 1
""")

# 2. Wenn Duplikat → SKIP (keine Wirkung)
if is_duplicate:
    logger.debug(f"Skipping duplicate: {stream_message_id}")
    await ack_message()
    return

# 3. Handler ausführen
await handler(event)

# 4. Als processed markieren
INSERT INTO processed_events (
    subscriber_name,
    stream_message_id,  -- PRIMARY
    event_id            -- SECONDARY (audit)
)

# 5. ACK message
await ack_message()
```

**Du musst nichts tun** – EventConsumer garantiert Idempotency!

### 6.4 Transient vs. Permanent Errors

**Permanent Errors (ACK + Log):**
- `ValueError`: Validation fehlgeschlagen
- `TypeError`: Falscher Datentyp
- `KeyError`: Pflichtfeld fehlt
- `AttributeError`: Objekt-Zugriff ungültig

**Transient Errors (NO ACK → Retry):**
- `ConnectionError`: DB/API nicht erreichbar
- `TimeoutError`: Request Timeout
- `asyncio.TimeoutError`: Async Timeout

**EventConsumer entscheidet automatisch:**

```python
# backend/mission_control_core/core/event_stream.py (EventConsumer)

def _is_permanent_error(self, error: Exception) -> bool:
    permanent_types = (KeyError, TypeError, ValueError, AttributeError)
    transient_types = (ConnectionError, TimeoutError, asyncio.TimeoutError)

    if isinstance(error, permanent_types):
        return True  # → ACK (nicht wiederholen)
    if isinstance(error, transient_types):
        return False  # → NO ACK (wiederholen)

    return False  # Default: transient (sicherer)
```

**In deinem Handler:** Wirf einfach die Exception – EventConsumer handled sie.

```python
async def handle_event(self, event: Event):
    payload = event.payload

    # ValueError → permanent → ACK
    if "required_field" not in payload:
        raise ValueError("required_field missing")  # ACK!

    # ConnectionError → transient → NO ACK (retry)
    try:
        await external_api.call()
    except ConnectionError:
        raise  # NO ACK → Redis redelivers
```

---

## 7. Tests (Phase 4 – Pflicht)

Phase 4 ist **Tests schreiben** – keine optionalen Tests.

### 7.1 Minimal erforderliche Tests (4 Tests)

**Jede Migration MUSS mindestens diese 4 Tests haben:**

1. ✅ **Event wird publiziert**
2. ✅ **Consumer verarbeitet Event**
3. ✅ **Replay derselben Message → keine Doppelwirkung**
4. ✅ **Fehlerfall korrekt behandelt**

### 7.2 Test 1: Event wird publiziert

```python
# backend/tests/test_my_module_events.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.app.modules.my_module.service import MyModuleService
from backend.mission_control_core.core.event_stream import EventType

@pytest.mark.asyncio
async def test_create_resource_publishes_event():
    """Test 1: Event wird publiziert"""
    # Arrange
    event_stream_mock = AsyncMock()
    service = MyModuleService(event_stream=event_stream_mock)

    # Act
    await service.create_resource({"name": "Test Resource"})

    # Assert
    event_stream_mock.publish_event.assert_called_once()
    call_args = event_stream_mock.publish_event.call_args[0][0]

    assert call_args.type == EventType.MY_MODULE_RESOURCE_CREATED
    assert call_args.payload["resource_name"] == "Test Resource"
    assert call_args.meta["schema_version"] == 1
    assert call_args.meta["producer"] == "my_module_service"
    assert call_args.meta["source_module"] == "my_module"
```

### 7.3 Test 2: Consumer verarbeitet Event

```python
@pytest.mark.asyncio
async def test_consumer_processes_event():
    """Test 2: Consumer verarbeitet Event"""
    # Arrange
    event_stream = EventStream(redis_url="redis://localhost:6379")
    await event_stream.initialize()

    consumer = MyModuleConsumer(
        event_stream=event_stream,
        db_session_factory=get_test_db_session
    )

    handler_mock = AsyncMock()
    consumer.consumer.register_handler(EventType.MY_EVENT, handler_mock)

    # Act
    await consumer.start()

    # Publish test event
    event = Event(
        id=str(uuid.uuid4()),
        type=EventType.MY_EVENT,
        source="test",
        target=None,
        payload={"test": "data"},
        timestamp=datetime.utcnow(),
        meta={"schema_version": 1, "producer": "test", "source_module": "test"}
    )
    await event_stream.publish_event(event)

    # Wait for processing
    await asyncio.sleep(1)

    # Assert
    handler_mock.assert_called_once()
    call_args = handler_mock.call_args[0][0]
    assert call_args.type == EventType.MY_EVENT
    assert call_args.payload["test"] == "data"

    # Cleanup
    await consumer.stop()
```

### 7.4 Test 3: Replay → keine Doppelwirkung

```python
@pytest.mark.asyncio
async def test_replay_same_message_is_idempotent():
    """Test 3: Replay derselben Message → keine Doppelwirkung"""
    # Arrange
    event_stream = EventStream(redis_url="redis://localhost:6379")
    await event_stream.initialize()

    execution_counter = {"count": 0}

    async def counting_handler(event: Event):
        execution_counter["count"] += 1

    consumer = EventConsumer(
        subscriber_name="test_idempotency_consumer",
        event_stream=event_stream,
        db_session_factory=get_test_db_session,
        stream_name="brain:events:stream"
    )
    consumer.register_handler(EventType.MY_EVENT, counting_handler)

    # Act: Publish event twice (simulating replay)
    event = Event(
        id=str(uuid.uuid4()),
        type=EventType.MY_EVENT,
        source="test",
        target=None,
        payload={"test": "idempotency"},
        timestamp=datetime.utcnow(),
        meta={"schema_version": 1, "producer": "test", "source_module": "test"}
    )

    await event_stream.publish_event(event)
    await consumer.start()
    await asyncio.sleep(1)

    # Simulate replay (same stream_message_id)
    # In real Redis Stream, this would be handled by consumer group
    # For test: manually re-read same message
    # (Implementation depends on test harness)

    await asyncio.sleep(1)

    # Assert: Handler only executed ONCE
    assert execution_counter["count"] == 1  # NOT 2!

    # Cleanup
    await consumer.stop()
```

### 7.5 Test 4: Fehlerfall korrekt behandelt

```python
@pytest.mark.asyncio
async def test_permanent_error_acks_message():
    """Test 4: Permanent Error → ACK (kein Retry)"""
    # Arrange
    event_stream = EventStream(redis_url="redis://localhost:6379")
    await event_stream.initialize()

    async def failing_handler(event: Event):
        raise ValueError("Permanent validation error")  # Permanent!

    consumer = EventConsumer(
        subscriber_name="test_error_consumer",
        event_stream=event_stream,
        db_session_factory=get_test_db_session
    )
    consumer.register_handler(EventType.MY_EVENT, failing_handler)

    # Mock _ack_message to verify it's called
    consumer._ack_message = AsyncMock()

    # Act
    await consumer.start()

    event = Event(
        id=str(uuid.uuid4()),
        type=EventType.MY_EVENT,
        source="test",
        target=None,
        payload={"test": "error"},
        timestamp=datetime.utcnow(),
        meta={"schema_version": 1, "producer": "test", "source_module": "test"}
    )
    await event_stream.publish_event(event)

    await asyncio.sleep(1)

    # Assert: ACK was called (permanent error)
    assert consumer._ack_message.called

    # Cleanup
    await consumer.stop()

@pytest.mark.asyncio
async def test_transient_error_no_ack():
    """Test 4b: Transient Error → NO ACK (Retry)"""
    # Similar test, but raise ConnectionError → verify NO ACK
    async def failing_handler(event: Event):
        raise ConnectionError("Transient connection error")  # Transient!

    # ... setup consumer ...
    consumer._ack_message = AsyncMock()

    # ... publish event ...

    # Assert: ACK was NOT called (transient error → retry)
    assert not consumer._ack_message.called
```

### 7.6 Test Ausführung

```bash
# Alle Modul-Tests ausführen
pytest backend/tests/test_my_module_events.py -v

# Erwartetes Ergebnis: 4 passed (minimum)
```

**Alle 4 Tests MÜSSEN grün sein** – sonst ist Migration nicht abgeschlossen.

---

## 8. Abschalten alter Pfade (Phase 5)

Phase 5 ist **Legacy-Code entfernen**.

### 8.1 Synchrone Modul-Aufrufe entfernen

**Vor Migration (synchroner Aufruf):**

```python
# backend/app/modules/payment/service.py (BEFORE)

from backend.app.modules.course_access.service import CourseAccessService

async def process_payment(self, payment_id: str):
    # ... payment logic ...

    # ❌ FALSCH: Direkter synchroner Aufruf
    course_access_service = CourseAccessService()
    await course_access_service.grant_access(user_id, course_id)

    return payment
```

**Nach Migration (Event):**

```python
# backend/app/modules/payment/service.py (AFTER)

async def process_payment(self, payment_id: str):
    # ... payment logic ...

    # ✅ RICHTIG: Event publishen
    event = Event(
        id=str(uuid.uuid4()),
        type=EventType.PAYMENT_COMPLETED,
        source="payment_service",
        target=None,
        payload={
            "payment_id": payment_id,
            "user_id": user_id,
            "course_id": course_id
        },
        timestamp=datetime.utcnow(),
        meta={
            "schema_version": 1,
            "producer": "payment_service",
            "source_module": "payment"
        }
    )
    await self.event_stream.publish_event(event)

    return payment

# course_access_service reagiert auf PAYMENT_COMPLETED Event (Consumer)
```

### 8.2 Legacy-Code löschen

**Nicht erlaubt:**

❌ Legacy-Code auskommentieren
❌ Legacy-Code mit `# TODO: remove` markieren
❌ Parallele Codepfade (legacy + event)

**Erlaubt:**

✅ Legacy-Code vollständig löschen
✅ Git History für Referenz nutzen

**Beispiel:**

```python
# ❌ FALSCH
async def create_resource(self, data: dict):
    # Old way (TODO: remove after migration)
    # await self._sync_create(data)

    # New way
    await self._create_with_event(data)

# ✅ RICHTIG
async def create_resource(self, data: dict):
    # Event-based implementation
    resource = await self._create_in_db(data)
    await self._publish_created_event(resource)
    return resource
```

### 8.3 Import-Statements bereinigen

```python
# ❌ FALSCH (alte Imports bleiben)
from backend.app.modules.other_module.service import OtherService  # unused
from backend.mission_control_core.core.event_stream import EventStream

# ✅ RICHTIG (nur benötigte Imports)
from backend.mission_control_core.core.event_stream import (
    EventStream, Event, EventType
)
```

### 8.4 Keine Feature-Flags für Legacy

**Nicht erlaubt:**

```python
# ❌ FALSCH
if os.getenv("USE_EVENTS") == "true":
    await self._create_with_event(data)
else:
    await self._create_legacy(data)  # NICHT erlaubt!
```

**Warum?**
EventStream ist gemäß ADR-001 **required** – es gibt keinen Legacy-Fallback.

---

## 9. Akzeptanzkriterien (Go/No-Go)

Ein Modul gilt **NUR DANN** als migriert, wenn **ALLE** folgenden Kriterien erfüllt sind:

### 9.1 Funktionale Kriterien

- [ ] **Events werden publiziert**
  - Alle relevanten Zustandsänderungen emittieren Events
  - Events enthalten korrekten EventType
  - Events enthalten vollständige meta.* Felder

- [ ] **Consumer aktiv (falls erforderlich)**
  - EventConsumer läuft und verarbeitet Events
  - Handler registriert für alle relevanten EventTypes
  - Consumer in Startup-Lifecycle integriert

- [ ] **Idempotency greift**
  - `processed_events` Tabelle wird befüllt
  - Replay derselben Message → keine Doppelwirkung
  - PRIMARY dedup key: `stream_message_id`

### 9.2 Test-Kriterien

- [ ] **Tests grün sind**
  - Test 1: Event wird publiziert ✅
  - Test 2: Consumer verarbeitet Event ✅
  - Test 3: Replay → keine Doppelwirkung ✅
  - Test 4: Fehlerfall korrekt behandelt ✅

- [ ] **Keine Test-Failures in CI**
  ```bash
  pytest backend/tests/test_my_module_events.py -v
  # Expected: 4 passed, 0 failed
  ```

### 9.3 Dokumentations-Kriterien

- [ ] **README des Moduls aktualisiert**
  - Events Published Sektion vorhanden
  - Events Consumed Sektion vorhanden (falls Consumer)
  - Beispiele für Event-Nutzung

- [ ] **EVENTS.md erstellt**
  - Liste aller Events (Type, Payload, Consumers)
  - Migration-Status dokumentiert

### 9.4 Code-Quality Kriterien

- [ ] **Legacy-Code entfernt**
  - Keine synchronen Modul-Aufrufe mehr
  - Keine auskommentierten Codepfade
  - Keine Feature-Flags für Legacy

- [ ] **Type Hints vollständig**
  - Alle Event-Handler haben Type Hints
  - Event Payload dokumentiert (TypedDict oder Pydantic)

### 9.5 Explizite No-Go Kriterien

**Migration ist NICHT abgeschlossen, wenn:**

❌ Events ohne `meta.*` Felder publiziert werden
❌ Consumer verwendet `event.id` als PRIMARY dedup key
❌ Legacy synchrone Aufrufe existieren noch
❌ Weniger als 4 Tests vorhanden
❌ Tests nicht grün
❌ README nicht aktualisiert

**Bei No-Go:** Migration zurückrollen, Fehler beheben, neu starten.

---

## 10. Modul-README Template (verbindlich)

Jedes migrierte Modul **MUSS** folgendes README-Format haben:

```markdown
# Module: MY_MODULE

**Version:** 1.0.0 (EventStream Migration)
**Owner:** Team/Person
**Last Updated:** YYYY-MM-DD

---

## Zweck

Einzeiler-Beschreibung des Moduls.

Beispiel: "Generiert KI-Kurse aus Themen mittels LLM-Integration."

---

## Events Published

Liste aller Events, die dieses Modul publiziert:

### 1. `my_module.resource.created`

**EventType:** `MY_MODULE_RESOURCE_CREATED`

**Wann:** Resource erfolgreich in Datenbank erstellt

**Payload:**
```json
{
  "resource_id": "string",
  "resource_name": "string",
  "creator_id": "string"
}
```

**Consumers:**
- `notification_service`: Benachrichtigung senden
- `metrics_service`: Erstellungs-Metrik erfassen

**Meta:**
```json
{
  "schema_version": 1,
  "producer": "my_module_service",
  "source_module": "my_module"
}
```

---

### 2. `my_module.resource.completed`

**EventType:** `MY_MODULE_RESOURCE_COMPLETED`

**Wann:** Resource erreicht finalen Zustand

**Payload:**
```json
{
  "resource_id": "string",
  "result": "object",
  "duration": "number (seconds)"
}
```

**Consumers:**
- `analytics_service`: Erfolgs-Metrik erfassen

---

## Events Consumed

Liste aller Events, auf die dieses Modul reagiert (falls Consumer):

### 1. `payment.transaction.completed`

**EventType:** `PAYMENT_COMPLETED`

**Handler:** `handle_payment_completed` (in `consumer.py`)

**Aktion:** Gewährt Kurs-Zugang für User

**Idempotent:** Ja (via `stream_message_id` dedup)

---

## Dependencies

- **EventStream:** Required (`backend.mission_control_core.core.event_stream`)
- **Database:** PostgreSQL (`processed_events` table for consumer dedup)
- **Redis:** EventStream Pub/Sub + Streams
- **External APIs:** Ollama (LLM generation)

---

## Betriebs-Hinweise

### Startup

Consumer wird automatisch gestartet in `main.py`:

```python
@app.on_event("startup")
async def startup_event():
    my_module_consumer = MyModuleConsumer(
        event_stream=app.state.event_stream,
        db_session_factory=get_db_session
    )
    await my_module_consumer.start()
    app.state.my_module_consumer = my_module_consumer
```

### Monitoring

- **Event Publish Errors:** Check logs für `"Event publishing failed"`
- **Consumer Lag:** Query Redis Stream `XINFO GROUPS brain:events:stream`
- **Dedup Table Growth:** Monitor `processed_events` row count

### Troubleshooting

**Problem:** Events werden nicht verarbeitet

**Lösung:**
1. Check Consumer läuft: `curl http://localhost:8000/api/health`
2. Check Redis Stream: `redis-cli XINFO STREAM brain:events:stream`
3. Check Consumer Group: `redis-cli XINFO GROUPS brain:events:stream`

---

## Migration Notes

**Migrated:** YYYY-MM-DD
**From:** Synchrone Modul-Aufrufe
**To:** EventStream-basiert (Charter v1.0 compliant)

**Breaking Changes:**
- Entfernt: Direkter Import von `OtherModuleService`
- Ersetzt durch: Event-Publikation (`my_module.resource.created`)

---
```

**Dieses Template ist PFLICHT** – kein Freestyle-Format erlaubt.

---

## 11. Häufige Fehler & Anti-Patterns

### 11.1 Anti-Pattern: Direkte Modul-Imports

❌ **FALSCH:**

```python
# backend/app/modules/payment/service.py
from backend.app.modules.course_access.service import CourseAccessService

async def process_payment(self, ...):
    # Direkter synchroner Aufruf
    course_service = CourseAccessService()
    await course_service.grant_access(user_id, course_id)
```

✅ **RICHTIG:**

```python
# backend/app/modules/payment/service.py
from backend.mission_control_core.core.event_stream import Event, EventType

async def process_payment(self, ...):
    # Event publishen
    event = Event(
        id=str(uuid.uuid4()),
        type=EventType.PAYMENT_COMPLETED,
        payload={"user_id": user_id, "course_id": course_id},
        # ... meta fields ...
    )
    await self.event_stream.publish_event(event)
```

### 11.2 Anti-Pattern: Polling statt Events

❌ **FALSCH:**

```python
# Polling-Loop (ineffizient, nicht skalierbar)
while True:
    resources = await db.query("SELECT * FROM resources WHERE status = 'pending'")
    for resource in resources:
        await process_resource(resource)
    await asyncio.sleep(5)  # Polling alle 5s
```

✅ **RICHTIG:**

```python
# Event-driven (reaktiv, skalierbar)
async def handle_resource_created(event: Event):
    resource_id = event.payload["resource_id"]
    await process_resource(resource_id)

consumer.register_handler(EventType.RESOURCE_CREATED, handle_resource_created)
```

### 11.3 Anti-Pattern: event.id als Dedup-Key

❌ **FALSCH:**

```python
# In Consumer (WRONG!)
async def handle_event(self, event: Event):
    # Check if event.id already processed
    existing = await db.query(
        "SELECT 1 FROM processed WHERE event_id = ?",
        event.id  # FALSCH: event.id ändert sich bei Retry!
    )
    if existing:
        return  # Skip duplicate
```

✅ **RICHTIG:**

```python
# EventConsumer macht das automatisch korrekt:
# - Nutzt stream_message_id (PRIMARY)
# - event.id ist nur SECONDARY (audit)

# Du musst NICHTS tun – EventConsumer handled Dedup!
```

### 11.4 Anti-Pattern: „Nur dieses eine Mal synchron"

❌ **FALSCH:**

```python
# "Nur dieses eine Mal machen wir's synchron, weil..."
async def create_course(self, ...):
    course = await self._create_in_db(...)

    # "Aber hier müssen wir sofort wissen, ob es klappt!"
    await notification_service.send_email(...)  # FALSCH!

    await self._publish_event(...)
```

✅ **RICHTIG:**

```python
# ALLES über Events
async def create_course(self, ...):
    course = await self._create_in_db(...)

    # Event: Course created
    await self._publish_event(EventType.COURSE_CREATED, ...)

    # notification_service reagiert auf COURSE_CREATED Event
    # Falls Notification fehlschlägt → kein Impact auf Course Creation
```

**Warum?**
Synchrone Aufrufe führen zu:
- Tight coupling (Modul-Abhängigkeiten)
- Transaktions-Chaos (wer rollt was zurück?)
- Schlechte Testbarkeit
- Nicht skalierbar

### 11.5 Anti-Pattern: Events ohne meta-Felder

❌ **FALSCH:**

```python
event = Event(
    id=str(uuid.uuid4()),
    type=EventType.MY_EVENT,
    payload={...},
    timestamp=datetime.utcnow()
    # meta fehlt! Charter-Violation!
)
```

✅ **RICHTIG:**

```python
event = Event(
    id=str(uuid.uuid4()),
    type=EventType.MY_EVENT,
    payload={...},
    timestamp=datetime.utcnow(),
    meta={  # PFLICHT!
        "schema_version": 1,
        "producer": "my_service",
        "source_module": "my_module"
    }
)
```

### 11.6 Anti-Pattern: Event Publishing Fehler brechen Business Logic

❌ **FALSCH:**

```python
async def create_resource(self, ...):
    resource = await self._create_in_db(...)

    # Event publishen (OHNE try/except)
    await self.event_stream.publish_event(event)  # Kann fehlschlagen!

    return resource  # Wird NIE erreicht, wenn Event fehlschlägt!
```

✅ **RICHTIG:**

```python
async def create_resource(self, ...):
    resource = await self._create_in_db(...)

    # Event publishen (MIT try/except)
    try:
        await self.event_stream.publish_event(event)
    except Exception as e:
        logger.error(f"Event publishing failed: {e}")
        # NICHT re-raisen! Business Operation ist erfolgreich.

    return resource  # Wird IMMER erreicht
```

### 11.7 Anti-Pattern: Sensitive Daten in Payload

❌ **FALSCH:**

```python
payload = {
    "user_email": "user@example.com",  # PII!
    "password_hash": "...",  # Sensitive!
    "credit_card": "1234-5678-9012-3456"  # PII + Sensitive!
}
```

✅ **RICHTIG:**

```python
payload = {
    "user_id": "user_abc123",  # Nur ID
    "payment_method_id": "pm_xyz456"  # Nur ID (Stripe)
    # Keine PII, keine Secrets
}
```

### 11.8 Anti-Pattern: Parallele Codepfade (Legacy + Event)

❌ **FALSCH:**

```python
async def create_resource(self, ...):
    if os.getenv("USE_EVENTS") == "true":
        await self._create_with_events(...)  # Neuer Weg
    else:
        await self._create_legacy(...)  # Alter Weg (parallel!)
```

✅ **RICHTIG:**

```python
async def create_resource(self, ...):
    # NUR ein Weg (Event-basiert)
    resource = await self._create_in_db(...)
    await self._publish_event(...)
    return resource

    # Legacy-Code GELÖSCHT (nicht auskommentiert!)
```

---

## Zusammenfassung

**Ein Modul ist Charter v1.0 compliant, wenn:**

1. ✅ Alle Events haben `meta.*` Felder (schema_version, producer, source_module)
2. ✅ EventStream ist required (kein `if event_stream is not None`)
3. ✅ Consumer nutzt `stream_message_id` als PRIMARY dedup key (nicht `event.id`)
4. ✅ Permanent Errors → ACK, Transient Errors → NO ACK
5. ✅ 4 Tests grün (Event publish, Consumer, Idempotency, Error handling)
6. ✅ Legacy-Code gelöscht (keine parallelen Pfade)
7. ✅ README aktualisiert (Events Published/Consumed)

**Keine Ausnahmen. Keine Sonderfälle. Ein Weg.**

---

**Ende MODULE_MIGRATION_GUIDE.md**

**Version:** 1.0.0
**Verbindlich für:** Sprint 1–3 (Modul-Migrationen)
**Maintainer:** BRAiN Core Team
**Letzte Änderung:** 2025-12-28
