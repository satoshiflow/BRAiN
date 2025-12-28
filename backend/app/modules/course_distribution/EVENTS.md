# Course Distribution - Event Specifications

**Module:** `backend/app/modules/course_distribution`
**Version:** 1.0.0 (EventStream Migration - Sprint 1)
**Last Updated:** 2025-12-28
**Charter Compliance:** v1.0 ✅

---

## 📋 Overview

Course Distribution publishes **9 event types** for distribution lifecycle, publishing, tracking, micro-niche variants, and versioning. It also **consumes 2 event types** from CourseFactory to automatically create distributions when courses are ready.

**Role:** PRODUCER + CONSUMER

---

## 📤 Producer Events (9 Total)

### 1. `distribution.created`

**When Published:** New distribution created

**Criticality:** High (downstream services need to index new distributions)

**Payload:**
```json
{
  "distribution_id": "dist_123abc",
  "course_id": "course_456def",
  "slug": "alternativen-banken-privatpersonen",
  "language": "de",
  "title": "Alternativen zu Banken & Sparkassen",
  "target_group": ["private_individuals"],
  "visibility": "private",
  "version": "v1",
  "derived_from": null,
  "created_at": "2025-12-28T10:30:00Z"
}
```

**Envelope (Charter v1.0):**
```json
{
  "id": "evt_uuid_v4",
  "type": "distribution.created",
  "timestamp": "2025-12-28T10:30:00.123456Z",
  "payload": { /* above */ },
  "meta": {
    "schema_version": "1.0",
    "producer": "course_distribution",
    "source_module": "course_distribution",
    "tenant_id": "brain_prod",
    "correlation_id": "req_123",
    "causation_id": null
  },
  "target": null
}
```

**Consumers:**
- Analytics Service (track distribution growth)
- Audit Log (compliance)

---

### 2. `distribution.updated`

**When Published:** Distribution metadata modified

**Criticality:** Medium

**Payload:**
```json
{
  "distribution_id": "dist_123abc",
  "updated_fields": ["title", "description", "seo"],
  "old_values": {
    "title": "Old Title"
  },
  "new_values": {
    "title": "New Title"
  },
  "updated_at": "2025-12-28T11:00:00Z"
}
```

**Consumers:**
- Cache Invalidation Service
- Audit Log

---

### 3. `distribution.deleted`

**When Published:** Distribution removed from catalog

**Criticality:** High (cascading deletes required)

**Payload:**
```json
{
  "distribution_id": "dist_123abc",
  "slug": "alternativen-banken-privatpersonen",
  "course_id": "course_456def",
  "deleted_at": "2025-12-28T12:00:00Z",
  "deleted_by": "admin_user_id"
}
```

**Consumers:**
- Cache Invalidation Service (remove from cache)
- SEO Indexer (remove from search index)
- Analytics Service (mark as deleted in reports)

---

### 4. `distribution.published` ⚠️ CRITICAL

**When Published:** Distribution visibility changed: PRIVATE → PUBLIC

**Criticality:** **CRITICAL** (triggers SEO indexing, notifications, marketing)

**Payload:**
```json
{
  "distribution_id": "dist_123abc",
  "slug": "alternativen-banken-privatpersonen",
  "course_id": "course_456def",
  "title": "Alternativen zu Banken & Sparkassen",
  "language": "de",
  "target_group": ["private_individuals"],
  "seo": {
    "meta_title": "Die 7 besten Alternativen zu klassischen Banken 2025",
    "meta_description": "Vergleich: Neobanken, FinTechs & Krypto-Wallets...",
    "meta_keywords": ["neobanken", "fintech", "alternativen"]
  },
  "published_at": "2025-12-28T13:00:00Z"
}
```

**Consumers:**
- **SEO Indexer** (add to Google/Bing index)
- **Marketing Service** (send launch notifications)
- **Notification Service** (notify subscribers)
- **Analytics Service** (track publish event)

---

