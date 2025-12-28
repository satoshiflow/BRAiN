# Course Factory Events Documentation

**Module:** course_factory
**Version:** 1.0.0 (EventStream Migration - Sprint 1)
**Last Updated:** 2025-12-28

---

## Events Published by course_factory

### 1. `course.generation.requested`

**EventType:** `COURSE_GENERATION_REQUESTED`

**When:** Course generation starts (after request validation, before any generation)

**Producer:** `CourseFactoryService.generate_course()` (service.py:87)

**Payload:**
```json
{
  "course_id": "string (UUID)",
  "title": "string",
  "description": "string",
  "language": "string (de|en|fr|es)",
  "target_audiences": ["string (private_individuals|employees|...)"],
  "tenant_id": "string",
  "dry_run": "boolean",
  "full_lessons_count": "integer"
}
```

**Consumers:**
- Analytics Service (track course requests)
- Monitoring (generation start tracking)

**Meta:**
```json
{
  "schema_version": 1,
  "producer": "course_factory_service",
  "source_module": "course_factory"
}
```

---

### 2. `course.outline.created`

**EventType:** `COURSE_OUTLINE_CREATED`

**When:** Course outline successfully generated

**Producer:** `CourseFactoryService.generate_course()` (after outline_gen.generate_outline())

**Payload:**
```json
{
  "course_id": "string (UUID)",
  "modules_count": "integer (4-6)",
  "total_lessons": "integer (12-30)",
  "template_id": "string (banking_alternatives|custom)"
}
```

**Consumers:**
- course_distribution (prepare for distribution)
- Analytics (track outline complexity)

**Meta:**
```json
{
  "schema_version": 1,
  "producer": "course_factory_service",
  "source_module": "course_factory"
}
```

---

### 3. `course.lesson.generated`

**EventType:** `COURSE_LESSON_GENERATED`

**When:** Each full lesson content generated (loop in generate_course)

**Producer:** `CourseFactoryService.generate_course()` (lesson loop)

**Payload:**
```json
{
  "course_id": "string (UUID)",
  "lesson_id": "string (UUID)",
  "lesson_title": "string",
  "module_id": "string (UUID)",
  "content_length": "integer (characters)",
  "lesson_index": "integer (1-based)"
}
```

**Consumers:**
- Progress Tracking (lesson-by-lesson)
- Content Analytics

**Meta:**
```json
{
  "schema_version": 1,
  "producer": "course_factory_service",
  "source_module": "course_factory"
}
```

**Note:** This event is published for EACH full lesson (not placeholders)

---

### 4. `course.quiz.created`

**EventType:** `COURSE_QUIZ_CREATED`

**When:** Quiz successfully generated (if generate_quiz=true)

**Producer:** `CourseFactoryService.generate_course()` (after quiz_gen.generate_quiz())

**Payload:**
```json
{
  "course_id": "string (UUID)",
  "quiz_id": "string (UUID)",
  "question_count": "integer (10-15)",
  "question_ids": ["string (UUID)", "..."]
}
```

**Consumers:**
- Assessment Service (quiz availability)
- Analytics (quiz complexity)

**Meta:**
```json
{
  "schema_version": 1,
  "producer": "course_factory_service",
  "source_module": "course_factory"
}
```

---

### 5. `course.landing_page.created`

**EventType:** `COURSE_LANDING_PAGE_CREATED`

**When:** Landing page successfully generated (if generate_landing_page=true)

**Producer:** `CourseFactoryService.generate_course()` (after landing_gen.generate_landing_page())

**Payload:**
```json
{
  "course_id": "string (UUID)",
  "landing_page_id": "string (UUID)",
  "sections_count": "integer",
  "has_hero": "boolean",
  "has_pricing": "boolean"
}
```

**Consumers:**
- Marketing Service (landing page ready)
- SEO Service (indexing)

**Meta:**
```json
{
  "schema_version": 1,
  "producer": "course_factory_service",
  "source_module": "course_factory"
}
```

---

### 6. `course.generation.completed`

**EventType:** `COURSE_GENERATION_COMPLETED`

**When:** ENTIRE course generation process successful (after all artifacts saved)

**Producer:** `CourseFactoryService.generate_course()` (end of try block)

**Payload:**
```json
{
  "course_id": "string (UUID)",
  "total_modules": "integer",
  "total_lessons": "integer",
  "full_lessons_generated": "integer",
  "quiz_questions_count": "integer",
  "evidence_pack_path": "string (filesystem path)",
  "execution_time_seconds": "float",
  "deployed": "boolean",
  "staging_url": "string (URL, nullable)"
}
```

**Consumers:** **CRITICAL**
- course_distribution (trigger distribution workflow)
- Analytics (completion metrics)
- Notification Service (notify user)
- Audit Log (evidence pack reference)

**Meta:**
```json
{
  "schema_version": 1,
  "producer": "course_factory_service",
  "source_module": "course_factory"
}
```

**Idempotency:** Safe to replay (course_id already exists, no duplicate artifacts)

---

### 7. `course.generation.failed`

**EventType:** `COURSE_GENERATION_FAILED`

**When:** Course generation fails (exception in generate_course)

**Producer:** `CourseFactoryService.generate_course()` (except block)

**Payload:**
```json
{
  "course_id": "string (UUID or empty if early failure)",
  "title": "string (requested title)",
  "error_message": "string",
  "error_type": "string (exception class)",
  "execution_time_seconds": "float"
}
```

