# Sprint 1 - Phase 0: course_factory Modul-Analyse

**Datum:** 2025-12-28
**Modul:** `backend/app/modules/course_factory`
**Status:** Phase 0 - Analyse abgeschlossen

---

## 1. Fachlicher Zweck

**Einzeiler:**
Generiert vollständige Online-Kurse aus einer Kursbeschreibung mittels Template-basierter Content-Generation und LLM-Integration.

**Hauptverantwortung:**
- Kurs-Outline erstellen (4-6 Module, 3-5 Lektionen pro Modul)
- Lesson-Content generieren (Markdown, vollständig oder Placeholder)
- Quiz erstellen (10-15 MCQs)
- Landing Page generieren
- Workflow-Management (draft → review → publish_ready → published)
- IR-Governance Integration (alle Aktionen tracken)
- WebGenesis Integration (Staging-Deployment vorbereiten)
- Monetization/Progress Tracking

---

## 2. Modul-Struktur

```
course_factory/
├── service.py                  # Haupt-Orchestrator (CourseFactoryService)
├── workflow.py                 # State Machine (draft → published)
├── monetization_service.py     # Payment/Progress Tracking
├── enhancements.py             # Content Enhancement (Flashcards, etc.)
├── webgenesis_integration.py   # WebGenesis Staging Deploy
├── generators/
│   ├── outline_generator.py    # Kurs-Struktur
│   ├── lesson_generator.py     # Lesson-Content
│   ├── quiz_generator.py       # Quiz-Fragen
│   └── landing_generator.py    # Landing Page
├── router.py                   # FastAPI Endpoints
└── schemas.py                  # Pydantic Models
```

---

## 3. Zustandsänderungen (Business Events)

### 3.1 Kurs-Generierung (Service.py)

| Methode | Zustandsänderung | Relevanz |
|---------|------------------|----------|
| `generate_course()` | Kurs erstellt, Outline generiert, Lessons erstellt, Quiz erstellt, Landing Page erstellt, Artifacts gespeichert | **CRITICAL** |
| `generate_ir()` | IR erstellt (Governance-Trail) | **HIGH** |
| `_save_course_artifacts()` | Files auf Disk gespeichert | **MEDIUM** |
| `_deploy_to_staging()` | Staging-Deployment durchgeführt | **HIGH** |

### 3.2 Workflow State Transitions (workflow.py)

| Transition | From State | To State | Requires Approval |
|------------|------------|----------|-------------------|
| `draft → review` | DRAFT | REVIEW | No |
| `review → publish_ready` | REVIEW | PUBLISH_READY | Yes (optional HITL) |
| `publish_ready → published` | PUBLISH_READY | PUBLISHED | No |
| `* → archived` | ANY | ARCHIVED | No |

### 3.3 Monetization (monetization_service.py)

| Methode | Zustandsänderung | Relevanz |
|---------|------------------|----------|
| `update_progress()` | User Progress aktualisiert | **MEDIUM** |
| `complete_course()` | Kurs abgeschlossen, Zertifikat ausgestellt | **HIGH** |
| `create_pack()` | Kurs-Pack erstellt (Monetization) | **MEDIUM** |

### 3.4 Enhancements (enhancements.py)

| Methode | Zustandsänderung | Relevanz |
|---------|------------------|----------|
| `generate_flashcards()` | Flashcards generiert | **LOW** |
| `enhance_content()` | Content enhanced (SEO, etc.) | **LOW** |

---

## 4. Externe Abhängigkeiten

### 4.1 Module (Direct Imports)

| Modul | Import | Nutzung |
|-------|--------|---------|
| `ir_governance` | `IR, IRStep, IRAction, IRProvider` | Governance-Trail für alle Aktionen |
| (KEINE ANDEREN) | - | course_factory ist **isoliert** (gut für Migration!) |

### 4.2 Externe APIs

| API | Zweck | Nutzung |
|-----|-------|---------|
| LLM (Ollama) | Content-Generierung | Lesson Content, Quiz Questions |
| Filesystem | Artifact Storage | `storage/courses/{course_id}/` |
| WebGenesis (geplant) | Staging Deployment | Preview-URL generieren |

### 4.3 Datenbank

- **Keine direkten DB-Aufrufe in course_factory**
- Alles über File-basierte Storage (`storage/courses/`)
- Monetization-Service nutzt DB (separates Concern)

---

## 5. Aktuelle Event-Nutzung

**Status:** ❌ **KEINE EventStream-Integration vorhanden**

**Grep-Ergebnis:**
```bash
grep -r "EventStream\|event_stream\|publish_event" backend/app/modules/course_factory
# No files found
```