### 5. `distribution.unpublished`

**When Published:** Distribution visibility changed: PUBLIC → PRIVATE

**Criticality:** High (must remove from public access)

**Payload:**
```json
{
  "distribution_id": "dist_123abc",
  "slug": "alternativen-banken-privatpersonen",
  "unpublished_at": "2025-12-28T14:00:00Z",
  "reason": "content_revision_required"
}
```

**Consumers:**
- SEO Indexer (remove from index)
- Cache Invalidation Service (purge public cache)

---

### 6. `distribution.viewed`

**When Published:** Course page viewed (aggregated, no PII)

**Criticality:** Low (analytics only)

**Payload:**
```json
{
  "distribution_id": "dist_123abc",
  "slug": "alternativen-banken-privatpersonen",
  "view_count": 127,
  "viewed_at": "2025-12-28T15:00:00Z",
  "referrer_category": "organic_search"
}
```

**Note:** NO user_id, IP, or session info (aggregated tracking only)

**Consumers:**
- Analytics Service (view metrics)
- Recommendation Engine (popularity scoring)

---

### 7. `distribution.enrollment_clicked`

**When Published:** Enrollment CTA button clicked

**Criticality:** Medium (conversion tracking)

**Payload:**
```json
{
  "distribution_id": "dist_123abc",
  "slug": "alternativen-banken-privatpersonen",
  "enrollment_count": 15,
  "clicked_at": "2025-12-28T16:00:00Z",
  "cta_type": "primary_button"
}
```

**Consumers:**
- Analytics Service (conversion funnel)
- A/B Testing Service (CTA performance)

---

### 8. `distribution.micro_niche_created`

**When Published:** Micro-niche variant derived from parent course

**Criticality:** Medium

**Payload:**
```json
{
  "child_distribution_id": "dist_789xyz",
  "parent_distribution_id": "dist_123abc",
  "parent_slug": "alternativen-banken",
  "child_slug": "alternativen-banken-angestellte",
  "target_group_override": ["employees"],
  "title_override": "Finanzalternativen für Angestellte",
  "created_at": "2025-12-28T17:00:00Z"
}
```

**Consumers:**
- Analytics Service (track variant performance vs parent)
- Parent Course Stats Aggregator

---

### 9. `distribution.version_bumped`

**When Published:** Course version incremented

**Criticality:** Medium

**Payload:**
```json
{
  "distribution_id": "dist_123abc",
  "slug": "alternativen-banken-privatpersonen",
  "old_version": "v1",
  "new_version": "v2",
  "bumped_at": "2025-12-28T18:00:00Z",
  "changelog": "Added new lesson on crypto wallets"
}
```

**Consumers:**
- Changelog Service (version history)
- Notification Service (notify enrolled users of updates)

---

## 📥 Consumer Events (2 Total)

### 1. `course.generation.completed` ⚠️ CRITICAL

**Source:** CourseFactory (`course_factory` module)

**Purpose:** Automatically create distribution entry when course generation succeeds

**Trigger:** Course generation completed successfully in CourseFactory

**Idempotency:** Via `stream_message_id` (PostgreSQL dedup table)

**Expected Payload:**
```json
{
  "course_id": "course_456def",
  "tenant_id": "brain_prod",
  "title": "Alternativen zu Banken & Sparkassen",
  "description": "Ein praxisnaher Grundlagenkurs...",
  "language": "de",
  "target_audiences": ["private_individuals"],
  "total_lessons": 12,
  "completed_at": "2025-12-28T09:00:00Z"
}
```

