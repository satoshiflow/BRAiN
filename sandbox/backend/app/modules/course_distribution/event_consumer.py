"""
Course Distribution EventConsumer

Sprint 1: EventStream Integration - Consumer Implementation
First EventConsumer in Sprint 1 (establishes pattern for future consumers)

Consumes:
- course.generation.completed (from course_factory) → auto-create distribution
- course.deployed.staging (from course_factory) → update staging URL

Idempotency:
- Primary key: stream_message_id (NOT event.id)
- PostgreSQL dedup table: event_dedup
- Replay protection via dedup check before processing

Error Handling (Charter v1.0):
- Permanent errors (invalid payload): ACK + log error
- Transient errors (DB unavailable): NO ACK + retry
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime
import asyncio

from loguru import logger
import asyncpg

from mission_control_core.core.event_stream import EventStream, Event, EventType
from .distribution_service import DistributionService
from .distribution_models import CourseSEO, CourseCTA


class DistributionEventConsumer:
    """
    EventConsumer for course_distribution module.

    Consumes events from course_factory to automatically:
    1. Create distributions when courses are ready
    2. Update distributions when courses are deployed

    Charter v1.0 Compliance:
    - Idempotent via stream_message_id deduplication
    - Non-blocking: failures don't crash consumer
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
        """
        Start consuming events.

        Subscribes to:
        - course.generation.completed
        - course.deployed.staging
        """
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

        logger.info(
            f"[DistributionConsumer] Started consuming events (consumer_id={self.consumer_id})"
        )

    async def stop(self):
        """Stop consuming events gracefully."""
        self.running = False

        # Cancel all subscription tasks
        for task in self._tasks:
            task.cancel()

        # Wait for cancellation
        await asyncio.gather(*self._tasks, return_exceptions=True)

        logger.info(f"[DistributionConsumer] Stopped (consumer_id={self.consumer_id})")

    # =========================================================================
    # Event Handlers
    # =========================================================================

    async def handle_course_generation_completed(self, event: Event):
        """
        Auto-create distribution when course is ready.

        Event: course.generation.completed (from course_factory)
        Action: Create distribution entry with auto-generated slug and default SEO/CTA

        Idempotency: Checked via stream_message_id deduplication
        """
        try:
            # 1. Check idempotency (CRITICAL)
            stream_message_id = event.meta.get("stream_message_id")
            if not stream_message_id:
                logger.warning(
                    f"[DistributionConsumer] Event {event.id} missing stream_message_id, "
                    "processing anyway (not idempotent)"
                )
            elif await self.is_duplicate(stream_message_id):
                logger.info(
                    f"[DistributionConsumer] Duplicate event {event.id} "
                    f"(stream_message_id={stream_message_id}), skipping"
                )
                # ACK the message (already processed)
                return

            # 2. Validate payload
            payload = event.payload
            required_fields = ["course_id", "title", "description", "language", "target_audiences"]
            for field in required_fields:
                if field not in payload:
                    logger.error(
                        f"[DistributionConsumer] PERMANENT ERROR: Event {event.id} missing required field '{field}', "
                        "ACKing to prevent retry"
                    )
                    # Mark as processed to prevent infinite retries
                    if stream_message_id:
                        await self.mark_processed(
                            stream_message_id,
                            event_id=event.id,
                            event_type=event.type.value,
                            error=f"Missing field: {field}"
                        )
                    return  # ACK (permanent error)

            # 3. Generate slug from title
            slug = self._generate_slug(payload["title"])

            # 4. Check if distribution already exists for this course_id
            # (protection against duplicate distributions if dedup table is corrupted)
            existing = await self._get_distribution_by_course_id(payload["course_id"])
            if existing:
                logger.warning(
                    f"[DistributionConsumer] Distribution already exists for course {payload['course_id']}, "
                    f"skipping creation (distribution_id={existing[0].distribution_id})"
                )
                # Mark as processed
                if stream_message_id:
                    await self.mark_processed(
                        stream_message_id,
                        event_id=event.id,
                        event_type=event.type.value
                    )
                return

            # 5. Create distribution
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

            # 6. Mark as processed
            if stream_message_id:
                await self.mark_processed(
                    stream_message_id,
                    event_id=event.id,
                    event_type=event.type.value
                )

            logger.info(
                f"[DistributionConsumer] Auto-created distribution {distribution.distribution_id} "
                f"for course {payload['course_id']} (slug={slug})"
            )

        except Exception as e:
            # Transient error (DB unavailable, network issue, etc.)
            logger.error(
                f"[DistributionConsumer] TRANSIENT ERROR handling course.generation.completed: {e}",
                exc_info=True,
            )
            # DO NOT mark as processed → NO ACK → message will be retried
            raise  # Re-raise to signal retry

    async def handle_course_deployed_staging(self, event: Event):
        """
        Update distribution with staging URL when course is deployed.

        Event: course.deployed.staging (from course_factory)
        Action: Update distribution(s) with staging_url

        Idempotency: Checked via stream_message_id deduplication
        """
        try:
            # 1. Check idempotency (CRITICAL)
            stream_message_id = event.meta.get("stream_message_id")
            if not stream_message_id:
                logger.warning(
                    f"[DistributionConsumer] Event {event.id} missing stream_message_id, "
                    "processing anyway (not idempotent)"
                )
            elif await self.is_duplicate(stream_message_id):
                logger.info(
                    f"[DistributionConsumer] Duplicate event {event.id} "
                    f"(stream_message_id={stream_message_id}), skipping"
                )
                return  # ACK (already processed)

            # 2. Validate payload
            payload = event.payload
            if "course_id" not in payload or "staging_url" not in payload:
                logger.error(
                    f"[DistributionConsumer] PERMANENT ERROR: Event {event.id} missing required fields, "
                    "ACKing to prevent retry"
                )
                # Mark as processed to prevent infinite retries
                if stream_message_id:
                    await self.mark_processed(
                        stream_message_id,
                        event_id=event.id,
                        event_type=event.type.value,
                        error="Missing required fields"
                    )
                return  # ACK (permanent error)

            # 3. Find all distributions for this course_id
            distributions = await self._get_distribution_by_course_id(payload["course_id"])

            if not distributions:
                logger.warning(
                    f"[DistributionConsumer] No distributions found for course {payload['course_id']}, "
                    "skipping staging URL update"
                )
                # Mark as processed anyway (no action needed)
                if stream_message_id:
                    await self.mark_processed(
                        stream_message_id,
                        event_id=event.id,
                        event_type=event.type.value
                    )
                return

            # 4. Update all distributions for this course
            updated_count = 0
            for dist in distributions:
                await self.service.update_distribution(
                    distribution_id=dist.distribution_id,
                    staging_url=payload["staging_url"],
                    staging_deployed_at=datetime.fromisoformat(
                        payload.get("deployed_at", datetime.utcnow().isoformat())
                    ),
                )
                updated_count += 1

            # 5. Mark as processed
            if stream_message_id:
                await self.mark_processed(
                    stream_message_id,
                    event_id=event.id,
                    event_type=event.type.value
                )

            logger.info(
                f"[DistributionConsumer] Updated {updated_count} distribution(s) "
                f"for course {payload['course_id']} with staging URL"
            )

        except Exception as e:
            # Transient error
            logger.error(
                f"[DistributionConsumer] TRANSIENT ERROR handling course.deployed.staging: {e}",
                exc_info=True,
            )
            # DO NOT mark as processed → NO ACK → retry
            raise

    # =========================================================================
    # Idempotency (PostgreSQL Dedup Table)
    # =========================================================================

    async def is_duplicate(self, stream_message_id: str) -> bool:
        """
        Check if event has already been processed.

        Uses PostgreSQL dedup table: processed_events
        Primary key: (subscriber_name, stream_message_id)

        Returns:
            True if already processed, False otherwise
        """
        if not self.db_pool:
            logger.warning(
                f"[DistributionConsumer] DB pool not available, cannot check duplicates "
                f"(stream_message_id={stream_message_id})"
            )
            return False  # Fail open - process event

        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.fetchrow(
                    """
                    SELECT 1 FROM processed_events
                    WHERE subscriber_name = $1 AND stream_message_id = $2
                    """,
                    self.consumer_id,
                    stream_message_id
                )
                is_dup = result is not None

                if is_dup:
                    logger.debug(
                        f"[DistributionConsumer] Duplicate detected: {stream_message_id}"
                    )

                return is_dup

        except Exception as e:
            logger.error(
                f"[DistributionConsumer] Error checking duplicate for {stream_message_id}: {e}",
                exc_info=True
            )
            return False  # Fail open on error

    async def mark_processed(
        self,
        stream_message_id: str,
        event_id: Optional[str] = None,
        event_type: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """
        Mark event as processed in dedup table.

        Args:
            stream_message_id: Unique Redis Stream message ID (primary dedup key)
            event_id: Event UUID (secondary, for audit/trace)
            event_type: Event type (for debugging)
            error: Optional error message (for permanent errors)
        """
        if not self.db_pool:
            logger.warning(
                f"[DistributionConsumer] DB pool not available, cannot mark processed "
                f"(stream_message_id={stream_message_id})"
            )
            return

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO processed_events (
                        subscriber_name,
                        stream_name,
                        stream_message_id,
                        event_id,
                        event_type,
                        metadata
                    )
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (subscriber_name, stream_message_id) DO NOTHING
                    """,
                    self.consumer_id,
                    "brain:events:stream",  # Default stream name
                    stream_message_id,
                    event_id,
                    event_type,
                    {"error": error} if error else None
                )

                logger.debug(
                    f"[DistributionConsumer] Marked {stream_message_id} as processed "
                    f"(event_id={event_id}, error={error})"
                )

        except Exception as e:
            logger.error(
                f"[DistributionConsumer] Error marking {stream_message_id} as processed: {e}",
                exc_info=True
            )
            # Don't raise - marking as processed is best-effort

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _generate_slug(self, title: str) -> str:
        """
        Generate URL-safe slug from title.

        Args:
            title: Course title

        Returns:
            URL-safe slug (lowercase, hyphens, no special chars)
        """
        import re

        # Convert to lowercase
        slug = title.lower()

        # Replace umlauts
        replacements = {
            "ä": "ae",
            "ö": "oe",
            "ü": "ue",
            "ß": "ss",
            "é": "e",
            "è": "e",
            "ê": "e",
            "à": "a",
            "â": "a",
            "ô": "o",
            "û": "u",
        }
        for char, replacement in replacements.items():
            slug = slug.replace(char, replacement)

        # Replace spaces and special chars with hyphens
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)

        # Remove leading/trailing hyphens
        slug = slug.strip("-")

        return slug

    def _generate_default_seo(self, payload: dict) -> CourseSEO:
        """Generate default SEO metadata from course payload."""
        # Ensure minimum length requirements
        title = payload["title"]
        description = payload["description"]

        # Pad if too short
        if len(title) < 10:
            title = title + " - Comprehensive Course"
        if len(description) < 50:
            description = description + " This comprehensive course provides detailed insights."

        return CourseSEO(
            meta_title=title[:60],  # Limit to 60 chars for SEO
            meta_description=description[:160],  # Limit to 160 chars
            keywords=[],  # TODO: Extract keywords from content
        )

    def _generate_default_cta(self) -> CourseCTA:
        """Generate default call-to-action."""
        return CourseCTA(
            label="Jetzt starten",
            action="open_course",
            url=None,  # Course URL will be set by frontend
        )

    async def _get_distribution_by_course_id(self, course_id: str):
        """
        Get all distributions for a given course_id.

        Args:
            course_id: Course ID

        Returns:
            List of distributions (empty if none found)
        """
        # TODO: Add method to DistributionService to query by course_id
        # For now, this is a workaround using storage directly
        try:
            # Access storage directly (not ideal, but functional)
            all_distributions = self.service.storage.distributions.values()
            return [d for d in all_distributions if d.course_id == course_id]
        except Exception as e:
            logger.error(
                f"[DistributionConsumer] Error fetching distributions for course {course_id}: {e}"
            )
            return []
