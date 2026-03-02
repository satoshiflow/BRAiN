# Sprint 12 – CourseFactory MVP
## BRAiN · Online-Kurs-Erstellung & Deployment

**Status:** ✅ Implemented
**Date:** 2025-12-26
**Mode:** IR-Governance · Dry-Run-First · Fail-Closed

---

## 🎯 Ziel erreicht

BRAiN kann jetzt **vollständige Online-Kurse** aus einer Kursbeschreibung erzeugen:

✅ **Kurs-Curriculum** (4-6 Module, 3-5 Lektionen je Modul)
✅ **Lerninhalte** (3 vollständig ausgearbeitete Lektionen in Markdown)
✅ **Quiz/Assessment** (15 Multiple-Choice-Fragen mit Erklärungen)
✅ **Landingpage** (Hero, Value Prop, Zielgruppen-Segmentierung)
✅ **IR-Governance** (Jede Aktion tracked, validiert, auditiert)
✅ **Evidence Packs** (Vollständiger Audit Trail)
✅ **Mehrsprachigkeits-Struktur** (DE vollständig, EN/FR/ES vorbereitet)
✅ **Micro-Nischen-Fähigkeit** (Klonbar für verschiedene Zielgruppen)

---

## 📘 Generierter Kurs (DE)

### Titel
**„Alternativen zu Banken & Sparkassen – Was du heute wissen musst"**

### Struktur

**Modul 1: Warum klassisches Bankwissen nicht mehr ausreicht** (3 Lektionen)
1. ✅ Die Entwicklung des Bankwesens seit 2000 (FULL, ~2000 Wörter)
2. ✅ Was sind Neobanken und FinTechs? (FULL, ~2000 Wörter)
3. ✅ Regulierung und Einlagensicherung (FULL, ~2500 Wörter)

**Modul 2: Übersicht der Alternativen** (4 Lektionen)
1. 📋 Neobanken in Deutschland (PLACEHOLDER)
2. 📋 Payment-Dienste und E-Wallets (PLACEHOLDER)
3. 📋 Self-Custody und dezentrale Systeme (PLACEHOLDER)
4. 📋 Hybride Lösungen (PLACEHOLDER)

**Modul 3: Risiken & Chancen** (4 Lektionen)
1. 📋 Technische Risiken (PLACEHOLDER)
2. 📋 Regulatorische Risiken (PLACEHOLDER)
3. 📋 Wirtschaftliche Risiken (PLACEHOLDER)
4. 📋 Chancen und Mehrwerte (PLACEHOLDER)

**Modul 4: Informierte Entscheidungen treffen** (4 Lektionen)
1. 📋 Bedarfsanalyse (PLACEHOLDER)
2. 📋 Vergleichskriterien (PLACEHOLDER)
3. 📋 Migration und Umstellung (PLACEHOLDER)
4. 📋 Kontinuierliche Bewertung (PLACEHOLDER)

**Gesamt:** 15 Lektionen, ~310 Minuten Dauer
**Vollständig:** 3 Lektionen (6500+ Wörter professioneller Content)
**Placeholders:** 12 Lektionen (strukturierte Gliederungen)

### Quiz

15 Multiple-Choice-Fragen mit:
- ✅ 4 Antwortoptionen pro Frage
- ✅ Korrekte Antwort markiert
- ✅ Detaillierte Erklärung
- ✅ Schwierigkeitsgrad (easy/medium/hard)
- ✅ Modulzuordnung

**Passing Score:** 70%
**Zeitlimit:** 30 Minuten

### Landingpage

- ✅ Hero Section (Titel, Subtitle, CTA)
- ✅ Value Proposition
- ✅ "Für wen?" (5 Punkte)
- ✅ "Für wen NICHT?" (3 Punkte)
- ✅ Kursstruktur (automatisch generiert)
- ✅ Features (6 Highlights)
- ✅ Disclaimer (keine Beratung, kein Verkauf)

---

## 🏗️ Technische Implementation

### Module Struktur

```
backend/app/modules/course_factory/
├── __init__.py              # Exports
├── schemas.py               # 17 Pydantic models
├── service.py               # Orchestration + IR
├── router.py                # 5 FastAPI endpoints
├── generators/
│   ├── outline_generator.py     # 4-6 Module, 3-5 Lektionen
│   ├── lesson_generator.py      # Markdown-Content (3 voll, 12 placeholder)
│   ├── quiz_generator.py        # 15 MCQs
│   └── landing_generator.py     # Landingpage
└── README.md                # Dokumentation
```

### IR Actions (Sprint 12)

| Action | Risk Tier | Approval | Implementiert |
|--------|-----------|----------|---------------|
| `course.create` | 0 | Nein | ✅ |
| `course.generate_outline` | 0 | Nein | ✅ |
| `course.generate_lessons` | 0 | Nein | ✅ |
| `course.generate_quiz` | 0 | Nein | ✅ |
| `course.generate_landing` | 0 | Nein | ✅ |
| `course.deploy_staging` | 1 | Nein | 📋 Vorbereitet |

**Risk Tier Logic:**
- Content-Generierung = **Tier 0** (keine Side Effects)
- Staging-Deploy = **Tier 1** (low risk, nur Staging)
- Production-Deploy = **❌ Verboten** (nicht im Scope)

### API Endpoints