**Consumer Action:**
```python
async def handle_course_generation_completed(self, event: Event):
    """
    Auto-create distribution entry when course is ready.

    Deduplication: Check stream_message_id in PostgreSQL dedup table
    """
    # 1. Check idempotency
    if await self.is_duplicate(event.meta.get("stream_message_id")):
        logger.info(f"Duplicate event {event.id}, skipping")
        return  # Already processed

    # 2. Create distribution
    payload = event.payload
    distribution = await self.service.create_distribution(
        course_id=payload["course_id"],
        slug=generate_slug(payload["title"]),  # Auto-generate slug
        language=payload["language"],
        title=payload["title"],
        description=payload["description"],
        target_group=payload["target_audiences"],
        seo=generate_default_seo(payload),  # Auto-generate SEO
        cta=generate_default_cta(),  # Default CTA
        version="v1",
        derived_from=None,
    )

    # 3. Mark as processed
    await self.mark_processed(event.meta.get("stream_message_id"))

    logger.info(f"Auto-created distribution {distribution.distribution_id} for course {payload['course_id']}")
```

**Error Handling:**
- **Permanent errors** (invalid payload): ACK + log error
- **Transient errors** (DB unavailable): NO ACK + retry

---

### 2. `course.deployed.staging`

**Source:** CourseFactory (`course_factory` module)

**Purpose:** Update distribution availability status when course is deployed to staging

**Trigger:** Course deployed to staging environment in CourseFactory

**Idempotency:** Via `stream_message_id` (PostgreSQL dedup table)

**Expected Payload:**
```json
{
  "course_id": "course_456def",
  "staging_url": "https://staging.brain.falklabs.de/courses/course_456def",
  "deployed_at": "2025-12-28T09:30:00Z"
}
```

**Consumer Action:**
```python
async def handle_course_deployed_staging(self, event: Event):
    """
    Update distribution with staging URL.

    Deduplication: Check stream_message_id in PostgreSQL dedup table
    """
    # 1. Check idempotency
    if await self.is_duplicate(event.meta.get("stream_message_id")):
        logger.info(f"Duplicate event {event.id}, skipping")
        return

    # 2. Find distribution by course_id
    payload = event.payload
    distributions = await self.service.get_distributions_by_course_id(payload["course_id"])

    # 3. Update all distributions for this course
    for dist in distributions:
        await self.service.update_distribution(
            distribution_id=dist.distribution_id,
            staging_url=payload["staging_url"],
            staging_deployed_at=payload["deployed_at"],
        )

    # 4. Mark as processed
    await self.mark_processed(event.meta.get("stream_message_id"))

    logger.info(f"Updated {len(distributions)} distributions for course {payload['course_id']}")
```

---

## 🔧 Implementation Guide

### Producer Integration (service.py)

```python
from backend.mission_control_core.core.event_stream import EventStream, Event, EventType
from datetime import datetime
import uuid

class DistributionService:
    def __init__(self, event_stream: Optional[EventStream] = None):
        self.event_stream = event_stream

    async def _publish_event_safe(self, event: Event) -> None:
        """Publish event with error handling (non-blocking)."""
        if self.event_stream is None:
            logger.debug("[Distribution] EventStream not available")
            return
        try:
            await self.event_stream.publish_event(event)
            logger.info(f"[Distribution] Event published: {event.type.value}")
        except Exception as e:
            logger.error(f"[Distribution] Event publish failed: {event.type.value}", exc_info=True)
            # DO NOT raise - business logic must continue

    async def create_distribution(self, ...) -> CourseDistribution:
        # ... business logic ...

        # Publish event
        await self._publish_event_safe(Event(
            id=str(uuid.uuid4()),
            type=EventType.DISTRIBUTION_CREATED,
            timestamp=datetime.utcnow().isoformat() + "Z",
            payload={
                "distribution_id": distribution.distribution_id,
                "course_id": distribution.course_id,
                "slug": distribution.slug,
                # ... full payload ...
            },
            meta={
                "schema_version": "1.0",
                "producer": "course_distribution",
                "source_module": "course_distribution",
            },
            target=None,  # Broadcast
        ))

        return distribution
```

### Consumer Integration (NEW)

**File:** `backend/app/modules/course_distribution/event_consumer.py`

