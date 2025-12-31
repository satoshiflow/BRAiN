# Sprint 13 – WebGenesis Deep Integration & LLM-Enhanced Course Content
## BRAiN · Author Workflow & Content Enhancement

**Status:** ✅ Implemented
**Date:** 2025-12-26
**Mode:** IR-Governance · Dry-Run-First · Fail-Closed

---

## 🎯 Ziel erreicht

Sprint 13 erweitert das CourseFactory-Modul aus Sprint 12 um professionelle Autoren-Workflows, LLM-basierte Content-Enhancements und tiefe WebGenesis-Integration:

✅ **Author Workflow State Machine** (draft → review → publish_ready → published)
✅ **LLM-Enhanced Content** (Opt-in, validiert, deterministische Placeholders für MVP)
✅ **Content Validators** (Regel-basiert, strukturelle Änderungen, Diff-Audit)
✅ **WebGenesis Deep Integration** (Theme-Binding, Section-Building, SEO, Preview)
✅ **IR-Governance Extended** (8 neue Actions, Risk Tiers)
✅ **Evidence Packs Extended** (Workflow-Transitionen, Enhancements, WebGenesis-Config)
✅ **Backward Compatible** (Sprint 12 bleibt voll funktionsfähig)

---

## 📘 Feature-Übersicht

### 1. Author Workflow State Machine

**Zweck:** Strukturierter Workflow von Kurs-Entwurf bis Veröffentlichung mit HITL-Approval-Gates.

**Workflow-States:**
```
DRAFT → REVIEW → PUBLISH_READY → PUBLISHED
   ↓       ↓            ↓             ↓
ARCHIVED ← ARCHIVED ← ARCHIVED ← ARCHIVED
```

**Allowed Transitions:**
- DRAFT → REVIEW (automatisch, wenn Content vollständig)
- REVIEW → DRAFT (zurück zu Bearbeitung)
- REVIEW → PUBLISH_READY (⚠️ Erfordert HITL-Approval)
- PUBLISH_READY → REVIEW (zurück zu Review)
- PUBLISH_READY → PUBLISHED (finale Veröffentlichung)
- Alle States → ARCHIVED (Archivierung)

**HITL Approval Gate:**
```python
# Review → Publish_Ready erfordert menschliche Freigabe
if to_state == WorkflowState.PUBLISH_READY and from_state == WorkflowState.REVIEW:
    if not hitl_approval:
        raise ValueError("HITL approval required for REVIEW → PUBLISH_READY transition")
```

**Rollback Support:**
```python
# Jede Transition kann rückgängig gemacht werden
rollback_transition = workflow_machine.rollback_transition(
    original_transition=transition,
    actor="admin",
    reason="Content needs revision"
)
```

**Evidence Pack:**
- Jede Transition wird gespeichert: `{course_id}/workflow_transitions/{transition_id}.json`
- Vollständiger Audit-Trail mit Actor, Timestamp, Reason

### 2. LLM-Enhanced Content (MVP: Placeholders)

**Zweck:** Opt-in Content-Verbesserung mit LLM, validiert und deterministisch.

**Enhancement Types:**
- `EXAMPLES` – Praktische Beispiele hinzufügen
- `SUMMARIES` – Zusammenfassungen generieren
- `FLASHCARDS` – Lernkarten erstellen
- `ANALOGIES` – Analogien und Vergleiche

**MVP Implementation:**
```python
# Sprint 13 MVP: Placeholder-basiert (keine echten LLM-Calls)
enhancement = self.enhancement_gen.enhance(lesson, EnhancementType.EXAMPLES)

# Ergebnis:
base_content + "\n\n**[TODO: LLM-enhanced examples will be added here]**"
```

**Future (LLM Integration):**
```python
# Zukünftig: Echter LLM-Call mit Prompt-Engineering
enhanced_content = await llm_client.generate(
    prompt=f"Add practical examples to: {base_content}",
    max_tokens=500
)
```

**Validation Pipeline:**
```python
# 1. Enhancement generieren
enhancement = generator.enhance(lesson, enhancement_type)

# 2. Validieren
passed, errors = validator.validate_enhancement(enhancement)

# 3. Diff-Audit
diff, diff_hash, stats = auditor.audit_diff(base_content, enhanced_content)

# 4. Evidence Pack speichern (wenn nicht dry-run)
```

**Validation Rules:**
- Max. 50% Längenzunahme
- Keine strukturellen Änderungen (Headings, Lists, Code Blocks)
- Kein leerer Content
- Diff-Hash für vollständigen Audit-Trail

### 3. Content Validators