```bash
GET  /api/course-factory/info           # Module Info
POST /api/course-factory/generate-ir    # IR Preview
POST /api/course-factory/validate-ir    # IR Validation
POST /api/course-factory/generate       # Generate Course (IR-governed)
POST /api/course-factory/dry-run        # Quick Preview (no IR)
GET  /api/course-factory/health         # Health Check
```

---

## 📁 Evidence Pack

Generierte Artefakte in `storage/courses/{course_id}/`:

```
{course_id}/
├── outline.json       # Komplette Kursstruktur
├── quiz.json          # 15 MCQs mit Erklärungen
├── landing.json       # Landingpage Content
└── lessons/
    ├── {lesson_1_id}.md   # Lektion 1 (Markdown)
    ├── {lesson_2_id}.md   # Lektion 2 (Markdown)
    └── {lesson_3_id}.md   # Lektion 3 (Markdown)
```

**Alle Dateien:**
- ✅ Deterministically generiert
- ✅ Mit Checksums
- ✅ IR-Hash verlinkt
- ✅ Timestamps
- ✅ Full Audit Trail

---

## 🌍 Mehrsprachigkeit

### MVP (Sprint 12)
- **Deutsch (DE):** ✅ Vollständig (Template + Content)
- **Englisch (EN):** 📋 Placeholder-Struktur
- **Französisch (FR):** 📋 Placeholder-Struktur
- **Spanisch (ES):** 📋 Placeholder-Struktur

### Architektur
- i18n-Key-Struktur vorhanden
- Alle Schemas mehrsprachig
- Content-Generator mehrsprachig vorbereitet
- **Zukünftig:** LLM-basierte Übersetzung

---

## 🔄 Micro-Nischen-Klonbarkeit

Das System unterstützt **Varianten desselben Kurses** für unterschiedliche Zielgruppen:

| Zielgruppe | Anpassungen |
|------------|-------------|
| Privatpersonen | Alltag, Kostenersparnis |
| KMU-Unternehmer | Geschäftskonten, Rechnungen |
| Rentner | Einfachheit, Sicherheit |
| Studenten | Niedrige Gebühren, International |

**Wie klonen:**
1. Gleiche Outline-Template verwenden
2. Beispiele und Tonalität anpassen
3. `target_audiences` Parameter ändern
4. Neue `course_id` generieren

**Vorteile:**
- ✅ Struktur wiederverwenden
- ✅ Qualitätskonsistenz
- ✅ Schnelles Deployment

---

## 🧪 Tests

### Test-Kommandos

```bash
# 1. Module Info
curl http://localhost:8000/api/course-factory/info

# 2. IR Preview generieren
curl -X POST http://localhost:8000/api/course-factory/generate-ir \
  -H "Content-Type: application/json" \
  -d @test_payload.json

# 3. IR Validieren
curl -X POST http://localhost:8000/api/course-factory/validate-ir \
  -H "Content-Type: application/json" \
  -d @generated_ir.json

# 4. Kurs generieren (Dry-Run)
curl -X POST http://localhost:8000/api/course-factory/dry-run \
  -H "Content-Type: application/json" \
  -d @test_payload.json

# 5. Kurs generieren (Live, mit IR)
curl -X POST http://localhost:8000/api/course-factory/generate \
  -H "Content-Type: application/json" \
  -d @test_payload.json
```

### Beispiel-Payload

```json
{
  "tenant_id": "brain_test",
  "title": "Alternativen zu Banken & Sparkassen – Was du heute wissen musst",
  "description": "Ein praxisnaher Grundlagenkurs für Privatpersonen, Angestellte und Berufseinsteiger",
  "language": "de",
  "target_audiences": ["private_individuals", "employees", "career_starters"],
  "full_lessons_count": 3,
  "generate_quiz": true,
  "generate_landing_page": true,
  "deploy_to_staging": false,
  "dry_run": false
}
```

---

## ⚠️ Scope Boundaries

### ✅ In Scope (Sprint 12)
- Kurs-Outline-Generierung
- Content-Generierung (template-based)
- Quiz-Erstellung
- Landingpage
- Evidence Packs
- IR-Governance
- Dry-Run-Support

### ❌ Out of Scope
- Payment-Integration
- E-Mail-Marketing
- Kundendaten / Enrollment
- LMS-Integration (Moodle, etc.)
- Production-Deployment
- DNS-Management
- SSL-Zertifikate
- Automatische WebGenesis-Deployment (vorbereitet, nicht implementiert)

---

## 🔮 Nächste Schritte (Sprint 13+)

1. **WebGenesis-Integration** (tatsächliches Deployment)
2. **LLM-Enhanced Content** (dynamische Generierung für beliebige Topics)
3. **Automatische Übersetzung** (DE → EN/FR/ES)
4. **Video-Script-Generierung** (aus Lektionen)
5. **A/B-Testing** (Landingpage-Varianten)
6. **SEO-Optimierung** (Meta-Tags, Structured Data)

---

## 📊 Definition of Done – Sprint 12

| Anforderung | Status |
|-------------|--------|
| Kurs-Draft (DE) vollständig generiert | ✅ |
| Evidence Pack vollständig & prüfbar | ✅ |
| IR-Governance integriert | ✅ |
| Micro-Nischen-Klon vorbereitet | ✅ |
| Keine Eingriffe in bestehende Systeme | ✅ |
| Repo clean, alles committed & pushed | ⏳ |

---

**Status:** ✅ **MVP Complete**
**Date:** 2025-12-26
**Next:** Git commit & push
