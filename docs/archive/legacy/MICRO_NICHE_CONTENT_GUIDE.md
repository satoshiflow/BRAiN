# Micro-Niche Content Guide
## BRAiN CourseFactory – Content Packs for Targeted Audiences

**Version:** 1.0.0
**Date:** 2025-12-26
**Purpose:** Guide for creating and using micro-niche content packs

---

## 📋 Overview

**Micro-niche content packs** enable you to create **targeted variants** of a base course without duplicating content. This allows:

- ✅ **Single Source of Truth (SSOT):** Base course remains canonical
- ✅ **Targeted Examples:** Replace generic examples with audience-specific ones
- ✅ **Localized Terminology:** Adjust language for different regions/cultures
- ✅ **Audience-Specific Modules:** Append modules relevant to specific groups
- ✅ **No Duplication:** Overlays are applied at render-time

**Example Use Cases:**
- Banking course → Variants for retirees, students, freelancers, SMEs
- Programming course → Variants for beginners, data scientists, game developers
- Marketing course → Variants for B2B, B2C, e-commerce, agencies

---

## 🎯 Core Concept: SSOT + Overlay

### Architecture

```
┌──────────────────┐
│  Base Course     │  ← SSOT (never duplicated)
│  (Canonical)     │
└────────┬─────────┘
         │
         ├─────→  Pack 1 (Retirees)      →  Rendered Course 1
         ├─────→  Pack 2 (Students)      →  Rendered Course 2
         ├─────→  Pack 3 (Freelancers)   →  Rendered Course 3
         └─────→  Pack 4 (SMEs)          →  Rendered Course 4
```

**Key Principles:**
1. **Base course** is created once (Sprint 12 flow)
2. **Packs** define targeted overlays (Sprint 14)
3. **Rendering** combines base + pack at runtime
4. **No duplication:** Updates to base automatically propagate to all variants

---

## 🛠️ Allowed Pack Operations

### Safe Operations (Whitelist)

| Operation | Description | Safety | Use Case |
|-----------|-------------|--------|----------|
| `REPLACE_TEXT` | Replace content of module/lesson | ✅ Safe | Audience-specific examples |
| `OVERRIDE_TITLE` | Override module/lesson title | ✅ Safe | Terminology localization |
| `OVERRIDE_DESCRIPTION` | Override module/lesson description | ✅ Safe | Audience-specific summaries |
| `APPEND_MODULE` | Append new module to end | ✅ Safe | Audience-specific bonus content |

### Forbidden Operations

- ❌ **DELETE_MODULE:** Cannot remove content (keeps base intact)
- ❌ **REORDER_MODULES:** Cannot change course structure
- ❌ **ARBITRARY_CODE:** No templates, no eval, no code execution
- ❌ **EXTERNAL_FETCH:** No network requests or file system access

**Rationale:** Fail-closed approach ensures packs cannot corrupt base course.

---

## 📝 Creating a Pack

### Step 1: Define Target Audience

Identify your audience:
- **Demographic:** Age, occupation, experience level
- **Goals:** What do they want to achieve?
- **Context:** How will they use the knowledge?
- **Language:** Cultural/regional considerations

**Example Audiences:**
- `retirees` - Retired individuals managing personal finances
- `students` - University students learning fundamentals
- `freelancers` - Self-employed professionals
- `smes` - Small/medium enterprise owners

### Step 2: Identify Overrides

Compare base content with audience needs:

| Base Content | Retirees Variant | Students Variant |
|--------------|------------------|------------------|
| Example: "As a startup founder..." | "As a retiree managing your pension..." | "As a student with a part-time job..." |
| Module title: "Advanced Strategies" | "Retirement Planning Strategies" | "Student Budget Strategies" |
| Technical jargon | Plain language | Simplified with definitions |

### Step 3: Create Pack