**ContentValidator:**
```python
class ContentValidator:
    MAX_LENGTH_INCREASE_PERCENT = 50

    def validate_enhancement(self, enhancement: ContentEnhancement):
        errors = []

        # 1. Length check
        if enhanced_len > base_len * 1.5:
            errors.append("Enhanced content too long")

        # 2. Structural changes check
        if self._has_structural_changes(base, enhanced):
            errors.append("Structural changes detected")

        # 3. Empty content check
        if not enhanced_content.strip():
            errors.append("Enhanced content is empty")

        return len(errors) == 0, errors
```

**DiffAuditor:**
```python
class DiffAuditor:
    def audit_diff(self, base_content: str, enhanced_content: str):
        # 1. Generate unified diff
        diff = difflib.unified_diff(base.splitlines(), enhanced.splitlines())

        # 2. Compute diff hash (SHA-256)
        diff_hash = hashlib.sha256(unified_diff.encode()).hexdigest()

        # 3. Compute stats
        stats = {
            "base_length": len(base_content),
            "enhanced_length": len(enhanced_content),
            "length_increase": len(enhanced_content) - len(base_content),
            "length_increase_percent": ...,
            "diff_hash": diff_hash
        }

        return unified_diff, diff_hash, stats
```

### 4. WebGenesis Deep Integration

**4.1 Theme Binding**

**Verfügbare Themes:**
```python
TRUSTED_THEMES = {
    "course-minimal": {
        "name": "Course Minimal",
        "description": "Clean, minimal design for focused learning",
        "primary_color": "#2563eb",
        "framework": "nextjs"
    },
    "course-professional": {
        "name": "Course Professional",
        "description": "Professional corporate look for business courses",
        "primary_color": "#0f172a",
        "framework": "nextjs"
    },
    "course-modern": {
        "name": "Course Modern",
        "description": "Modern, vibrant design for creative courses",
        "primary_color": "#8b5cf6",
        "framework": "nextjs"
    }
}
```

**Theme Customization:**
```python
# Basis-Theme + Custom Colors
theme = await service.bind_theme(
    course_id="course_123",
    theme_id="course-professional",
    custom_colors={
        "primary": "#1e40af",
        "secondary": "#facc15",
        "accent": "#10b981"
    }
)
```

**4.2 Section Building**

**6 Section Types:**
```python
sections = [
    {
        "type": "hero",
        "order": 0,
        "content": {
            "title": outline.metadata.title,
            "subtitle": outline.metadata.description,
            "cta_text": "Jetzt starten"
        }
    },
    {
        "type": "syllabus",
        "order": 1,
        "content": {
            "modules": [{
                "title": module.title,
                "lessons": [...]
            } for module in outline.modules]
        }
    },
    {
        "type": "lesson_preview",
        "order": 2,
        "content": {
            "lessons": [full_lessons[:3]]  # First 3 full lessons
        }
    },
    {
        "type": "faq",
        "order": 3,
        "content": {
            "questions": [...]
        }
    },
    {
        "type": "cta",
        "order": 4,
        "content": {
            "text": "Starten Sie jetzt mit dem Kurs",
            "button_text": "Zum Kurs"
        }
    },
    {
        "type": "footer",
        "order": 5,
        "content": {
            "legal": "© 2025 BRAiN CourseFactory. Alle Rechte vorbehalten.",
            "disclaimer": "Dieser Kurs dient ausschließlich Bildungszwecken."
        }
    }
]
```

**4.3 SEO Pack Generation**

**Complete SEO Metadata:**
```python
seo_pack = {
    # Meta Tags
    "meta_title": "Alternativen zu Banken & Sparkassen – Online-Kurs",
    "meta_description": "Lernen Sie moderne Bankalternativen kennen...",

    # Open Graph (Facebook, LinkedIn)
    "og_title": "Alternativen zu Banken & Sparkassen",
    "og_description": "...",
    "og_type": "website",
    "og_image": "https://...",

    # Twitter Card
    "twitter_card": "summary_large_image",
    "twitter_title": "...",
    "twitter_description": "...",
    "twitter_image": "...",

    # JSON-LD (Schema.org Course)
    "json_ld": {
        "@context": "https://schema.org",
        "@type": "Course",
        "name": "Alternativen zu Banken & Sparkassen",
        "description": "...",
        "provider": {
            "@type": "Organization",
            "name": "BRAiN CourseFactory"
        },
        "timeRequired": "PT310M",  # 310 Minuten
        "educationalLevel": "Beginner"
    },

    # Keywords
    "keywords": ["Banking", "FinTech", "Neobanken", ...]
}
```

**4.4 Preview URL Generation**

```python
# Versioned Preview URLs
preview_url = generator.generate_preview_url(
    course_id="course_abc123",
    version="v1.0.0"
)

# Ergebnis:
# https://preview.webgenesis.local/courses/course_abc123?v=v1.0.0
```