```python
from backend.mission_control_core.core.event_stream import EventStream, Event, EventType
from loguru import logger

class DistributionEventConsumer:
    """
    EventConsumer for course_distribution module.

    Consumes:
    - course.generation.completed (auto-create distribution)
    - course.deployed.staging (update staging URL)
    """

    def __init__(self, event_stream: EventStream, service: DistributionService):
        self.event_stream = event_stream
        self.service = service
        self.consumer_id = "distribution_consumer"

    async def start(self):
        """Start consuming events."""
        await self.event_stream.subscribe(
            EventType.COURSE_GENERATION_COMPLETED,
            self.handle_course_generation_completed,
            consumer_id=self.consumer_id,
        )
        await self.event_stream.subscribe(
            EventType.COURSE_DEPLOYED_STAGING,
            self.handle_course_deployed_staging,
            consumer_id=self.consumer_id,
        )
        logger.info("[DistributionConsumer] Started consuming events")

    async def handle_course_generation_completed(self, event: Event):
        """Auto-create distribution when course is ready."""
        # Implementation from above
        pass

    async def handle_course_deployed_staging(self, event: Event):
        """Update distribution with staging URL."""
        # Implementation from above
        pass

    async def is_duplicate(self, stream_message_id: str) -> bool:
        """Check if event already processed (PostgreSQL dedup table)."""
        # Query: SELECT EXISTS(SELECT 1 FROM event_dedup WHERE stream_message_id = ?)
        pass

    async def mark_processed(self, stream_message_id: str):
        """Mark event as processed (PostgreSQL dedup table)."""
        # INSERT INTO event_dedup (stream_message_id, processed_at) VALUES (?, NOW())
        pass
```

---

## 🧪 Testing Requirements

### Producer Tests (9 events)

1. ✅ `distribution.created` published on create_distribution()
2. ✅ `distribution.updated` published on update_distribution()
3. ✅ `distribution.deleted` published on delete_distribution()
4. ✅ `distribution.published` published on publish_distribution()
5. ✅ `distribution.unpublished` published on unpublish_distribution()
6. ✅ `distribution.viewed` published on log_view()
7. ✅ `distribution.enrollment_clicked` published on track_enrollment_click()
8. ✅ `distribution.micro_niche_created` published on create_micro_niche_variant()
9. ✅ `distribution.version_bumped` published on bump_version()

### Consumer Tests (NEW - 2 events)

1. ✅ `course.generation.completed` → distribution auto-created
2. ✅ `course.deployed.staging` → distribution updated with staging URL
3. ✅ Replay same event → NO duplicate distribution (idempotency)
4. ✅ Invalid payload → ACK + error logged (permanent error)
5. ✅ DB unavailable → NO ACK + retry (transient error)

---

## 📊 Event Flow Diagram

```
CourseFactory                    EventStream                    Distribution
┌─────────────┐                 ┌──────────┐                   ┌──────────────┐
│ Generate    │                 │          │                   │              │
│ Course      │─────────────────>│ Publish  │                   │              │
│             │ course.generation│          │                   │              │
│             │    .completed    │          │────────────────────>│ Consume     │
└─────────────┘                 │          │                   │ → Create    │
                                │          │                   │   Dist      │
                                │          │                   └──────┬───────┘
                                │          │                          │
                                │          │<──────────────────────────┘
                                │          │   distribution.created
                                │          │
                                │          │────────> Analytics
                                │          │────────> SEO Indexer
                                └──────────┘────────> Audit Log
```

---

## ✅ Phase 1 Checklist

- [x] 9 EventTypes added to event_stream.py
- [x] All producer event payloads specified
- [x] All consumer event handlers designed
- [x] Idempotency strategy documented (stream_message_id + PostgreSQL)
- [x] Error handling strategy defined (permanent vs transient)
- [x] Testing requirements outlined
- [x] Implementation code samples provided

---

**Status:** ✅ **COMPLETE**
**Next Phase:** Phase 2 (Producer Implementation)
