
# CourseFactory Module - Sprint 12

**Version:** 1.0.0
**Status:** MVP (Minimum Viable Product)
**Governance:** IR-Compliant, Fail-Closed, Dry-Run-First

---

## 📋 Overview

CourseFactory generates complete online courses from a single course description, with full IR governance integration for auditability and safety.

### Key Features

✅ **Course Outline Generation** (4-6 modules, 3-5 lessons each)
✅ **Full Lesson Content** (Markdown format, 3 fully developed by default)
✅ **Quiz Generation** (10-15 multiple-choice questions)
✅ **Landing Page Creation** (Hero, Value Prop, Target Audience)
✅ **Multilingual Structure** (DE/EN/FR/ES placeholders)
✅ **IR Governance** (Every action tracked and validated)
✅ **Dry-Run Support** (Test before execute)
✅ **Evidence Packs** (Full audit trail)
✅ **Micro-Niche Ready** (Cloneable for different audiences)

---

## 🏗️ Architecture

```
course_factory/
├── schemas.py              # Pydantic models (CourseOutline, Quiz, etc.)
├── generators/             # Content generators
│   ├── outline_generator.py    # 4-6 modules, 3-5 lessons each
│   ├── lesson_generator.py     # Full lesson content (Markdown)
│   ├── quiz_generator.py       # 10-15 MCQs with explanations
│   └── landing_generator.py    # Landing page content
├── service.py              # Orchestration & IR integration
├── router.py               # FastAPI endpoints
└── README.md               # This file
```

---

## 🔐 IR Governance

### IR Actions (Sprint 12)

| Action | Risk Tier | Requires Approval | Description |
|--------|-----------|-------------------|-------------|
| `course.create` | Tier 0 | No | Create course metadata |
| `course.generate_outline` | Tier 0 | No | Generate course structure |
| `course.generate_lessons` | Tier 0 | No | Generate lesson content |
| `course.generate_quiz` | Tier 0 | No | Generate quiz questions |
| `course.generate_landing` | Tier 0 | No | Generate landing page |
| `course.deploy_staging` | Tier 1 | No | Deploy to staging (low risk) |

**Governance Rules:**
- Content generation = **Tier 0** (read-only, no side effects)
- Staging deployment = **Tier 1** (low risk, staging only)
- Production deployment = **❌ Forbidden** (not in scope for Sprint 12)
- All actions require valid IR with idempotency keys
- Dry-run mode bypasses IR validation (for previews)

---

## 📡 API Endpoints

### 1. Module Information

```bash
GET /api/course-factory/info
```

**Response:**
```json
{
  "name": "CourseFactory",
  "version": "1.0.0",
  "features": ["..."],
  "ir_actions": ["course.create", "..."]
}
```

---

### 2. Generate Course (with IR Governance)

```bash
POST /api/course-factory/generate
```

**Request Body:**
```json
{
  "tenant_id": "brain_test",
  "title": "Alternativen zu Banken & Sparkassen – Was du heute wissen musst",
  "description": "Ein praxisnaher Grundlagenkurs...",
  "language": "de",
  "target_audiences": ["private_individuals", "employees"],
  "full_lessons_count": 3,
  "generate_quiz": true,
  "generate_landing_page": true,
  "deploy_to_staging": false,
  "staging_domain": "course-alt-banken.staging.brain",
  "dry_run": false
}
```

**Response:**
```json
{
  "success": true,
  "course_id": "abc123...",
  "outline": { "...": "..." },
  "quiz": { "...": "..." },
  "landing_page": { "...": "..." },
  "deployed": false,
  "staging_url": null,
  "evidence_pack_path": "storage/courses/abc123...",
  "ir_hash": "sha256_hash",
  "total_modules": 4,
  "total_lessons": 15,
  "full_lessons_generated": 3,
  "quiz_questions_count": 15,
  "execution_time_seconds": 2.5,
  "errors": [],
  "warnings": []
}
```

---

### 3. Generate IR Only (Preview)

```bash
POST /api/course-factory/generate-ir
```

**Use Case:** Inspect what will be done before approval.

**Response:** IR object with all steps

---

### 4. Validate IR

```bash
POST /api/course-factory/validate-ir
```

**Request Body:** IR object

**Response:**
```json
{
  "status": "PASS",
  "violations": [],
  "risk_tier": 0,
  "requires_approval": false,
  "ir_hash": "sha256_hash"
}
```

---

### 5. Dry-Run (No IR Validation)

```bash
POST /api/course-factory/dry-run
```

**Use Case:** Quick preview without governance overhead.

**Response:** Same as `/generate`, but with `dry_run=true` forced.

---

## 🎓 Course Structure

### German Banking Alternatives Course

**Title:** Alternativen zu Banken & Sparkassen – Was du heute wissen musst

**Modules:**

1. **Warum klassisches Bankwissen nicht mehr ausreicht** (3 lessons, 60 min)
2. **Übersicht der Alternativen** (4 lessons, 90 min)
3. **Risiken & Chancen** (4 lessons, 70 min)
4. **Informierte Entscheidungen treffen** (4 lessons, 90 min)

**Total:** 15 lessons, ~310 minutes

