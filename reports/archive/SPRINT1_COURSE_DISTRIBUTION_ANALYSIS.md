# Sprint 1 - Phase 0 Analysis: course_distribution

**Module:** `backend/app/modules/course_distribution`
**Analyzed:** 2025-12-28
**Analyst:** Claude (Sprint 1 Migration)

---

## 📋 Module Purpose

**course_distribution** manages the public-facing distribution of generated courses:

- **Distribution Management**: Create, update, delete course distributions
- **Publishing Workflow**: Control course visibility (PRIVATE ↔ PUBLIC)
- **Micro-Niche Variants**: Clone courses for different target audiences
- **Public API**: Serve course catalog, details, outlines (read-only)
- **Aggregated Tracking**: Log views and enrollment clicks (no PII)
- **SEO & CTA**: Manage search optimization and calls-to-action
- **Version Management**: Bump course versions

**Current Status:** Sprint 15 (Distribution & Growth Layer)

---

## 🔍 Key Business State Changes

### 1. Distribution Lifecycle

| Operation | Method | State Change |
|-----------|--------|--------------|
| Create | `create_distribution()` | Distribution created with PRIVATE visibility |
| Update | `update_distribution()` | Distribution metadata modified |
| Delete | `delete_distribution()` | Distribution removed from catalog |
| Publish | `publish_distribution()` | Visibility: PRIVATE → PUBLIC |
| Unpublish | `unpublish_distribution()` | Visibility: PUBLIC → PRIVATE |

### 2. Tracking (Aggregated)

| Operation | Method | State Change |
|-----------|--------|--------------|
| View | `log_view()` | View count incremented (no user PII) |
| Enrollment Click | `track_enrollment_click()` | Enrollment click count incremented |

### 3. Micro-Niche Derivation

| Operation | Method | State Change |
|-----------|--------|--------------|
| Create Variant | `create_micro_niche_variant()` | Child distribution created from parent |
| Get Variants | `get_micro_niche_variants()` | Read-only (no state change) |

### 4. Version Management

| Operation | Method | State Change |
|-----------|--------|--------------|
| Bump Version | `bump_version()` | Version string incremented (e.g., v1 → v2) |

---

## 📡 Event Design (Phase 0 → Phase 1)

### Events to Publish (Producer Role)

| Event Type | When Published | Critical? | Consumers |
|------------|----------------|-----------|-----------|
| `distribution.created` | Distribution created | Yes | Analytics, Audit |
| `distribution.updated` | Distribution metadata changed | No | Analytics, Audit |
| `distribution.deleted` | Distribution removed | Yes | Cache Invalidation, Audit |
| `distribution.published` | Course made public | **CRITICAL** | SEO Indexer, Marketing, Notifications |
| `distribution.unpublished` | Course made private | Yes | SEO Indexer, Cache Invalidation |
| `distribution.viewed` | Course page viewed (aggregated) | No | Analytics, Recommendations |
| `distribution.enrollment_clicked` | Enrollment CTA clicked | Yes | Analytics, Conversion Tracking |
| `distribution.micro_niche_created` | Micro-niche variant created | Yes | Analytics, Parent Course Stats |
| `distribution.version_bumped` | Course version incremented | Yes | Changelog, Notifications |

**Total Events (Producer):** 9

### Events to Consume (Consumer Role)

**CRITICAL INTEGRATION POINT:**

The module has TODOs indicating it SHOULD integrate with CourseFactory:

```python
# distribution_service.py:295
# TODO: Integrate with CourseFactory to get actual course structure

# distribution_service.py:320
# TODO: Integrate with actual CourseFactory service.
```

**Events to Consume:**

| Event Type | Purpose | Action on Receipt |
|------------|---------|-------------------|
| `course.generation.completed` | **CRITICAL** - Course ready for distribution | Auto-create distribution entry, prepare for publishing |
| `course.deployed.staging` | Staging deployment complete | Update course availability status |

**Consumer Implementation:**
- **EventConsumer** class required
- **PostgreSQL dedup table** required
- **Idempotency** via `stream_message_id`

---

## 🏗️ Module Architecture

```
course_distribution/
├── distribution_models.py      # Pydantic models (CourseDistribution, SEO, CTA)
├── distribution_service.py     # Business logic (11 methods)
├── distribution_router.py      # FastAPI endpoints (10 endpoints)
├── distribution_storage.py     # JSON file storage
├── template_renderer.py        # Jinja2 template rendering
└── templates/                  # HTML templates for course pages
```