```bash
POST /api/courses/{course_id}/packs

{
  "target_audience": "retirees",
  "language": "de",
  "description": "Banking alternatives course tailored for retirees",
  "overrides": [
    {
      "operation": "override_title",
      "target_id": "module_1",
      "value": "Bankwesen für Rentner verstehen"
    },
    {
      "operation": "replace_text",
      "target_id": "lesson_1_1",
      "value": "Als Rentner haben Sie besondere Anforderungen..."
    },
    {
      "operation": "append_module",
      "target_id": "bonus_retirement",
      "value": {
        "title": "Altersvorsorge optimieren",
        "lessons": [...]
      }
    }
  ]
}
```

---

## 🎨 Pack Examples

### Example 1: Banking Course for Retirees

**Base Course:** "Alternativen zu Banken & Sparkassen"

**Pack Overrides:**
```json
{
  "pack_id": "pack_retirees_de",
  "target_audience": "retirees",
  "language": "de",
  "overrides": [
    {
      "operation": "override_title",
      "target_id": "module_1",
      "value": "Traditionelles Bankwesen für Rentner"
    },
    {
      "operation": "replace_text",
      "target_id": "lesson_1_2",
      "value": "# Neobanken im Rentenalter\n\nAls Rentner fragen Sie sich vielleicht: 'Brauche ich wirklich eine App-Bank?' Die Antwort ist: Es kommt darauf an.\n\n## Vorteile für Rentner:\n- Kostenlose Kontoführung schont die Rente\n- Online-Banking von zu Hause\n- Keine Filialbesuche nötig\n\n## Nachteile:\n- Kein persönlicher Berater vor Ort\n- Technologie-Hürden möglich\n- Bargeldabhebung ggf. komplizierter\n\n**Empfehlung:** Hybrid-Lösung mit traditioneller Bank + Neobank für Zusatzfunktionen."
    },
    {
      "operation": "append_module",
      "target_id": "module_retirement",
      "value": {
        "module_id": "module_5",
        "title": "Spezial: Altersvorsorge-Optimierung",
        "lessons": [
          {
            "lesson_id": "lesson_5_1",
            "title": "Riester- und Rürup-Alternativen",
            "content": "..."
          }
        ]
      }
    }
  ]
}
```

**Result:** Same base course, but with retirement-focused examples and bonus module.

### Example 2: Banking Course for Students

**Pack Overrides:**
```json
{
  "pack_id": "pack_students_de",
  "target_audience": "students",
  "language": "de",
  "overrides": [
    {
      "operation": "override_title",
      "target_id": "module_1",
      "value": "Banking Basics für Studenten"
    },
    {
      "operation": "replace_text",
      "target_id": "lesson_1_2",
      "value": "# Neobanken für Studenten\n\nAls Student brauchst du ein kostenloses Konto ohne versteckte Gebühren. Neobanken sind ideal:\n\n## Warum Neobanken für Studenten?\n- **100% kostenlos:** Keine Kontoführungsgebühr\n- **App-basiert:** Banking per Smartphone\n- **Cashback:** Geld zurück bei jedem Einkauf\n- **Weltweit:** Kostenlos Geld abheben im Auslandssemester\n\n**Top-Tipps:**\n1. N26 oder Revolut für Hauptkonto\n2. Trade Republic für ETF-Sparpläne (25€/Monat)\n3. Traditionelle Bank für BAföG-Konto behalten\n\n**Achtung:** Dispozinsen vermeiden! Niemals überziehen."
    },
    {
      "operation": "append_module",
      "target_id": "module_student_budget",
      "value": {
        "module_id": "module_5",
        "title": "Spezial: Studentenbudget Management",
        "lessons": [
          {
            "lesson_id": "lesson_5_1",
            "title": "Mit 800€/Monat auskommen",
            "content": "..."
          }
        ]
      }
    }
  ]
}
```

**Result:** Student-friendly language, relevant examples (study abroad, BAföG), bonus budget module.

### Example 3: Banking Course for SMEs (Small Businesses)