**Bewertung:**
- course_factory ist **reiner Producer** (keine Consumer)
- Nutzt aktuell **synchrone Orchestrierung**
- Perfekt für Event-Migration (keine Legacy-Events)

---

## 6. Geplante Events (Output Phase 0)

### 6.1 Course Generation Lifecycle

#### Event 1: `course.generation.requested`
**Wann:** Zu Beginn von `generate_course()` (nach Validierung)
**Payload:**
- `course_id` (str): Unique Course ID
- `title` (str): Kurs-Titel
- `description` (str): Kurs-Beschreibung
- `language` (str): Sprache (de/en/fr/es)
- `target_audiences` (list[str]): Zielgruppen
- `tenant_id` (str): Mandant
- `dry_run` (bool): Dry-Run Modus
**Consumers:** (TBD: Analytics, Monitoring)

#### Event 2: `course.outline.created`
**Wann:** Nach erfolgreicher Outline-Generierung
**Payload:**
- `course_id` (str)
- `modules_count` (int)
- `total_lessons` (int)
- `template_id` (str): Verwendetes Template
**Consumers:** (TBD: course_distribution vorbereiten)

#### Event 3: `course.lesson.generated`
**Wann:** Jede vollständige Lesson generiert (loop)
**Payload:**
- `course_id` (str)
- `lesson_id` (str)
- `lesson_title` (str)
- `content_length` (int): Zeichen-Anzahl
**Consumers:** (TBD: Progress Tracking)

#### Event 4: `course.quiz.created`
**Wann:** Quiz erfolgreich generiert
**Payload:**
- `course_id` (str)
- `question_count` (int)
- `question_ids` (list[str])
**Consumers:** (TBD: Quiz-Service, Assessment)

#### Event 5: `course.landing_page.created`
**Wann:** Landing Page generiert
**Payload:**
- `course_id` (str)
- `landing_page_url` (str): Staging-URL (falls deployed)
**Consumers:** (TBD: Marketing, SEO)

#### Event 6: `course.generation.completed`
**Wann:** Gesamter Generierungs-Prozess erfolgreich
**Payload:**
- `course_id` (str)
- `total_modules` (int)
- `total_lessons` (int)
- `full_lessons_generated` (int)
- `quiz_questions_count` (int)
- `evidence_pack_path` (str)
- `execution_time_seconds` (float)
**Consumers:** **CRITICAL** → course_distribution, Analytics, Notification

#### Event 7: `course.generation.failed`
**Wann:** Generierung fehlschlägt (Exception in `generate_course()`)
**Payload:**
- `course_id` (str)
- `error_message` (str)
- `error_type` (str): Exception-Type
- `execution_time_seconds` (float)
**Consumers:** Alerting, Error Tracking

### 6.2 Workflow State Transitions

#### Event 8: `course.workflow.transitioned`
**Wann:** Workflow-State ändert sich (`workflow.py:transition()`)
**Payload:**
- `course_id` (str)
- `from_state` (str): DRAFT, REVIEW, etc.
- `to_state` (str)
- `transitioned_by` (str): User/System
- `requires_approval` (bool)
- `approval_token` (str, optional)
**Consumers:** Notification, HITL Dashboard

### 6.3 Deployment Events

#### Event 9: `course.deployed.staging`
**Wann:** Staging-Deployment erfolgreich
**Payload:**
- `course_id` (str)
- `staging_url` (str)
- `deployed_at` (timestamp)
**Consumers:** course_distribution, WebGenesis, Preview Service

#### Event 10: `course.deployed.production` (Future)
**Wann:** Prod-Deployment erfolgreich (NICHT in Sprint 1)
**Payload:**
- `course_id` (str)
- `production_url` (str)
**Consumers:** CDN, Analytics, Billing

### 6.4 Monetization Events (Optional - Sprint 2?)

#### Event 11: `course.progress.updated`
**Wann:** User macht Fortschritt
**Payload:**
- `course_id` (str)
- `user_id` (str)
- `lesson_id` (str)
- `progress_percentage` (float)
**Consumers:** Progress Dashboard, Gamification

#### Event 12: `course.completed`
**Wann:** User schließt Kurs ab
**Payload:**
- `course_id` (str)
- `user_id` (str)
- `completion_date` (timestamp)
- `certificate_id` (str)
**Consumers:** Certificate Service, Badge System, Email Notification

---

## 7. Event-Consumer Analyse

**Ist course_factory ein Consumer?**
❌ **NEIN** (in Sprint 1)

**Begründung:**
- course_factory ist **Producer-only** (Content-Generierung)
- Keine Reaktion auf externe Events
- Workflow ist intern (State Machine)

**Ausnahme (Future):**
- course_factory KÖNNTE auf `payment.completed` reagieren → dann Kurs freischalten
- ABER: Das ist Monetization-Concern → nicht in Sprint 1

