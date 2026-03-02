# LLM Enhancement Guardrails
## BRAiN CourseFactory · Safe & Controlled Content Enhancement

**Version:** 1.0.0
**Date:** 2025-12-26
**Purpose:** Guidelines and technical constraints for LLM-based content enhancements

---

## 📋 Übersicht

Dieses Dokument definiert **strikte Guardrails** für LLM-basierte Content-Enhancements im CourseFactory-Modul. Ziel ist es, **sichere, validierte und kontrollierte** Content-Generierung zu ermöglichen, ohne die Qualität und Integrität der Kurse zu gefährden.

**Kernprinzipien:**
1. **Opt-in Only** – Enhancements niemals automatisch, nur auf explizite Anfrage
2. **Validierung First** – Jedes Enhancement wird vor Speicherung validiert
3. **Diff-Audit** – Vollständiger Audit-Trail aller Änderungen
4. **Human-in-the-Loop** – HITL-Approval für kritische Änderungen
5. **Fail-Closed** – Bei Validierungsfehlern wird Enhancement abgelehnt
6. **Deterministic Fallback** – Placeholders als Fallback bei LLM-Ausfall

---

## 🔒 Guardrail Categories

### 1. Content Integrity Guardrails

**Ziel:** Sicherstellen, dass LLM-Enhancements die ursprüngliche Content-Struktur nicht zerstören.

#### 1.1 Strukturelle Integrität

**Rule:** Keine Änderungen an strukturellen Markdown-Elementen.