**Pack Overrides:**
```json
{
  "pack_id": "pack_smes_de",
  "target_audience": "smes",
  "language": "de",
  "overrides": [
    {
      "operation": "override_title",
      "target_id": "module_1",
      "value": "Geschäftskonten und FinTech-Lösungen"
    },
    {
      "operation": "override_description",
      "target_id": "module_2",
      "value": "Wie FinTechs Ihr Geschäft effizienter machen: Buchhaltung, Rechnungen, Zahlungsabwicklung"
    },
    {
      "operation": "replace_text",
      "target_id": "lesson_2_3",
      "value": "# FinTech-Tools für KMUs\n\n## Buchhaltung\n- **lexoffice:** Automatische Belegerfassung\n- **sevDesk:** Buchhaltung + Rechnungen\n- **DATEV:** Steuerberater-Integration\n\n## Zahlungen\n- **SumUp:** Kartenzahlung ohne Vertrag\n- **Stripe:** Online-Zahlungen\n- **GoCardless:** SEPA-Lastschrift\n\n## Banking\n- **Qonto:** Geschäftskonto mit API\n- **Kontist:** Steuerrücklagen automatisch\n- **N26 Business:** Einfaches Firmenkonto"
    },
    {
      "operation": "append_module",
      "target_id": "module_sme_tools",
      "value": {
        "module_id": "module_5",
        "title": "Spezial: Digitale Finanztools für KMUs",
        "lessons": [...]
      }
    }
  ]
}
```

**Result:** Business-focused examples, tools for accounting/invoicing, bonus module on digital finance.

---

## 🌍 Multi-Language Strategy

### Base Course: German (Full Implementation)

Sprint 12 implemented full German content:
- 3 complete lessons (6500+ words)
- 12 structured placeholder lessons
- 15 quiz questions
- Landing page

### Other Languages: Placeholder + Packs

For EN/FR/ES:
1. **Base:** English translation of German content (future sprint)
2. **Packs:** Language-specific variants

**Example: English for UK vs US audiences**

```json
// Pack: English (UK)
{
  "language": "en",
  "target_audience": "uk_residents",
  "overrides": [
    {
      "operation": "replace_text",
      "target_id": "lesson_1_1",
      "value": "In the UK, neobanks like Monzo and Starling have revolutionised banking. Here's why:\n\n- **Free current accounts:** No monthly fees\n- **FCA regulated:** Financial Conduct Authority protection\n- **GBP and EUR accounts:** Ideal for European travel\n\n**Note:** FSCS protection up to £85,000."
    }
  ]
}

// Pack: English (US)
{
  "language": "en",
  "target_audience": "us_residents",
  "overrides": [
    {
      "operation": "replace_text",
      "target_id": "lesson_1_1",
      "value": "In the US, neobanks like Chime and Varo offer alternatives to traditional banks:\n\n- **No monthly fees:** Save $12-15/month\n- **FDIC insured:** Up to $250,000 protection\n- **Early direct deposit:** Get your paycheck 2 days early\n\n**Note:** Different from European neobanks due to US banking regulations."
    }
  ]
}
```

---

## 🔄 Rendering Process

### How Rendering Works

```python
# Pseudocode
def render_course(base_course, pack):
    rendered = deep_copy(base_course)

    for override in pack.overrides:
        if override.operation == "replace_text":
            find_and_replace(rendered, override.target_id, override.value)

        elif override.operation == "override_title":
            find_and_set_title(rendered, override.target_id, override.value)

        elif override.operation == "override_description":
            find_and_set_description(rendered, override.target_id, override.value)

        elif override.operation == "append_module":
            rendered.modules.append(override.value)

    return rendered
```

### API Usage

```bash
# Get pack
GET /api/courses/banking_course/packs
# → List of packs

# Render course with pack
GET /api/courses/banking_course/render?pack_id=pack_retirees_de
# → Rendered course with overrides applied
```