**Consumers:**
- Alerting Service (notify ops team)
- Error Tracking (Sentry, etc.)
- Analytics (failure rate)

**Meta:**
```json
{
  "schema_version": 1,
  "producer": "course_factory_service",
  "source_module": "course_factory"
}
```

**Severity:** ERROR

---

### 8. `course.workflow.transitioned`

**EventType:** `COURSE_WORKFLOW_TRANSITIONED`

**When:** Workflow state changes (draft → review → publish_ready → published)

**Producer:** `WorkflowStateMachine.transition()` (workflow.py:85)

**Payload:**
```json
{
  "course_id": "string (UUID)",
  "from_state": "string (DRAFT|REVIEW|PUBLISH_READY|PUBLISHED|ARCHIVED)",
  "to_state": "string",
  "transitioned_by": "string (user_id or system)",
  "requires_approval": "boolean",
  "approval_token": "string (nullable)"
}
```

**Consumers:**
- Notification Service (notify stakeholders)
- HITL Dashboard (approval requests)
- Audit Log (state transition history)

**Meta:**
```json
{
  "schema_version": 1,
  "producer": "workflow_state_machine",
  "source_module": "course_factory"
}
```

---

### 9. `course.deployed.staging`

**EventType:** `COURSE_DEPLOYED_STAGING`

**When:** Course successfully deployed to staging environment

**Producer:** `CourseFactoryService._deploy_to_staging()` (service.py:168)

**Payload:**
```json
{
  "course_id": "string (UUID)",
  "staging_url": "string (URL)",
  "staging_domain": "string",
  "deployed_at": "string (ISO-8601 timestamp)"
}
```

**Consumers:**
- course_distribution (staging deployment complete)
- WebGenesis (preview ready)
- QA Team (testing notification)

**Meta:**
```json
{
  "schema_version": 1,
  "producer": "course_factory_service",
  "source_module": "course_factory"
}
```

---

## Events Consumed by course_factory

**None** (course_factory is producer-only in Sprint 1)

**Future Consumers (Sprint 2+):**
- `payment.completed` → Unlock course access
- `user.enrolled` → Initialize progress tracking

---

## Event Flow Diagram

```
[User Request]
      ↓
course.generation.requested
      ↓
course.outline.created
      ↓
course.lesson.generated (x N lessons)
      ↓
course.quiz.created (if requested)
      ↓
course.landing_page.created (if requested)
      ↓
course.deployed.staging (if deploy_to_staging=true)
      ↓
course.generation.completed
      ↓
[course_distribution consumes]
```

**Error Path:**
```
[Exception in generate_course]
      ↓
course.generation.failed
      ↓
[Alerting Service]
```

**Workflow Path:**
```
course.generation.completed
      ↓
course.workflow.transitioned (DRAFT → REVIEW)
      ↓
[HITL Approval]
      ↓
course.workflow.transitioned (REVIEW → PUBLISH_READY)
      ↓
course.workflow.transitioned (PUBLISH_READY → PUBLISHED)
```

---

## Payload Size Constraints

**Rule:** Keep payloads small (< 1 KB per event)

**What to EXCLUDE from payload:**
- ❌ Full lesson content (Markdown) → too large, use `lesson_id` reference
- ❌ Full outline JSON → too large, use `course_id` reference
- ❌ Quiz questions full text → use `quiz_id` reference
- ❌ Landing page HTML → use `landing_page_id` reference

**What to INCLUDE:**
- ✅ IDs (course_id, lesson_id, user_id)
- ✅ Counts (lessons_count, modules_count)
- ✅ Status flags (deployed, dry_run)
- ✅ Metadata (execution_time, template_id)

---

## Sensitive Data Policy

**Never include in payloads:**
- ❌ User PII (email, name, address)
- ❌ Payment information (credit card, bank account)
- ❌ API Keys (LLM API keys, WebGenesis keys)
- ❌ Internal IDs (database primary keys) → use UUIDs

**Always use:**
- ✅ User IDs (not emails)
- ✅ Course UUIDs (not DB IDs)
- ✅ Tenant IDs (for multi-tenancy)

---

## Idempotency Notes

**Safe to replay:**
- ✅ `course.generation.completed` (course_id already exists, artifacts not duplicated)
- ✅ `course.outline.created` (outline already saved)
- ✅ `course.deployed.staging` (deployment is idempotent)

**Replay protection:**
- ✅ EventConsumer uses `stream_message_id` as PRIMARY dedup key
- ✅ `event.id` is SECONDARY (audit/trace only)

---

## Testing Events

**Test Event Publishing:**
```python
# backend/tests/test_course_factory_events.py

async def test_generate_course_publishes_events(event_stream_mock):
    service = CourseFactoryService()
    service.event_stream = event_stream_mock

    request = CourseGenerationRequest(
        title="Test Course",
        description="Test",
        language="de",
        target_audiences=["private_individuals"],
        dry_run=False
    )

    result = await service.generate_course(request)

    # Verify events published
    assert event_stream_mock.publish_event.call_count >= 3  # requested, outline, completed
```

---

## Migration Notes

**Migrated:** 2025-12-28
**From:** No EventStream (synchronous orchestration)
**To:** EventStream-based (Charter v1.0 compliant)

**Breaking Changes:**
- None (events are additive)

**Backward Compatibility:**
- ✅ Fully backward compatible (events added, nothing removed)

---

**Last Updated:** 2025-12-28
**Owner:** BRAiN Core Team
**Status:** ✅ Event Design Complete (Phase 1)
