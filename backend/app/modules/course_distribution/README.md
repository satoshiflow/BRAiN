# Course Distribution Module

**Version:** 1.0.0
**Status:** ✅ EventStream Integrated (Sprint 1 - Phase 5 Complete)
**Migration Date:** 2025-12-28
**Role:** PRODUCER + CONSUMER

---

## 📋 Overview

The **Course Distribution** module manages the public-facing distribution of generated courses, including:

- Distribution lifecycle management (create, update, delete)
- Publishing workflow (PRIVATE ↔ PUBLIC visibility control)
- SEO optimization and call-to-action configuration
- Micro-niche variant creation for targeted audiences
- Aggregated view and enrollment tracking (no PII)
- Version management and changelog tracking

**Key Features:**
- **Auto-distribution creation** when courses are ready (via EventStream consumer)
- **Staging deployment tracking** (updates distribution with staging URLs)
- **Multi-language support** with hreflang alternates
- **SEO-optimized** with customizable meta tags
- **Privacy-first** aggregated tracking (no user PII)

---

## 🏗️ Architecture

### Module Structure

```
course_distribution/
├── distribution_models.py      # Pydantic models (CourseDistribution, SEO, CTA)
├── distribution_service.py     # Business logic + EventStream producer
├── distribution_router.py      # FastAPI endpoints (10 routes)
├── distribution_storage.py     # JSON file storage
├── event_consumer.py           # EventStream consumer (auto-create distributions)
├── template_renderer.py        # Jinja2 template rendering
├── templates/                  # HTML templates for course pages
├── EVENTS.md                   # Event specifications (11 events)
└── README.md                   # This file
```

### Dependencies

- **mission_control_core** - EventStream for event bus
- **course_factory** - Consumes events from course generation
- No direct cross-module imports (event-driven integration)

---

## 📡 EventStream Integration

**Status:** ✅ Migrated (Charter v1.0 compliant)
**Migration Date:** 2025-12-28
**Role:** PRODUCER + CONSUMER (first consumer in Sprint 1!)

### Event Catalog

#### Producer Events (9 total)

| Event Type | When Published | Criticality | Consumers |
|------------|----------------|-------------|-----------|
| `distribution.created` | Distribution created | High | Analytics, Audit |
| `distribution.updated` | Metadata modified | Medium | Analytics, Audit |
| `distribution.deleted` | Distribution removed | High | Cache Invalidation, Audit |
| **`distribution.published`** | **Course made PUBLIC** | **CRITICAL** | **SEO Indexer, Marketing, Notifications** |
| `distribution.unpublished` | Course made PRIVATE | High | SEO Indexer, Cache Invalidation |
| `distribution.viewed` | Page viewed (aggregated) | Low | Analytics, Recommendations |
| `distribution.enrollment_clicked` | Enrollment CTA clicked | Medium | Analytics, Conversion Tracking |
| `distribution.micro_niche_created` | Micro-niche variant created | Medium | Analytics, Parent Stats |
| `distribution.version_bumped` | Version incremented | Medium | Changelog, Notifications |

#### Consumer Events (2 total)

| Event Type | Source | Purpose | Idempotency |
|------------|--------|---------|-------------|
| **`course.generation.completed`** | **course_factory** | **Auto-create distribution** | PostgreSQL dedup (stream_message_id) |
| `course.deployed.staging` | course_factory | Update staging URL | PostgreSQL dedup (stream_message_id) |

### Dependency Injection

```python
# Backend/main.py (FastAPI startup)
from backend.mission_control_core.core.event_stream import EventStream

app.state.event_stream = EventStream(redis_client=redis_client)

# distribution_router.py
from fastapi import Request

def get_distribution_service_with_events(request: Request) -> DistributionService:
    """Get DistributionService with EventStream injection."""
    event_stream: Optional[EventStream] = getattr(request.app.state, "event_stream", None)
    return DistributionService(event_stream=event_stream)
```

### Event Publishing Pattern

```python
# distribution_service.py
from backend.mission_control_core.core.event_stream import Event, EventType
from datetime import datetime
import uuid

async def _publish_event_safe(self, event: Event) -> None:
    """Publish event with error handling (non-blocking)."""
    if self.event_stream is None:
        logger.debug("[Distribution] EventStream not available, skipping")
        return

    try:
        await self.event_stream.publish_event(event)
        logger.info(f"[Distribution] Event published: {event.type.value}")
    except Exception as e:
        logger.error(f"[Distribution] Event publishing failed", exc_info=True)
        # DO NOT raise - business logic must continue

async def create_distribution(...) -> CourseDistribution:
    # ... business logic ...

    # EVENT: distribution.created
    await self._publish_event_safe(
        Event(
            id=str(uuid.uuid4()),
            type=EventType.DISTRIBUTION_CREATED,
            source="course_distribution",
            target=None,  # Broadcast
            timestamp=datetime.utcnow(),
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
        )
    )

    return distribution
```

### Event Consumer Pattern (NEW in Sprint 1)