**Verboten:**
- ❌ Hinzufügen/Entfernen von Headings (`# Heading`)
- ❌ Änderung von Listen (`-`, `*`, `1.`)
- ❌ Änderung von Code-Blocks (` ``` `)
- ❌ Änderung von Tabellen

**Erlaubt:**
- ✅ Hinzufügen von Text-Absätzen
- ✅ Hinzufügen von Inline-Code (`code`)
- ✅ Hinzufügen von Links und Formatierungen

**Implementation:**
```python
def _has_structural_changes(base: str, enhanced: str) -> bool:
    base_structure = self._extract_structure(base)
    enhanced_structure = self._extract_structure(enhanced)

    # Compare counts of structural elements
    for key in ["headings", "lists", "code_blocks"]:
        if base_structure[key] != enhanced_structure[key]:
            return True  # Structural change detected!

    return False
```

**Test Case:**
```python
# ✅ PASS: Nur Text hinzugefügt
base = "# Introduction\nThis is content."
enhanced = "# Introduction\nThis is content.\n\nHere is an example: xyz."

# ❌ FAIL: Heading hinzugefügt
base = "# Introduction\nThis is content."
enhanced = "# Introduction\nThis is content.\n\n## New Section\nMore content."
```

#### 1.2 Längenbeschränkung

**Rule:** Enhancements dürfen Content max. um 50% verlängern.

**Rationale:**
- Verhindert "Content-Bloat"
- Erhält Lesbarkeit
- Vermeidet Token-Limit-Probleme

**Implementation:**
```python
MAX_LENGTH_INCREASE_PERCENT = 50

def validate_length(base_content: str, enhanced_content: str) -> bool:
    base_len = len(base_content)
    enhanced_len = len(enhanced_content)

    max_allowed = base_len * (1 + MAX_LENGTH_INCREASE_PERCENT / 100)

    if enhanced_len > max_allowed:
        raise ValidationError(
            f"Enhanced content too long: {enhanced_len} chars "
            f"(max allowed: {int(max_allowed)})"
        )

    return True
```

**Example:**
```python
# Base: 1000 characters
# Max allowed: 1500 characters (1000 * 1.5)

# ✅ PASS: 1400 characters
# ❌ FAIL: 1600 characters
```

#### 1.3 Leerer Content

**Rule:** Enhanced Content darf niemals leer sein.

**Implementation:**
```python
if not enhanced_content.strip():
    raise ValidationError("Enhanced content is empty")
```

### 2. Content Quality Guardrails

**Ziel:** Sicherstellen, dass LLM-Enhancements die Content-Qualität verbessern, nicht verschlechtern.

#### 2.1 Tone Consistency (Future)

**Rule:** LLM-Enhanced Content muss denselben Ton wie Base Content haben.

**Tone Categories:**
- `formal` – Akademisch, professionell
- `casual` – Locker, freundlich
- `technical` – Fachlich, präzise
- `instructional` – Anleitend, didaktisch

**Implementation (Future):**
```python
# Tone Detection (LLM-based)
base_tone = detect_tone(base_content)
enhanced_tone = detect_tone(enhanced_content)

if base_tone != enhanced_tone:
    warnings.append(f"Tone mismatch: {base_tone} → {enhanced_tone}")
```

#### 2.2 Factual Accuracy (Future)

**Rule:** Neue Fakten müssen mit Quellen belegt werden.

**Source Marker:**
```markdown
Dies ist eine neue Aussage [Quelle: https://example.com].
```

**Implementation (Future):**
```python
# Detect new factual claims
new_claims = extract_new_claims(base_content, enhanced_content)

for claim in new_claims:
    if not has_source_marker(claim):
        warnings.append(f"Claim without source: {claim[:50]}...")
```

#### 2.3 Language Consistency

**Rule:** Enhanced Content muss in derselben Sprache wie Base Content sein.

**Implementation (Future):**
```python
base_lang = detect_language(base_content)
enhanced_lang = detect_language(enhanced_content)

if base_lang != enhanced_lang:
    raise ValidationError(f"Language mismatch: {base_lang} → {enhanced_lang}")
```

### 3. Security Guardrails

**Ziel:** Verhindern von schädlichem oder unsicherem Content.

#### 3.1 No External Code Execution

**Rule:** Enhancements dürfen keinen ausführbaren Code enthalten.

**Verboten:**
- ❌ JavaScript `<script>` Tags
- ❌ Inline Event Handlers (`onclick=...`)
- ❌ Base64-encoded Scripts
- ❌ External Resource Includes (außer whitelisted domains)

**Erlaubt:**
- ✅ Code-Beispiele in Markdown Code Blocks
- ✅ Inline-Code für Syntax-Highlighting

**Implementation (Future):**
```python
FORBIDDEN_PATTERNS = [
    r"<script",
    r"onclick=",
    r"onerror=",
    r"eval\(",
    r"Function\(",
]

for pattern in FORBIDDEN_PATTERNS:
    if re.search(pattern, enhanced_content, re.IGNORECASE):
        raise SecurityError(f"Forbidden pattern detected: {pattern}")
```

#### 3.2 No Personal Data

**Rule:** Enhancements dürfen keine persönlichen Daten enthalten.

**Verboten:**
- ❌ E-Mail-Adressen (außer Beispiele: `user@example.com`)
- ❌ Telefonnummern
- ❌ Kreditkartennummern
- ❌ IP-Adressen (außer Beispiele: `192.0.2.1`)

**Implementation (Future):**
```python
# Detect PII (Personally Identifiable Information)
if detect_email(enhanced_content):
    warnings.append("Email address detected")

if detect_phone_number(enhanced_content):
    warnings.append("Phone number detected")
```

#### 3.3 No Malicious Links

**Rule:** Alle Links müssen auf sichere Domains zeigen.

**Whitelist:**
```python
ALLOWED_DOMAINS = [
    "wikipedia.org",
    "github.com",
    "docs.python.org",
    "developer.mozilla.org",
    # ... weitere trusted domains
]
```

**Implementation (Future):**
```python
links = extract_links(enhanced_content)

for link in links:
    domain = extract_domain(link)
    if domain not in ALLOWED_DOMAINS:
        warnings.append(f"Untrusted link: {link}")
```

### 4. Operational Guardrails

**Ziel:** Sicherstellen, dass LLM-Enhancements operational sicher sind.

#### 4.1 Dry-Run First

**Rule:** Jedes Enhancement sollte zuerst im Dry-Run-Modus getestet werden.

**Implementation:**
```python
# Dry-Run Mode
enhancement_request = EnhancementRequest(
    course_id="course_123",
    lesson_ids=["lesson_1"],
    enhancement_types=[EnhancementType.EXAMPLES],
    dry_run=True  # ⚠️ Kein Speichern!
)

result = await service.enhance_content(request, lessons)

# User prüft result.enhancements
# Wenn OK: Nochmal ohne dry_run
```

#### 4.2 Rate Limiting

**Rule:** Max. N Enhancements pro Zeiteinheit, um Kosten zu kontrollieren.

**Limits:**
```python
RATE_LIMITS = {
    "per_course": 100,   # Max 100 Enhancements pro Kurs
    "per_hour": 50,      # Max 50 Enhancements pro Stunde
    "per_day": 500,      # Max 500 Enhancements pro Tag
}
```

**Implementation (Future):**
```python
# Check rate limits before enhancement
if get_enhancement_count(course_id) >= RATE_LIMITS["per_course"]:
    raise RateLimitError("Course enhancement limit exceeded")
```

#### 4.3 Token Budget

**Rule:** LLM-Calls haben ein Token-Budget pro Enhancement.

**Budgets:**
```python
TOKEN_BUDGETS = {
    EnhancementType.EXAMPLES: {
        "max_input_tokens": 2000,
        "max_output_tokens": 500,
    },
    EnhancementType.SUMMARIES: {
        "max_input_tokens": 4000,
        "max_output_tokens": 300,
    },
    EnhancementType.FLASHCARDS: {
        "max_input_tokens": 2000,
        "max_output_tokens": 1000,
    },
}
```

**Implementation (Future):**
```python
# Truncate input if too long
input_tokens = count_tokens(lesson.content_markdown)

if input_tokens > budget["max_input_tokens"]:
    truncated_input = truncate_to_tokens(
        lesson.content_markdown,
        budget["max_input_tokens"]
    )
```

#### 4.4 Timeout Protection

**Rule:** LLM-Calls haben ein Timeout.

**Timeouts:**
```python
LLM_TIMEOUTS = {
    EnhancementType.EXAMPLES: 30,    # 30 seconds
    EnhancementType.SUMMARIES: 20,   # 20 seconds
    EnhancementType.FLASHCARDS: 40,  # 40 seconds
}
```

**Implementation (Future):**
```python
import asyncio

try:
    enhanced = await asyncio.wait_for(
        llm_client.generate(prompt),
        timeout=LLM_TIMEOUTS[enhancement_type]
    )
except asyncio.TimeoutError:
    logger.error("LLM enhancement timed out, using fallback")
    enhanced = placeholder_enhancement(base_content)
```

### 5. Audit & Compliance Guardrails

**Ziel:** Vollständige Nachvollziehbarkeit aller Enhancements.

#### 5.1 Diff-Audit

**Rule:** Jedes Enhancement wird als Unified Diff gespeichert.

**Implementation:**
```python
# Generate unified diff
diff = difflib.unified_diff(
    base_content.splitlines(keepends=True),
    enhanced_content.splitlines(keepends=True),
    fromfile="base",
    tofile="enhanced",
    lineterm=""
)

unified_diff = "".join(diff)

# Compute diff hash (SHA-256)
diff_hash = hashlib.sha256(unified_diff.encode()).hexdigest()
```

**Storage:**
```
{course_id}/enhancements/enhancement_{timestamp}.json
{
  "enhancement_id": "enh_abc123",
  "lesson_id": "lesson_1",
  "enhancement_type": "examples",
  "base_content_hash": "sha256:...",
  "enhanced_content_hash": "sha256:...",
  "diff_hash": "sha256:...",
  "validated": true,
  "validation_passed": true,
  "timestamp": "2025-12-26T12:00:00Z"
}
```

#### 5.2 Actor Tracking

**Rule:** Jedes Enhancement wird einem Actor zugeordnet.

**Actors:**
- `system` – Automatisches Enhancement
- `user:{user_id}` – Manuelles Enhancement durch User
- `llm:{model}` – LLM-generiertes Enhancement

**Implementation:**
```python
enhancement = ContentEnhancement(
    enhancement_id="enh_123",
    actor="llm:gpt-4",
    actor_metadata={
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 500
    }
)
```

#### 5.3 Rollback Support

**Rule:** Jedes Enhancement kann rückgängig gemacht werden.

**Implementation:**
```python
# Rollback Enhancement
rollback = await service.rollback_enhancement(
    course_id="course_123",
    enhancement_id="enh_abc123",
    reason="Enhancement quality not satisfactory"
)

# Ergebnis: Base Content wiederhergestellt
```

---

## 🎯 LLM Prompt Engineering Guidelines

### Prompt Structure

**Best Practice:**
```python
ENHANCEMENT_PROMPT_TEMPLATE = """
You are a professional course content enhancer.

Original Content:
{base_content}

Task: {enhancement_type}

Guidelines:
- Do NOT change the structure (headings, lists, code blocks)
- Do NOT add more than 50% additional content
- Keep the tone consistent with the original
- Add practical examples where appropriate
- Ensure factual accuracy

Output:
[Enhanced content only, no explanations]
"""
```

### Context Window Management

**Strategy:**
```python
# 1. Prioritize most relevant context
context = {
    "lesson_title": lesson.title,
    "lesson_content": lesson.content_markdown[:2000],  # Truncate if too long
    "course_title": course.metadata.title,
    "target_audience": course.metadata.target_audiences,
}

# 2. Use structured prompts
prompt = construct_prompt(
    template=ENHANCEMENT_PROMPT_TEMPLATE,
    context=context,
    enhancement_type=enhancement_type
)

# 3. Validate token count
if count_tokens(prompt) > MAX_INPUT_TOKENS:
    prompt = truncate_prompt(prompt, MAX_INPUT_TOKENS)
```

### Output Parsing

**Robust Parsing:**
```python
# LLM Output often contains extra formatting
raw_output = llm_response.content

# Clean output
cleaned = clean_llm_output(raw_output)

# Validate structure
if not is_valid_markdown(cleaned):
    logger.warning("Invalid markdown in LLM output")
    cleaned = fallback_to_base_content(base_content)

return cleaned
```

---

## 🧪 Testing Guidelines

### Unit Tests

**Test Coverage:**
```python
# 1. Validation Tests
def test_max_length_validation():
    """Test that enhancements exceeding 50% length are rejected."""
    base = "Short content."
    enhanced = "Short content." + ("x" * 1000)  # Way too long

    validator = ContentValidator()
    passed, errors = validator.validate_enhancement(...)

    assert not passed
    assert "Enhanced content too long" in errors[0]


# 2. Structural Change Detection
def test_structural_changes_detection():
    """Test that added headings are detected."""
    base = "# Intro\nContent."
    enhanced = "# Intro\nContent.\n\n## New Section\nMore."

    validator = ContentValidator()
    assert validator._has_structural_changes(base, enhanced) == True


# 3. Diff Audit
def test_diff_audit():
    """Test that diff hash is deterministic."""
    base = "Content A"
    enhanced = "Content A\nEnhanced."

    auditor = DiffAuditor()
    diff, hash1, stats = auditor.audit_diff(base, enhanced)

    # Same input should produce same hash
    _, hash2, _ = auditor.audit_diff(base, enhanced)
    assert hash1 == hash2
```

### Integration Tests

**Test Scenarios:**
```python
# 1. End-to-End Enhancement Flow
async def test_enhancement_flow():
    """Test complete enhancement flow with validation."""
    request = EnhancementRequest(
        course_id="test_course",
        lesson_ids=["lesson_1"],
        enhancement_types=[EnhancementType.EXAMPLES],
        dry_run=False
    )

    result = await service.enhance_content(request, lessons)

    assert result.success
    assert result.validated_count > 0
    assert len(result.errors) == 0


# 2. Rollback Test
async def test_enhancement_rollback():
    """Test enhancement rollback."""
    # Enhance
    result = await service.enhance_content(request, lessons)

    # Rollback
    rollback = await service.rollback_enhancement(
        course_id="test_course",
        enhancement_id=result.enhancements[0].enhancement_id
    )

    assert rollback.success
```

---

## 📊 Monitoring & Alerting

### Metrics

**Track:**
```python
ENHANCEMENT_METRICS = {
    "total_enhancements": Counter,
    "validation_failures": Counter,
    "avg_enhancement_time": Histogram,
    "llm_token_usage": Counter,
    "llm_cost_usd": Gauge,
}
```

### Alerts

**Alert Rules:**
```yaml
alerts:
  - name: HighValidationFailureRate
    condition: validation_failure_rate > 0.2  # > 20%
    action: notify_admin

  - name: LLMCostExceedsThreshold
    condition: daily_llm_cost_usd > 100
    action: notify_billing

  - name: LongEnhancementTime
    condition: avg_enhancement_time_seconds > 60
    action: investigate_performance
```

---

## 🔮 Future Enhancements

1. **Advanced Tone Analysis**
   - LLM-based tone detection
   - Multi-dimensional tone matching (formality, technicality, friendliness)

2. **Fact-Checking Integration**
   - External fact-checking APIs
   - Citation verification
   - Source credibility scoring

3. **A/B Testing**
   - Generate multiple enhancement variants
   - User preference tracking
   - Automatic selection of best variant

4. **Feedback Loop**
   - User ratings for enhancements
   - Model fine-tuning based on feedback
   - Continuous improvement

---

## 📋 Checklist für LLM-Integration

Vor Go-Live mit echten LLM-Calls:

- [ ] Alle Validators implementiert und getestet
- [ ] Rate Limiting funktionsfähig
- [ ] Token Budgets definiert und enforced
- [ ] Timeout Protection aktiv
- [ ] Diff-Audit vollständig
- [ ] Rollback-Funktionalität getestet
- [ ] Security Guardrails aktiv (No Code Execution, No PII)
- [ ] Monitoring & Alerting eingerichtet
- [ ] Cost Tracking implementiert
- [ ] Dry-Run Mode getestet
- [ ] HITL-Approval-Gates funktionsfähig
- [ ] Prompt Engineering finalisiert
- [ ] LLM Model Selection (GPT-4, Claude, etc.)
- [ ] API Keys sicher gespeichert (nicht in Code!)
- [ ] Fallback-Strategie bei LLM-Ausfall definiert
- [ ] Dokumentation vollständig

---

**Version:** 1.0.0
**Date:** 2025-12-26
**Status:** ✅ Ready for LLM Integration