---

## 🏗️ Technische Implementation

### Module Struktur (Sprint 13 Ergänzungen)

```
backend/app/modules/course_factory/
├── enhanced_schemas.py        # 12 neue Pydantic Models
├── workflow.py                # WorkflowStateMachine
├── webgenesis_integration.py  # ThemeRegistry, SectionBuilder, SEOGenerator, PreviewURLGenerator
├── validators.py              # ContentValidator, DiffAuditor
├── enhancements.py            # EnhancementGenerator, FlashcardGenerator, EnhancementService
├── service.py                 # Extended mit Sprint 13 Methods
└── router.py                  # Extended mit 7 neuen Endpoints
```

### IR Actions (Sprint 13)

| Action | Risk Tier | Approval | Implementiert |
|--------|-----------|----------|---------------|
| `course.enhance_examples` | 0 | Nein | ✅ |
| `course.enhance_summaries` | 0 | Nein | ✅ |
| `course.generate_flashcards` | 0 | Nein | ✅ |
| `course.workflow_transition` | 0 | Nein | ✅ |
| `webgenesis.bind_theme` | 0 | Nein | ✅ |
| `webgenesis.apply_seo` | 0 | Nein | ✅ |
| `webgenesis.build_sections` | 1 | Nein | ✅ |
| `webgenesis.preview` | 1 | Nein | ✅ |

**Risk Tier Logic (Sprint 13):**
- Content Enhancements = **Tier 0** (keine Side Effects)
- Workflow Transitions = **Tier 0** (nur Metadaten)
- WebGenesis Theme/SEO = **Tier 0** (nur Config)
- WebGenesis Build/Preview = **Tier 1** (Staging Deployment)

### API Endpoints (Sprint 13)

```bash
# Workflow Management
POST /api/course-factory/workflow/transition      # Transition workflow state
POST /api/course-factory/workflow/rollback        # Rollback transition

# Content Enhancements
POST /api/course-factory/enhance                  # Enhance content with LLM

# WebGenesis Integration
POST /api/course-factory/webgenesis/bind-theme    # Bind theme
POST /api/course-factory/webgenesis/build-sections # Build sections
POST /api/course-factory/webgenesis/generate-seo  # Generate SEO pack
POST /api/course-factory/webgenesis/preview       # Generate preview URL
```

---

## 📁 Evidence Pack (Sprint 13 Erweiterungen)

Neue Artefakte in `storage/courses/{course_id}/`:

```
{course_id}/
├── workflow_transitions/
│   ├── {transition_1_id}.json     # Workflow Transition 1
│   ├── {transition_2_id}.json     # Workflow Transition 2
│   └── ...
├── enhancements/
│   ├── enhancement_1234567890.json # Enhancement Result 1
│   └── ...
├── webgenesis_theme.json          # Theme Binding
├── webgenesis_sections.json       # Generated Sections
└── seo_pack.json                  # SEO Metadata
```

**Alle Dateien:**
- ✅ Timestamps
- ✅ Actor-Information (wer hat was geändert)
- ✅ Diff-Hashes (bei Content-Änderungen)
- ✅ Full Audit Trail

---

## 🔄 Workflow Example

### Typischer Kurs-Lifecycle

```python
# 1. Kurs generieren (Sprint 12)
result = await service.generate_course(request)
# → State: DRAFT

# 2. Content enhancen (Sprint 13)
enhancement_request = EnhancementRequest(
    course_id=result.course_id,
    lesson_ids=[...],
    enhancement_types=[EnhancementType.EXAMPLES, EnhancementType.SUMMARIES]
)
enhancement_result = await service.enhance_content(enhancement_request, lessons)

# 3. Workflow: Draft → Review
transition = await service.transition_workflow(
    course_id=result.course_id,
    from_state=WorkflowState.DRAFT,
    to_state=WorkflowState.REVIEW,
    actor="author_user_123",
    reason="Content ready for review"
)

# 4. WebGenesis: Theme binden
theme = await service.bind_theme(
    course_id=result.course_id,
    theme_id="course-professional"
)

# 5. WebGenesis: Sections bauen
sections = await service.build_sections(
    course_id=result.course_id,
    outline=result.outline,
    landing_page=result.landing_page
)

# 6. WebGenesis: SEO generieren
seo_pack = await service.generate_seo_pack(
    course_id=result.course_id,
    outline=result.outline
)

# 7. Preview URL generieren
preview_url = await service.generate_preview_url(
    course_id=result.course_id,
    version="v1.0.0"
)

# 8. Workflow: Review → Publish_Ready (mit HITL-Approval)
transition = await service.transition_workflow(
    course_id=result.course_id,
    from_state=WorkflowState.REVIEW,
    to_state=WorkflowState.PUBLISH_READY,
    actor="reviewer_user_456",
    hitl_approval=True,  # ⚠️ Erforderlich!
    reason="Content reviewed and approved"
)

# 9. Workflow: Publish_Ready → Published
transition = await service.transition_workflow(
    course_id=result.course_id,
    from_state=WorkflowState.PUBLISH_READY,
    to_state=WorkflowState.PUBLISHED,
    actor="admin_user_789",
    reason="Final publication"
)
```

