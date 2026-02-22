# Course Factory Migration Plan
## Von REST-only → Event-basierte Architektur

**Datum:** 2026-02-22  
**Modul:** course_factory  
**Status:** CRITICAL (Go-Live Blocker)  
**Priorität:** P0  

---

## 🎯 Ziel

Course Factory soll Events publishen und empfangen können für:
- Kurs-Erstellung (course.generation.started/completed/failed)
- Zahlungs-Ereignisse (payment.*)
- Verteilung (distribution.*)

---

## 📊 Aktueller Status

**File:** `backend/app/modules/course_factory/`  
**Pattern:** REST-only (keine Events)  
**Charter-konform:** ❌ NEIN  
**Risk:** 🔴 CRITICAL

**Problem:**
- Direkte REST-Calls zu anderen Modulen
- Kein Audit-Trail
- Keine asynchrone Verarbeitung
- Keine Wiederherstellung bei Fehlern

---

## 🗓️ Migrations-Timeline

### **Woche 1: Event Design & Setup**

#### Tag 1-2: Event-Analyse
**Aufgaben:**
- [ ] Alle Zustandsänderungen identifizieren
- [ ] Externe Abhängigkeiten dokumentieren
- [ ] Event-Liste erstellen

**Fragen zu beantworten:**
1. Was passiert wenn ein Kurs erstellt wird?
2. Welche anderen Module müssen das wissen?
3. Was passiert bei Fehlern?

**Output:**
```markdown
## Events für course_factory

1. course.generation.started
   - Wann: Vor Kurs-Erstellung
   - Payload: topic, user_id, parameters
   
2. course.generation.completed
   - Wann: Nach erfolgreicher Erstellung
   - Payload: course_id, url, duration
   
3. course.generation.failed
   - Wann: Bei Fehler
   - Payload: error, retry_count
   
4. course.payment.required
   - Wann: Vor Bezahlung
   - Payload: course_id, amount, currency
   
5. course.payment.completed
   - Wann: Nach Zahlung
   - Payload: course_id, transaction_id
```

#### Tag 3-4: Event Implementierung

**Files zu ändern:**
```
backend/app/modules/course_factory/
├── service.py          # Event-Publishing hinzufügen
├── router.py           # Keine Änderung (REST bleibt)
├── events.py           # NEU: Event-Typen & Handler
└── consumer.py         # NEU: Event-Consumer
```

**Code-Änderungen:**

**1. service.py - Event Publishing:**
```python
# ALT
async def create_course(self, data: dict):
    course = await self.db.create(data)
    return course

# NEU
async def create_course(self, data: dict):
    # 1. Event publishen (VOR der Arbeit)
    await self.event_stream.publish(Event(
        type=EventType.COURSE_GENERATION_STARTED,
        payload={"topic": data['topic'], "user_id": data['user_id']}
    ))
    
    try:
        # 2. Kurs erstellen
        course = await self.db.create(data)
        await self.db.commit()
        
        # 3. Success Event
        await self.event_stream.publish(Event(
            type=EventType.COURSE_GENERATION_COMPLETED,
            payload={"course_id": course.id, "url": course.url}
        ))
        return course
        
    except Exception as e:
        # 4. Failure Event
        await self.event_stream.publish(Event(
            type=EventType.COURSE_GENERATION_FAILED,
            payload={"error": str(e), "retry_count": data.get('retry', 0)}
        ))
        raise
```

**2. consumer.py - Event Empfangen:**
```python
from mission_control_core.core.event_stream import EventConsumer

class CourseFactoryConsumer:
    """Consumes events relevant to course_factory"""
    
    async def on_payment_completed(self, event: Event):
        """Handle payment completion - start course delivery"""
        course_id = event.payload['course_id']
        
        # Kurs freischalten
        await self.service.enable_course(course_id)
        
        # Distribution Event senden
        await self.event_stream.publish(Event(
            type=EventType.COURSE_DISTRIBUTION_REQUESTED,
            payload={"course_id": course_id}
        ))
```

#### Tag 5: Testing

**Tests zu schreiben:**
```python
# test_events.py
async def test_course_generation_event_flow():
    # 1. Kurs erstellen
    course = await service.create_course({"topic": "AI"})
    
    # 2. Events prüfen
    events = await event_stream.get_events(type="course.generation.*")
    assert len(events) == 2  # started + completed
    
    # 3. Reihenfolge prüfen
    assert events[0].type == "course.generation.started"
    assert events[1].type == "course.generation.completed"
```

### **Woche 2: Integration & Rollout**

#### Tag 1-2: Course Distribution Integration
- [ ] Distribution-Modul auf Events umstellen
- [ ] End-to-End Test

#### Tag 3-4: Payment Integration
- [ ] PayCore Events implementieren
- [ ] Zahlungs-Flow testen

#### Tag 5: Go-Live Vorbereitung
- [ ] Monitoring einrichten
- [ ] Rollback-Plan
- [ ] Dokumentation

---

## 🔧 Technische Details

### Event-Typen (neu)

```python
class CourseEventType(str, Enum):
    # Generation
    GENERATION_STARTED = "course.generation.started"
    GENERATION_COMPLETED = "course.generation.completed"
    GENERATION_FAILED = "course.generation.failed"
    
    # Payment
    PAYMENT_REQUIRED = "course.payment.required"
    PAYMENT_COMPLETED = "course.payment.completed"
    PAYMENT_FAILED = "course.payment.failed"
    
    # Distribution
    DISTRIBUTION_REQUESTED = "course.distribution.requested"
    DISTRIBUTION_COMPLETED = "course.distribution.completed"
    DISTRIBUTION_FAILED = "course.distribution.failed"
```

### Datenbank-Änderungen

**Neue Events werden automatisch gespeichert:**
```sql
-- Bereits vorhanden durch Migration 002
-- Table: events (event_stream)
```

**Keine Schema-Änderung nötig!**

---

## ✅ Erfolgskriterien

| Kriterium | Wie gemessen | Ziel |
|-----------|--------------|------|
| Events publishen | Event-Log prüfen | 100% der Kurs-Erstellungen |
| Events empfangen | Consumer-Logs | Zahlungen werden verarbeitet |
| Reihenfolge | Event-Zeitstempel | Korrekte Reihenfolge |
| Fehlerhandling | Failed Events | < 1% Fehlerrate |
| Performance | Latenz | < 100ms zusätzlich |

---

## ⚠️ Risiken & Mitigation

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| Event-System überlastet | Mittel | Rate Limiting, Batch-Verarbeitung |
| Event-Verlust | Niedrig | Idempotency-Keys, Retry-Logik |
| Reihenfolge falsch | Niedrig | Zeitstempel + Sequenz-Nummern |
| Kompatibilität | Mittel | Versionierung im Event-Schema |

---

## 🚀 Go/No-Go Kriterien

**GO wenn:**
- [ ] Alle Tests grün
- [ ] Events werden korrekt publisiht
- [ ] Keine Performance-Einbußen > 20%
- [ ] Rollback-Plan getestet

**NO-GO wenn:**
- [ ] Kritische Bugs in Event-Verarbeitung
- [ ] Performance-Einbußen > 50%
- [ ] Datenverlust-Risiko

---

## 📋 Nächste Schritte

1. **Heute:** Event-Analyse starten
2. **Morgen:** Erste Events implementieren
3. **Diese Woche:** Testing & Integration
4. **Nächste Woche:** Go-Live

**Soll ich mit der Implementierung starten?** 🔥