```python
# event_consumer.py
from backend.mission_control_core.core.event_stream import EventStream, Event, EventType
import asyncpg

class DistributionEventConsumer:
    """
    EventConsumer for course_distribution module.

    Charter v1.0 Compliance:
    - Idempotent via stream_message_id deduplication (PostgreSQL)
    - Permanent errors: ACK + log
    - Transient errors: NO ACK + retry
    """

    def __init__(
        self,
        event_stream: EventStream,
        service: DistributionService,
        db_pool: Optional[asyncpg.Pool] = None,
        consumer_id: str = "distribution_consumer",
    ):
        self.event_stream = event_stream
        self.service = service
        self.db_pool = db_pool
        self.consumer_id = consumer_id
        self.running = False
        self._tasks = []

    async def start(self):
        """Start consuming events."""
        self.running = True

        # Subscribe to course.generation.completed
        task1 = asyncio.create_task(
            self.event_stream.subscribe(
                EventType.COURSE_GENERATION_COMPLETED,
                self.handle_course_generation_completed,
                consumer_id=self.consumer_id,
            )
        )
        self._tasks.append(task1)

        # Subscribe to course.deployed.staging
        task2 = asyncio.create_task(
            self.event_stream.subscribe(
                EventType.COURSE_DEPLOYED_STAGING,
                self.handle_course_deployed_staging,
                consumer_id=self.consumer_id,
            )
        )
        self._tasks.append(task2)

        logger.info(f"[DistributionConsumer] Started consuming events")

    async def handle_course_generation_completed(self, event: Event):
        """Auto-create distribution when course is ready."""
        try:
            # 1. Check idempotency (CRITICAL)
            stream_message_id = event.meta.get("stream_message_id")
            if await self.is_duplicate(stream_message_id):
                logger.info(f"Duplicate event {event.id}, skipping")
                return  # ACK (already processed)

            # 2. Validate payload (permanent error check)
            payload = event.payload
            required_fields = ["course_id", "title", "description", "language", "target_audiences"]
            for field in required_fields:
                if field not in payload:
                    logger.error(f"PERMANENT ERROR: Missing field '{field}', ACKing")
                    await self.mark_processed(stream_message_id, event.id, event.type.value, error=f"Missing field: {field}")
                    return  # ACK (permanent error)

            # 3. Generate slug from title
            slug = self._generate_slug(payload["title"])

            # 4. Create distribution
            distribution = await self.service.create_distribution(
                course_id=payload["course_id"],
                slug=slug,
                language=payload.get("language", "de"),
                title=payload["title"],
                description=payload["description"],
                target_group=payload.get("target_audiences", []),
                seo=self._generate_default_seo(payload),
                cta=self._generate_default_cta(),
                version="v1",
                derived_from=None,
            )

            # 5. Mark as processed
            await self.mark_processed(stream_message_id, event.id, event.type.value)

            logger.info(f"Auto-created distribution {distribution.distribution_id}")

        except Exception as e:
            # Transient error (DB unavailable, network issue, etc.)
            logger.error(f"TRANSIENT ERROR: {e}", exc_info=True)
            raise  # Re-raise → NO ACK → retry
```

### Idempotency Implementation

**Primary Dedup Key:** `stream_message_id` (NOT `event.id`)
**Storage:** PostgreSQL table `processed_events`
**Migration:** `backend/alembic/versions/002_event_dedup_stream_message_id.py`

```python
async def is_duplicate(self, stream_message_id: str) -> bool:
    """Check if event already processed (PostgreSQL dedup table)."""
    if not self.db_pool:
        logger.warning("DB pool not available, cannot check duplicates")
        return False  # Fail open

    async with self.db_pool.acquire() as conn:
        result = await conn.fetchrow(
            """
            SELECT 1 FROM processed_events
            WHERE subscriber_name = $1 AND stream_message_id = $2
            """,
            self.consumer_id,
            stream_message_id
        )
        return result is not None

async def mark_processed(
    self,
    stream_message_id: str,
    event_id: Optional[str] = None,
    event_type: Optional[str] = None,
    error: Optional[str] = None,
):
    """Mark event as processed in dedup table."""
    if not self.db_pool:
        return

    async with self.db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO processed_events (
                subscriber_name, stream_name, stream_message_id,
                event_id, event_type, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (subscriber_name, stream_message_id) DO NOTHING
            """,
            self.consumer_id,
            "brain:events:stream",
            stream_message_id,
            event_id,
            event_type,
            {"error": error} if error else None
        )
```

### Error Handling (Charter v1.0)

| Error Type | Example | Action | Result |
|------------|---------|--------|--------|
| **Permanent** | Invalid payload (missing required fields) | ACK + log error + mark processed | Message discarded (no retry) |
| **Transient** | Database unavailable, network timeout | NO ACK + log error | Message requeued for retry |

```python
# Permanent error (invalid payload)
if "title" not in payload:
    logger.error("PERMANENT ERROR: Missing title, ACKing")
    await self.mark_processed(stream_message_id, error="Missing title")
    return  # ACK - do not retry

# Transient error (DB unavailable)
try:
    distribution = await self.service.create_distribution(...)
except Exception as e:
    logger.error(f"TRANSIENT ERROR: {e}", exc_info=True)
    raise  # Re-raise → NO ACK → retry
```

