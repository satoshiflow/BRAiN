"""
Course Distribution Service

Sprint 15: Course Distribution & Growth Layer
Business logic for course distribution, SEO, and micro-niche variants.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from .distribution_models import (
    CourseDistribution,
    CourseCTA,
    CourseSEO,
    CourseVisibility,
    PublicCourseListItem,
    PublicCourseDetail,
    PublicCourseOutline,
    CourseOutlineModule,
    MicroNicheDerivedContent,
    MicroNicheDerivationRequest,
)
from .distribution_storage import DistributionStorage


class DistributionService:
    """
    Service layer for course distribution.

    Responsibilities:
    - Create and manage course distributions
    - Handle micro-niche derivations
    - Provide public course data (read-only)
    - Track views and enrollments (aggregated)
    - Version management
    """

    def __init__(self, storage: Optional[DistributionStorage] = None):
        self.storage = storage or DistributionStorage()

    # =========================================================================
    # Distribution CRUD
    # =========================================================================

    async def create_distribution(
        self,
        course_id: str,
        slug: str,
        language: str,
        title: str,
        description: str,
        target_group: List[str],
        seo: CourseSEO,
        cta: CourseCTA,
        version: str = "v1",
        derived_from: Optional[str] = None,
    ) -> CourseDistribution:
        """
        Create a new course distribution.

        Args:
            course_id: Reference to base course
            slug: URL-safe slug
            language: ISO language code
            title: Course title
            description: Course description
            target_group: Target audiences
            seo: SEO metadata
            cta: Call-to-action
            version: Course version
            derived_from: Parent course_id if micro-niche variant

        Returns:
            CourseDistribution instance

        Raises:
            ValueError: If slug already exists
        """
        distribution = CourseDistribution(
            course_id=course_id,
            slug=slug,
            language=language,
            title=title,
            description=description,
            target_group=target_group,
            seo=seo,
            cta=cta,
            version=version,
            derived_from=derived_from,
            visibility=CourseVisibility.PRIVATE,  # Start as private
        )

        self.storage.save_distribution(distribution)

        logger.info(
            f"Created distribution {distribution.distribution_id} with slug '{slug}'"
        )

        return distribution

    async def get_distribution_by_slug(self, slug: str) -> Optional[CourseDistribution]:
        """Get distribution by slug."""
        return self.storage.get_distribution_by_slug(slug)

    async def get_distribution_by_id(self, distribution_id: str) -> Optional[CourseDistribution]:
        """Get distribution by ID."""
        return self.storage.get_distribution_by_id(distribution_id)

    async def update_distribution(
        self,
        distribution_id: str,
        **updates,
    ) -> Optional[CourseDistribution]:
        """
        Update distribution fields.

        Args:
            distribution_id: Distribution ID
            **updates: Fields to update

        Returns:
            Updated CourseDistribution, or None if not found
        """
        distribution = self.storage.get_distribution_by_id(distribution_id)
        if not distribution:
            return None

        # Apply updates
        for key, value in updates.items():
            if hasattr(distribution, key):
                setattr(distribution, key, value)

        self.storage.save_distribution(distribution)

        logger.info(f"Updated distribution {distribution_id}")
        return distribution

    async def delete_distribution(self, distribution_id: str) -> bool:
        """Delete a distribution."""
        success = self.storage.delete_distribution(distribution_id)
        if success:
            logger.info(f"Deleted distribution {distribution_id}")
        return success

    # =========================================================================
    # Publishing
    # =========================================================================

    async def publish_distribution(self, distribution_id: str) -> bool:
        """
        Publish a distribution (make public).

        Args:
            distribution_id: Distribution ID

        Returns:
            True if published

        Raises:
            ValueError: If distribution not found
        """
        distribution = self.storage.get_distribution_by_id(distribution_id)
        if not distribution:
            raise ValueError(f"Distribution {distribution_id} not found")

        success = self.storage.publish_distribution(distribution_id)

        if success:
            logger.info(f"Published distribution {distribution_id} (slug: {distribution.slug})")

        return success

    async def unpublish_distribution(self, distribution_id: str) -> bool:
        """
        Unpublish a distribution (make private).

        Args:
            distribution_id: Distribution ID

        Returns:
            True if unpublished
        """
        success = self.storage.unpublish_distribution(distribution_id)

        if success:
            logger.info(f"Unpublished distribution {distribution_id}")

        return success

    # =========================================================================
    # Public API (Read-only)
    # =========================================================================

    async def list_public_courses(
        self,
        language: Optional[str] = None,
        limit: int = 50,
    ) -> List[PublicCourseListItem]:
        """
        List all public courses (read-only).

        Args:
            language: Filter by language
            limit: Maximum results

        Returns:
            List of PublicCourseListItem
        """
        distributions = self.storage.list_distributions(
            visibility=CourseVisibility.PUBLIC,
            language=language,
            only_published=True,
        )

        # Convert to public list items
        results = []
        for dist in distributions[:limit]:
            item = PublicCourseListItem(
                slug=dist.slug,
                language=dist.language,
                title=dist.title,
                description=dist.description,
                target_group=dist.target_group,
                version=dist.version,
                view_count=dist.view_count,
                enrollment_count=dist.enrollment_count,
                published_at=dist.published_at,
            )
            results.append(item)

        return results

    async def get_public_course_detail(self, slug: str) -> Optional[PublicCourseDetail]:
        """
        Get public course detail by slug (read-only).

        Args:
            slug: Course slug

        Returns:
            PublicCourseDetail or None
        """
        distribution = self.storage.get_distribution_by_slug(slug)

        if not distribution or not distribution.is_public():
            return None

        # Log view (aggregated, no PII)
        self.storage.log_view(slug)

        # Get parent slug if micro-niche
        derived_from_slug = None
        if distribution.derived_from:
            parent_dist = self.storage.get_distribution_by_id(distribution.derived_from)
            if parent_dist:
                derived_from_slug = parent_dist.slug

        detail = PublicCourseDetail(
            slug=distribution.slug,
            language=distribution.language,
            title=distribution.title,
            description=distribution.description,
            target_group=distribution.target_group,
            version=distribution.version,
            derived_from_slug=derived_from_slug,
            seo=distribution.seo,
            cta=distribution.cta,
            view_count=distribution.view_count,
            enrollment_count=distribution.enrollment_count,
            published_at=distribution.published_at,
            updated_at=distribution.updated_at,
        )

        return detail

    async def get_public_course_outline(self, slug: str) -> Optional[PublicCourseOutline]:
        """
        Get public course outline by slug (structure only, no content).

        Args:
            slug: Course slug

        Returns:
            PublicCourseOutline or None
        """
        distribution = self.storage.get_distribution_by_slug(slug)

        if not distribution or not distribution.is_public():
            return None

        # TODO: Integrate with CourseFactory to get actual course structure
        # For now, return mock outline
        modules = self._get_course_modules(distribution.course_id)

        total_chapters = sum(m.chapter_count for m in modules)
        total_duration = sum(m.estimated_duration_minutes for m in modules)

        outline = PublicCourseOutline(
            slug=distribution.slug,
            title=distribution.title,
            language=distribution.language,
            version=distribution.version,
            modules=modules,
            total_chapters=total_chapters,
            total_duration_minutes=total_duration,
            prerequisites=[],
            learning_outcomes=[],
        )

        return outline

    def _get_course_modules(self, course_id: str) -> List[CourseOutlineModule]:
        """
        Get course modules from CourseFactory.

        TODO: Integrate with actual CourseFactory service.

        Args:
            course_id: Course ID

        Returns:
            List of CourseOutlineModule
        """
        # Mock implementation
        # In real implementation, fetch from CourseFactory storage
        return [
            CourseOutlineModule(
                module_id="mod_001",
                title="Einführung",
                description="Grundlagen und Überblick",
                chapter_count=3,
                estimated_duration_minutes=45,
            ),
            CourseOutlineModule(
                module_id="mod_002",
                title="Hauptteil",
                description="Vertiefung der Konzepte",
                chapter_count=5,
                estimated_duration_minutes=90,
            ),
        ]

    # =========================================================================
    # Tracking (Aggregated, No PII)
    # =========================================================================

    async def track_enrollment_click(self, slug: str) -> bool:
        """
        Track enrollment CTA click (aggregated).

        Args:
            slug: Course slug

        Returns:
            True if tracked
        """
        return self.storage.log_enrollment_click(slug)

    # =========================================================================
    # Micro-Niche Derivations
    # =========================================================================

    async def create_micro_niche_variant(
        self,
        request: MicroNicheDerivationRequest,
    ) -> CourseDistribution:
        """
        Create micro-niche variant from parent course.

        Args:
            request: Derivation request

        Returns:
            New CourseDistribution (child variant)

        Raises:
            ValueError: If parent course not found
        """
        # Verify parent exists
        parent_dist = self.storage.get_distribution_by_id(request.parent_course_id)
        if not parent_dist:
            raise ValueError(f"Parent course {request.parent_course_id} not found")

        # Apply content overrides
        title = request.derived_content.title_override or parent_dist.title
        description = request.derived_content.description_override or parent_dist.description
        target_group = request.derived_content.target_group_override or request.target_group

        # Create child distribution
        child_dist = await self.create_distribution(
            course_id=parent_dist.course_id,  # Same base course
            slug=request.new_slug,
            language=request.language,
            title=title,
            description=description,
            target_group=target_group,
            seo=request.seo,
            cta=request.cta,
            version=parent_dist.version,  # Inherit version
            derived_from=request.parent_course_id,
        )

        # Save derivation metadata
        self.storage.save_derivation(
            parent_course_id=request.parent_course_id,
            child_distribution_id=child_dist.distribution_id,
            derived_content=request.derived_content,
        )

        logger.info(
            f"Created micro-niche variant {child_dist.distribution_id} "
            f"from parent {request.parent_course_id}"
        )

        return child_dist

    async def get_micro_niche_variants(self, parent_course_id: str) -> List[CourseDistribution]:
        """
        Get all micro-niche variants derived from parent course.

        Args:
            parent_course_id: Parent course ID

        Returns:
            List of child distributions
        """
        derivations = self.storage.get_derivations(parent_course_id)

        variants = []
        for deriv in derivations:
            child_id = deriv["child_distribution_id"]
            child_dist = self.storage.get_distribution_by_id(child_id)
            if child_dist:
                variants.append(child_dist)

        return variants

    # =========================================================================
    # Version Management
    # =========================================================================

    async def bump_version(self, distribution_id: str) -> Optional[str]:
        """
        Bump course version.

        Args:
            distribution_id: Distribution ID

        Returns:
            New version string, or None if not found
        """
        new_version = self.storage.bump_version(distribution_id)

        if new_version:
            logger.info(f"Bumped distribution {distribution_id} to {new_version}")

        return new_version

    # =========================================================================
    # Search & Discovery
    # =========================================================================

    async def search_public_courses(
        self,
        query: str,
        language: Optional[str] = None,
        limit: int = 20,
    ) -> List[PublicCourseListItem]:
        """
        Search public courses by title/description.

        Args:
            query: Search query
            language: Filter by language
            limit: Maximum results

        Returns:
            List of matching courses
        """
        # Get all public courses
        all_courses = await self.list_public_courses(language=language, limit=100)

        # Simple text search
        query_lower = query.lower()
        results = []

        for course in all_courses:
            if (
                query_lower in course.title.lower()
                or query_lower in course.description.lower()
            ):
                results.append(course)

        return results[:limit]