**Storage:** JSON files (no PostgreSQL yet)
**Dependencies:** No direct cross-module imports (good!)

---

## 🚨 Legacy Code Patterns

### ❌ Cross-Module Synchronous Calls

**Status:** ✅ **NONE FOUND**

No direct imports from `course_factory` or `ir_governance` detected.

### ⚠️ TODO Integration Points

**Found 2 critical TODOs:**

1. **Line 295:** `# TODO: Integrate with CourseFactory to get actual course structure`
2. **Line 320:** `# TODO: Integrate with actual CourseFactory service.`

**Migration Strategy:**
- These TODOs will be resolved via EventStream consumer
- NO legacy code to remove (integration never existed)
- Consumer will listen for `course.generation.completed` and auto-create distributions

---

## 🎯 Migration Role Determination

**Role:** **PRODUCER + CONSUMER**

**Producer:**
- Publishes 9 event types for distribution state changes

**Consumer:**
- Listens for `course.generation.completed` from course_factory
- Listens for `course.deployed.staging` from course_factory
- Creates distribution entry automatically when course is ready

---

## 📦 Phase 1 Requirements

### EventTypes to Add (event_stream.py)

```python
# Course Distribution Events (Sprint 1)
DISTRIBUTION_CREATED = "distribution.created"
DISTRIBUTION_UPDATED = "distribution.updated"
DISTRIBUTION_DELETED = "distribution.deleted"
DISTRIBUTION_PUBLISHED = "distribution.published"
DISTRIBUTION_UNPUBLISHED = "distribution.unpublished"
DISTRIBUTION_VIEWED = "distribution.viewed"
DISTRIBUTION_ENROLLMENT_CLICKED = "distribution.enrollment_clicked"
DISTRIBUTION_MICRO_NICHE_CREATED = "distribution.micro_niche_created"
DISTRIBUTION_VERSION_BUMPED = "distribution.version_bumped"
```

### Files to Create

1. **`EVENTS.md`** - Complete event specification (9 producer events + 2 consumer events)
2. **`README.md`** - Module documentation (doesn't exist yet!)

### Files to Modify

1. **`distribution_service.py`** - Add EventStream injection, 9 publisher methods, 1 consumer class
2. **`distribution_router.py`** - Update dependency injection
3. **`event_stream.py`** - Add 9 new EventTypes

---

## 🧪 Test Requirements (Phase 4)

**Mandatory Tests (4):**

1. ✅ Event wird publiziert (Test producer: distribution.created, etc.)
2. ✅ Consumer verarbeitet Event (Test consumer: course.generation.completed)
3. ✅ Replay derselben Message → keine Doppelwirkung (Idempotency test)
4. ✅ Fehlerfall korrekt behandelt (Permanent vs Transient errors)

**Additional Tests:**
- Visibility change events (publish/unpublish)
- Micro-niche derivation events
- View tracking events (aggregated)
- Enrollment click tracking

**Test File:** `backend/tests/test_course_distribution_events.py`

---

## 📊 Complexity Assessment

**Phase 2 (Producer):** Medium
- 9 events to publish
- 11 service methods to instrument
- Standard `_publish_event_safe()` pattern

**Phase 3 (Consumer):** Medium-High
- **NEW:** EventConsumer class required (first consumer in Sprint 1!)
- PostgreSQL dedup table setup
- Idempotency logic implementation
- Integration with course_factory events

**Phase 4 (Tests):** Medium
- Producer tests: Standard (similar to course_factory)
- Consumer tests: **NEW** - replay/idempotency tests required

**Overall Complexity:** **Medium-High** (due to consumer implementation)

---

## ✅ Phase 0 Completion Checklist

- [x] Module purpose documented
- [x] All business state changes identified (9 producer events)
- [x] Consumer role identified (2 events to consume)
- [x] Legacy code patterns checked (none found)
- [x] Event list finalized (9 + 2)
- [x] Architecture documented
- [x] Test requirements outlined
- [x] Complexity assessed

---

## 🚀 Next Steps

**Phase 1:** Event Design
- Create `EVENTS.md` with 11 event specifications (9 producer + 2 consumer)
- Add 9 EventTypes to `event_stream.py`
- Design consumer event handlers for `course.generation.completed`

**Critical Decision Point:**
- consumer implementation is NEW for Sprint 1
- May require EventConsumer base class creation
- Coordinate with course_factory event publishing

---

**Analysis Status:** ✅ **COMPLETE**
**Proceed to Phase 1:** YES