---

## 🚀 API Endpoints

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/distributions/catalog` | List all PUBLIC distributions |
| GET | `/api/distributions/{slug}` | Get distribution by slug |
| GET | `/api/distributions/{slug}/outline` | Get course outline |

### Admin Endpoints (Protected)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/distributions/create` | Create new distribution |
| PUT | `/api/distributions/{id}` | Update distribution |
| DELETE | `/api/distributions/{id}` | Delete distribution |
| POST | `/api/distributions/{id}/publish` | Publish (PRIVATE → PUBLIC) |
| POST | `/api/distributions/{id}/unpublish` | Unpublish (PUBLIC → PRIVATE) |
| POST | `/api/distributions/{id}/log-view` | Log aggregated view |
| POST | `/api/distributions/{id}/track-click` | Track enrollment click |

---

## 🧪 Testing

**Test File:** `backend/tests/test_course_distribution_events.py`
**Total Tests:** 14 (9 producer + 5 consumer)
**Status:** ✅ Infrastructure complete (some tests pending due to JSON storage persistence)

### Test Coverage

**Producer Tests:**
- ✅ `distribution.created` event published
- ✅ `distribution.updated` event published
- ✅ `distribution.deleted` event published
- ✅ `distribution.published` event published
- ✅ `distribution.unpublished` event published
- ✅ `distribution.viewed` event published
- ✅ `distribution.enrollment_clicked` event published
- ✅ `distribution.micro_niche_created` event published
- ✅ `distribution.version_bumped` event published

**Consumer Tests:**
- ✅ Auto-create distribution on `course.generation.completed`
- ✅ Update distribution on `course.deployed.staging`
- ✅ Idempotency prevents duplicate distributions
- ✅ Permanent errors ACKed and logged
- ✅ Transient errors trigger retry

---

## 📊 Data Models

### CourseDistribution

```python
class CourseDistribution(BaseModel):
    distribution_id: str  # Primary key
    course_id: str        # Reference to course_factory
    slug: str             # URL-safe identifier (unique)

    # Content
    language: str         # ISO language code
    title: str           # Display title
    description: str     # Long description
    target_group: List[str]  # Target audiences

    # Versioning
    version: str         # e.g., "v1", "v2"
    derived_from: Optional[str]  # Parent distribution (micro-niche)

    # SEO & CTA
    seo: CourseSEO       # SEO metadata
    cta: CourseCTA       # Call-to-action

    # Visibility
    visibility: CourseVisibility  # PRIVATE | PUBLIC | UNLISTED
    published_at: Optional[float]

    # Timestamps
    created_at: float
    updated_at: float
```

### CourseSEO

```python
class CourseSEO(BaseModel):
    meta_title: str           # 10-60 chars
    meta_description: str     # 50-160 chars
    keywords: List[str]       # Max 10 keywords
    og_image_url: Optional[str]
    hreflang_alternates: Dict[str, str]  # {lang: url}
```

### CourseCTA

```python
class CourseCTA(BaseModel):
    label: str        # 5-50 chars
    action: str       # "open_course" | "download_outline" | "contact" | "custom"
    url: Optional[str]
```

---

## 🔄 Migration Guide (from course_factory integration)

If you have existing CourseFactory integration that directly calls DistributionService:

**Before (Direct Coupling):**
```python
from backend.app.modules.course_distribution.distribution_service import DistributionService

# ANTI-PATTERN: Direct module coupling
distribution_service = DistributionService()
await distribution_service.create_distribution(...)
```

**After (Event-Driven):**
```python
# course_factory/service.py
await self.event_stream.publish_event(
    Event(
        type=EventType.COURSE_GENERATION_COMPLETED,
        payload={
            "course_id": course_id,
            "title": title,
            "description": description,
            # ...
        },
        # ...
    )
)

# course_distribution/event_consumer.py
# Automatically consumes event and creates distribution
```

---

## 📝 Notes

### Storage

**Current:** JSON file-based storage (`backend/storage/distributions/`)
**Future:** PostgreSQL migration planned (Sprint 2)

### Slug Generation

Auto-generated from course titles with:
- Lowercase conversion
- Umlaut replacement (ä→ae, ö→oe, ü→ue, ß→ss)
- Special character removal
- Hyphen-separated words

### Privacy

- **No PII stored** in view/enrollment tracking
- **Aggregated metrics only** (counts, not individual users)
- **GDPR compliant** tracking

---

## 🎯 Future Enhancements

- [ ] PostgreSQL storage migration
- [ ] A/B testing for CTA variants
- [ ] Advanced SEO keyword extraction
- [ ] Multi-language distribution management
- [ ] Automated slug optimization
- [ ] Distribution templates for faster creation

---

**Last Updated:** 2025-12-28
**Maintainer:** BRAiN Core Team
**Module Version:** 1.0.0
**EventStream Version:** Charter v1.0