**Full Lessons (Default: 3):**
1. Die Entwicklung des Bankwesens seit 2000
2. Was sind Neobanken und FinTechs?
3. Regulierung und Einlagensicherung

**Placeholder Lessons:** Remaining 12 (structured outline + bulletpoints)

**Quiz:** 15 MCQs covering all modules

---

## 🌍 Multilingual Support

### MVP (Sprint 12)
- **German (DE):** Fully supported (template + content)
- **English (EN):** Placeholder structure only
- **French (FR):** Placeholder structure only
- **Spanish (ES):** Placeholder structure only

### i18n Structure

```json
{
  "course_id": "abc123",
  "languages": {
    "de": { "status": "full", "path": "courses/abc123/de/" },
    "en": { "status": "placeholder", "path": "courses/abc123/en/" },
    "fr": { "status": "placeholder", "path": "courses/abc123/fr/" },
    "es": { "status": "placeholder", "path": "courses/abc123/es/" }
  }
}
```

**Future:** Automatic translation via LLM or DeepL API.

---

## 🔄 Micro-Niche Cloning

The architecture supports creating variants of the same course for different audiences:

### Example: Banking Alternatives Course

| Audience | Adjustments |
|----------|-------------|
| **Private Individuals** | Focus on everyday banking, cost savings |
| **SME Entrepreneurs** | Business accounts, payment processing, invoicing |
| **Retirees** | Simplicity, safety, pension payments |
| **Students** | Low fees, international transfers, budgeting |

**How to Clone:**
1. Use same outline template
2. Adjust examples and language tone
3. Change target_audiences parameter
4. Generate new course_id

**Benefits:**
- Reuse core structure
- Maintain quality consistency
- Rapid deployment of niche variants

---

## 📁 Evidence Pack

Generated artifacts:

```
storage/courses/{course_id}/
├── outline.json          # Course structure
├── quiz.json             # Quiz questions
├── landing.json          # Landing page content
└── lessons/
    ├── {lesson_id_1}.md
    ├── {lesson_id_2}.md
    └── {lesson_id_3}.md
```

**Evidence Includes:**
- IR hash
- Validation results
- Generated timestamps
- File checksums
- Environment snapshot

---

## 🧪 Testing

### Manual Test

```bash
# 1. Dry-run (no IR, no files)
curl -X POST http://localhost:8000/api/course-factory/dry-run \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test",
    "title": "Test Course",
    "description": "Test description",
    "language": "de",
    "target_audiences": ["private_individuals"],
    "dry_run": true
  }'

# 2. Generate IR
curl -X POST http://localhost:8000/api/course-factory/generate-ir \
  -H "Content-Type: application/json" \
  -d '{...}'

# 3. Validate IR
curl -X POST http://localhost:8000/api/course-factory/validate-ir \
  -H "Content-Type: application/json" \
  -d '{IR_FROM_STEP_2}'

# 4. Generate course (with IR)
curl -X POST http://localhost:8000/api/course-factory/generate \
  -H "Content-Type: application/json" \
  -d '{...}'
```

---

## 🚀 Deployment Workflow

### Staging Deployment (Sprint 12 - Simulated)

```
1. Generate Course (dry_run=false)
2. Artifacts saved to storage/courses/{id}/
3. IR validated (PASS)
4. WebGenesis integration (TODO: Sprint 13)
5. Deploy to https://{staging_domain}/
6. Evidence pack generated
```

**Not Included in Sprint 12:**
- ❌ Actual WebGenesis deployment
- ❌ DNS configuration
- ❌ SSL certificates
- ❌ Production deployment

---

## ⚠️ Important Constraints

### Hard Rules (Sprint 12)

1. **No Production Deploy** - Only staging allowed
2. **No Payment Integration** - Educational content only
3. **No User Data** - No customer/student information
4. **No LMS Integration** - Standalone course generation
5. **Fail-Closed** - Invalid IR → block execution
6. **Dry-Run First** - Always test before execute

### Scope Boundaries

**In Scope:**
✅ Course structure generation
✅ Content generation (template-based)
✅ Quiz creation
✅ Landing page
✅ Evidence packs
✅ Staging deployment (simulated)

**Out of Scope:**
❌ Payment processing
❌ Email marketing
❌ Student enrollment
❌ LMS integration (Moodle, etc.)
❌ Production deployment
❌ Domain management

---

## 🔮 Future Enhancements

### Sprint 13+

- **LLM-Enhanced Content:** Dynamic lesson generation for any topic
- **Real WebGenesis Integration:** Actual deployment pipeline
- **Multi-Language Translation:** Automatic DE→EN/FR/ES
- **Video Script Generation:** Lesson content → video scripts
- **Interactive Elements:** Quizzes with immediate feedback
- **Progress Tracking:** Student analytics (if LMS integrated)
- **A/B Testing:** Landing page variants
- **SEO Optimization:** Meta tags, structured data

---

## 📞 Support

**Documentation:** This README
**API Docs:** http://localhost:8000/docs (Swagger UI)
**Logs:** Check `loguru` output for detailed execution traces
**Issues:** Report via GitHub Issues

---

**Last Updated:** 2025-12-26
**Sprint:** 12 - CourseFactory MVP
**Status:** ✅ Production-Ready (with constraints)