**Decision:** **Consumer-Implementierung überspringen in Sprint 1** (Phase 3 entfällt)

---

## 8. Legacy-Code Identifikation

### 8.1 Synchrone Cross-Module Aufrufe

**Gefunden:** ❌ **KEINE**

```python
# Grep-Ergebnis:
grep -r "from.*import.*Service" backend/app/modules/course_factory
# Nur interne Services (MonetizationService, EnhancementService)
```

**Bewertung:**
- ✅ course_factory ist bereits isoliert
- ✅ Keine direkten Modul-Imports (außer ir_governance, was OK ist)
- ✅ Keine synchronen Service-Aufrufe

### 8.2 Zu löschende/migrierende Patterns

**Nichts gefunden** – Modul ist "clean" (kein Legacy-Ballast)

**Einzige Änderung erforderlich:**
- EventStream **hinzufügen** (nicht ersetzen)
- Events **publizieren** nach erfolgreichen Zustandsänderungen

---

## 9. EventType Registrierung (Vorbereitung Phase 1)

**Neue EventTypes für `event_stream.py`:**

```python
class EventType(str, Enum):
    # ... existing types ...

    # Course Factory Events
    COURSE_GENERATION_REQUESTED = "course.generation.requested"
    COURSE_OUTLINE_CREATED = "course.outline.created"
    COURSE_LESSON_GENERATED = "course.lesson.generated"
    COURSE_QUIZ_CREATED = "course.quiz.created"
    COURSE_LANDING_PAGE_CREATED = "course.landing_page.created"
    COURSE_GENERATION_COMPLETED = "course.generation.completed"
    COURSE_GENERATION_FAILED = "course.generation.failed"

    COURSE_WORKFLOW_TRANSITIONED = "course.workflow.transitioned"

    COURSE_DEPLOYED_STAGING = "course.deployed.staging"
    COURSE_DEPLOYED_PRODUCTION = "course.deployed.production"  # Future

    # Monetization (Optional - Sprint 2)
    # COURSE_PROGRESS_UPDATED = "course.progress.updated"
    # COURSE_COMPLETED = "course.completed"
```

---

## 10. Abhängigkeiten für Migration

### 10.1 EventStream Verfügbarkeit

✅ **EventStream ist bereits verfügbar** (`backend/mission_control_core/core/event_stream.py`)

### 10.2 Alembic Migration

✅ **Migration 002 bereits angewendet** (`processed_events` Tabelle existiert)

### 10.3 Environment

✅ **`BRAIN_EVENTSTREAM_MODE=required`** (default, korrekt)

---

## 11. Risiko-Bewertung

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Event Publishing schlägt fehl | LOW | MEDIUM | Try/except in Producer, Business Logic nicht brechen |
| Payload zu groß (Lesson Content) | MEDIUM | LOW | Nur IDs publishen, kein Full Content |
| Workflow-Transitions race conditions | LOW | MEDIUM | State Machine ist synchron (OK) |
| IR-Governance Overhead | LOW | LOW | IR bleibt unverändert (separates Concern) |

**Gesamt-Risiko:** ✅ **LOW** (course_factory ist gut strukturiert)

---

## 12. Go/No-Go Entscheidung Phase 1

### Vorbedingungen Check

- [x] EventStream läuft im `required` Mode
- [x] Alembic Migration `002` angewendet
- [x] Modul identifiziert (course_factory)
- [x] Modul-Owner: BRAiN Core Team
- [x] Keine kritischen Abhängigkeiten

### Go-Kriterien

- [x] Modul produziert relevante Business Events (12 Events identifiziert)
- [x] Modul ist aktiv in Nutzung (ProductionsReady für PayCore)
- [x] Keine Legacy-Pfade zu bereinigen (clean module)
- [x] EventStream verfügbar

### Decision

✅ **GO FÜR PHASE 1** (Event Design)

---

## Nächste Schritte

**Phase 1: Event Design**
1. EventTypes zu `event_stream.py` hinzufügen
2. Event Envelope Templates definieren
3. Payload Schemas validieren
4. EVENTS.md für course_factory erstellen

**Geschätzte Events:** 7 kritische Events (Sprint 1 Scope)
- course.generation.requested
- course.outline.created
- course.lesson.generated (optional: loop)
- course.quiz.created
- course.landing_page.created
- course.generation.completed
- course.generation.failed

**Producer-Count:** 1 (CourseFactoryService)
**Consumer-Count:** 0 (in Sprint 1)

---

**Phase 0 Status:** ✅ **ABGESCHLOSSEN**
**Nächster Schritt:** Phase 1 - Event Design
**Datum:** 2025-12-28