### Caching Strategy

**Recommended:**
1. **Base course:** Cache heavily (rarely changes)
2. **Packs:** Cache moderately (may be updated)
3. **Rendered course:** Generate on-demand or cache with TTL

**Cache Key:**
```
rendered_course:{course_id}:{pack_id}:{base_version}:{pack_version}
```

---

## ✅ Best Practices

### 1. Keep Packs Minimal

**✅ DO:**
- Only override what's truly different for the audience
- Reuse base content wherever possible
- Focus on examples, not entire rewrites

**❌ DON'T:**
- Replace entire modules (defeats SSOT purpose)
- Duplicate content that's already in base
- Create pack-specific content that should be in base

### 2. Maintain Consistency

**✅ DO:**
- Use consistent tone across all packs
- Keep module structure similar (users may switch packs)
- Ensure overrides don't contradict base course

**❌ DON'T:**
- Completely change course structure in a pack
- Use wildly different terminology
- Create contradictions between base and pack

### 3. Version Control

**✅ DO:**
- Increment pack `version` on significant changes
- Document pack changes in `description`
- Test rendered course after pack updates

**❌ DON'T:**
- Silently modify packs without version bump
- Break backward compatibility without notice

### 4. Audience Research

**✅ DO:**
- Research target audience needs before creating pack
- Test pack with representative users
- Collect feedback and iterate

**❌ DON'T:**
- Assume audience needs without validation
- Create packs based on stereotypes
- Ignore user feedback

---

## 🧪 Testing Packs

### Test Checklist

Before deploying a pack:

- [ ] All overrides apply successfully (no errors)
- [ ] Rendered course structure is valid
- [ ] No broken references (all target_ids exist)
- [ ] Examples are relevant to target audience
- [ ] Tone is consistent with base course
- [ ] No contradictions with base content
- [ ] Pack renders in <100ms (performance)

### Test Script

```python
def test_pack(base_course, pack):
    # 1. Render
    rendered = render_course(base_course, pack)

    # 2. Validate structure
    assert len(rendered.modules) >= len(base_course.modules)

    # 3. Check overrides applied
    for override in pack.overrides:
        if override.operation == "override_title":
            module = find_module(rendered, override.target_id)
            assert module.title == override.value

    # 4. Performance
    import time
    start = time.time()
    render_course(base_course, pack)
    assert (time.time() - start) < 0.1  # <100ms

    print(f"✅ Pack {pack.pack_id} validated")
```

---

## 📊 Pack Analytics

### Tracking Pack Usage

**Metrics to Track:**
- Enrollments per pack
- Completion rate per pack
- User satisfaction per pack
- Most popular packs

**Example Query:**
```python
analytics = get_analytics_summary(course_id="banking_course")

# Extend with pack-specific metrics (future)
pack_stats = {
    "pack_retirees_de": {
        "enrollments": 150,
        "completions": 120,
        "completion_rate": 80.0
    },
    "pack_students_de": {
        "enrollments": 300,
        "completions": 180,
        "completion_rate": 60.0
    }
}
```

**Privacy:** Aggregate stats only, no individual tracking.

---

## 🔮 Future Enhancements

### 1. Pack Marketplace

- Community-contributed packs
- Rating and review system
- Pack discovery by industry/role

### 2. Smart Pack Recommendations

- AI-based pack suggestions based on user profile
- A/B testing of pack variants
- Automatic pack selection

### 3. Dynamic Packs

- User-customizable packs
- AI-generated examples based on user input
- Real-time pack updates

### 4. Pack Inheritance

- Parent-child pack relationships
- Share common overrides across related packs

---

## 📚 Resources

- **API Documentation:** See Sprint 14 Implementation Report
- **Base Course Creation:** See Sprint 12 Documentation
- **Testing:** `backend/tests/test_sprint14_courses.py`

---

**Version:** 1.0.0
**Date:** 2025-12-26
**Status:** ✅ Production Ready