---

## 🧪 Test-Beispiele

### 1. Workflow Transition (mit HITL-Approval)

```bash
curl -X POST http://localhost:8000/api/course-factory/workflow/transition \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "course_abc123",
    "from_state": "review",
    "to_state": "publish_ready",
    "actor": "reviewer@example.com",
    "hitl_approval": true,
    "reason": "Content approved by reviewer"
  }'
```

### 2. Content Enhancement

```bash
curl -X POST http://localhost:8000/api/course-factory/enhance \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "course_abc123",
    "lesson_ids": ["lesson_1", "lesson_2"],
    "enhancement_types": ["examples", "summaries"],
    "dry_run": false
  }'
```

### 3. Theme Binding

```bash
curl -X POST http://localhost:8000/api/course-factory/webgenesis/bind-theme \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "course_abc123",
    "theme_id": "course-professional",
    "custom_colors": {
      "primary": "#1e40af",
      "secondary": "#facc15"
    }
  }'
```

### 4. Preview URL Generation

```bash
curl -X POST http://localhost:8000/api/course-factory/webgenesis/preview \
  -H "Content-Type: application/json" \
  -d '{
    "course_id": "course_abc123",
    "version": "v1.0.0"
  }'
```

---

## ⚠️ Scope Boundaries (Sprint 13)

### ✅ In Scope

- Workflow State Machine (vollständig implementiert)
- LLM Enhancement Placeholders (MVP-ready für spätere LLM-Integration)
- Content Validators (regel-basiert, ohne LLM)
- WebGenesis Integration (Theme, Sections, SEO, Preview)
- Backward Compatibility mit Sprint 12
- Evidence Pack Extensions

### ❌ Out of Scope

- Tatsächliche LLM-Integration (Placeholder für zukünftige Sprints)
- Automatische Übersetzung (EN/FR/ES bleiben Placeholders)
- Production WebGenesis Deployment (Preview-URLs simuliert)
- Automatische Workflow-Transitionen (alle manuell)
- Content-Approval-UI (nur API)

---

## 🔮 Future Enhancements (Sprint 14+)

1. **LLM-Integration**
   - OpenAI, Anthropic Claude, oder lokales LLM
   - Prompt-Engineering für Content-Enhancements
   - A/B-Testing verschiedener LLM-Outputs

2. **Automatische Workflow-Transitionen**
   - Draft → Review (wenn Content vollständig)
   - Review → Publish_Ready (nach X positiven Reviews)

3. **Content-Approval-UI**
   - Visuelle Diff-Ansicht
   - Side-by-side Comparison (Base vs. Enhanced)
   - One-Click Approval/Reject

4. **Erweiterte Validatoren**
   - Tone Analysis (bleibt der Ton konsistent?)
   - Fact-Checking (sind neue Fakten korrekt?)
   - Source Marker Verification (sind Quellen angegeben?)

5. **WebGenesis Production Deployment**
   - Tatsächliche WebGenesis-Integration
   - Automatisches Deployment zu Staging/Production
   - DNS-Management
   - SSL-Zertifikate

---

## 📊 Definition of Done – Sprint 13

| Anforderung | Status |
|-------------|--------|
| Workflow State Machine implementiert | ✅ |
| HITL-Approval-Gates funktionsfähig | ✅ |
| Content Validators (regel-basiert) | ✅ |
| Diff-Audit vollständig | ✅ |
| LLM-Enhancement Placeholders | ✅ |
| WebGenesis Theme-Binding | ✅ |
| WebGenesis Section-Building | ✅ |
| WebGenesis SEO-Generation | ✅ |
| WebGenesis Preview-URLs | ✅ |
| 7 neue API-Endpoints | ✅ |
| 8 neue IR-Actions | ✅ |
| Evidence Pack Extensions | ✅ |
| Backward Compatibility | ✅ |
| Keine Eingriffe in Sprint 12 Features | ✅ |
| Dokumentation vollständig | ✅ |
| Repo clean, alles committed & pushed | ⏳ |

---

**Status:** ✅ **Sprint 13 Complete**
**Date:** 2025-12-26
**Next:** Git commit & push
