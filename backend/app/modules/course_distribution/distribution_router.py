"""
Course Distribution Router

Sprint 15: Course Distribution & Growth Layer
Public API endpoints for course distribution.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from loguru import logger
from pydantic import BaseModel, Field

from .distribution_models import (
    CourseCTA,
    CourseSEO,
    CourseVisibility,
    MicroNicheDerivedContent,
    MicroNicheDerivationRequest,
    PublicCourseDetail,
    PublicCourseListItem,
    PublicCourseOutline,
)
from .distribution_service import DistributionService
from .template_renderer import TemplateRenderer


router = APIRouter(prefix="/api/courses", tags=["course-distribution"])


# =========================================================================
# Request/Response Models
# =========================================================================

class CreateDistributionRequest(BaseModel):
    """Request to create course distribution."""
    course_id: str
    slug: str
    language: str
    title: str
    description: str
    target_group: List[str]
    seo: CourseSEO
    cta: CourseCTA
    version: str = "v1"

    model_config = {"extra": "forbid"}


class CreateDistributionResponse(BaseModel):
    """Response after creating distribution."""
    distribution_id: str
    slug: str
    message: str

    model_config = {"extra": "forbid"}


class PublishResponse(BaseModel):
    """Response after publishing/unpublishing."""
    distribution_id: str
    published: bool
    message: str

    model_config = {"extra": "forbid"}


class VersionBumpResponse(BaseModel):
    """Response after version bump."""
    distribution_id: str
    old_version: str
    new_version: str
    message: str

    model_config = {"extra": "forbid"}


class TrackEnrollmentResponse(BaseModel):
    """Response after tracking enrollment click."""
    slug: str
    tracked: bool
    message: str

    model_config = {"extra": "forbid"}


class HealthResponse(BaseModel):
    """Health check response."""
    name: str
    version: str
    status: str
    public_courses_count: int

    model_config = {"extra": "forbid"}


# =========================================================================
# Dependency Injection
# =========================================================================

def get_distribution_service() -> DistributionService:
    """Get distribution service instance."""
    return DistributionService()


# =========================================================================
# PUBLIC ENDPOINTS (Read-only, No Authentication)
# =========================================================================

@router.get(
    "/public",
    response_model=List[PublicCourseListItem],
    summary="List all public courses",
    description="Get list of all publicly available courses. No authentication required.",
)
async def list_public_courses(
    language: Optional[str] = Query(None, description="Filter by language (ISO code)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    service: DistributionService = None,
) -> List[PublicCourseListItem]:
    """
    List all public courses.

    **Public endpoint** - No authentication required.

    Args:
        language: Filter by language code (e.g., 'de', 'en')
        limit: Maximum number of results (1-100)

    Returns:
        List of public course summaries
    """
    if service is None:
        service = get_distribution_service()

    try:
        courses = await service.list_public_courses(language=language, limit=limit)
        return courses
    except Exception as e:
        logger.error(f"Error listing public courses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch public courses",
        )


@router.get(
    "/public/{slug}",
    response_model=PublicCourseDetail,
    summary="Get public course details",
    description="Get detailed information about a specific public course. No authentication required.",
)
async def get_public_course_detail(
    slug: str,
    service: DistributionService = None,
) -> PublicCourseDetail:
    """
    Get public course details by slug.

    **Public endpoint** - No authentication required.
    Increments view counter (aggregated, no PII).

    Args:
        slug: Course slug (URL-safe identifier)

    Returns:
        Course details including SEO metadata and CTA

    Raises:
        404: Course not found or not public
    """
    if service is None:
        service = get_distribution_service()

    try:
        detail = await service.get_public_course_detail(slug)

        if not detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course '{slug}' not found or not public",
            )

        return detail
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching course detail for '{slug}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch course details",
        )


@router.get(
    "/public/{slug}/outline",
    response_model=PublicCourseOutline,
    summary="Get public course outline",
    description="Get course structure/outline (modules, chapters). No content, structure only.",
)
async def get_public_course_outline(
    slug: str,
    service: DistributionService = None,
) -> PublicCourseOutline:
    """
    Get public course outline by slug.

    **Public endpoint** - No authentication required.

    Returns course structure (modules, chapters) without actual content.
    Useful for displaying course overview before enrollment.

    Args:
        slug: Course slug

    Returns:
        Course outline with modules and chapter counts

    Raises:
        404: Course not found or not public
    """
    if service is None:
        service = get_distribution_service()

    try:
        outline = await service.get_public_course_outline(slug)

        if not outline:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course '{slug}' not found or not public",
            )

        return outline
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching course outline for '{slug}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch course outline",
        )


@router.post(
    "/public/{slug}/track-enrollment",
    response_model=TrackEnrollmentResponse,
    summary="Track enrollment CTA click",
    description="Track when user clicks enrollment CTA. Aggregated tracking, no PII.",
)
async def track_enrollment_click(
    slug: str,
    service: DistributionService = None,
) -> TrackEnrollmentResponse:
    """
    Track enrollment CTA click.

    **Public endpoint** - No authentication required.

    Increments enrollment counter (aggregated, no PII).
    Called when user clicks "Start Course" or similar CTA.

    Args:
        slug: Course slug

    Returns:
        Tracking confirmation

    Raises:
        404: Course not found
    """
    if service is None:
        service = get_distribution_service()

    try:
        # Verify course exists
        distribution = await service.get_distribution_by_slug(slug)
        if not distribution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course '{slug}' not found",
            )

        # Track click
        tracked = await service.track_enrollment_click(slug)

        return TrackEnrollmentResponse(
            slug=slug,
            tracked=tracked,
            message="Enrollment click tracked",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking enrollment for '{slug}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to track enrollment",
        )


@router.get(
    "/public/{slug}/page",
    response_class=HTMLResponse,
    summary="Render course landing page (HTML)",
    description="Get fully rendered HTML course landing page with SEO, OpenGraph, structured data.",
)
async def render_course_page(
    slug: str,
    service: DistributionService = None,
) -> HTMLResponse:
    """
    Render complete course landing page as HTML.

    **Public endpoint** - No authentication required.

    Returns fully rendered HTML with:
    - SEO meta tags
    - OpenGraph / Twitter Cards
    - JSON-LD structured data
    - Responsive design
    - CTA buttons

    Args:
        slug: Course slug

    Returns:
        Rendered HTML page

    Raises:
        404: Course not found or not public
    """
    if service is None:
        service = get_distribution_service()

    try:
        # Get course detail and outline
        detail = await service.get_public_course_detail(slug)
        outline = await service.get_public_course_outline(slug)

        if not detail or not outline:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course '{slug}' not found or not public",
            )

        # Render HTML
        renderer = TemplateRenderer()
        html = renderer.render_course_page(detail, outline)

        return HTMLResponse(content=html, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering course page for '{slug}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to render course page",
        )


# =========================================================================
# ADMIN ENDPOINTS (Protected - Future: Add Authentication)
# =========================================================================

@router.post(
    "/distribution/create",
    response_model=CreateDistributionResponse,
    summary="Create course distribution",
    description="Create a new course distribution record. Admin only.",
    status_code=status.HTTP_201_CREATED,
)
async def create_distribution(
    request: CreateDistributionRequest,
    service: DistributionService = None,
) -> CreateDistributionResponse:
    """
    Create a new course distribution.

    **Admin endpoint** - Future: Requires authentication.

    Args:
        request: Distribution creation data

    Returns:
        Created distribution info

    Raises:
        400: Invalid data or slug already exists
    """
    if service is None:
        service = get_distribution_service()

    try:
        distribution = await service.create_distribution(
            course_id=request.course_id,
            slug=request.slug,
            language=request.language,
            title=request.title,
            description=request.description,
            target_group=request.target_group,
            seo=request.seo,
            cta=request.cta,
            version=request.version,
        )

        return CreateDistributionResponse(
            distribution_id=distribution.distribution_id,
            slug=distribution.slug,
            message=f"Distribution created successfully (slug: {distribution.slug})",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating distribution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create distribution",
        )


@router.post(
    "/distribution/{distribution_id}/publish",
    response_model=PublishResponse,
    summary="Publish course distribution",
    description="Make course publicly visible. Admin only.",
)
async def publish_distribution(
    distribution_id: str,
    service: DistributionService = None,
) -> PublishResponse:
    """
    Publish a course distribution (make public).

    **Admin endpoint** - Future: Requires authentication.

    Args:
        distribution_id: Distribution ID

    Returns:
        Publish confirmation

    Raises:
        404: Distribution not found
    """
    if service is None:
        service = get_distribution_service()

    try:
        success = await service.publish_distribution(distribution_id)

        return PublishResponse(
            distribution_id=distribution_id,
            published=True,
            message="Course published successfully",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error publishing distribution {distribution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish distribution",
        )


@router.post(
    "/distribution/{distribution_id}/unpublish",
    response_model=PublishResponse,
    summary="Unpublish course distribution",
    description="Make course private (remove from public listing). Admin only.",
)
async def unpublish_distribution(
    distribution_id: str,
    service: DistributionService = None,
) -> PublishResponse:
    """
    Unpublish a course distribution (make private).

    **Admin endpoint** - Future: Requires authentication.

    Args:
        distribution_id: Distribution ID

    Returns:
        Unpublish confirmation

    Raises:
        404: Distribution not found
    """
    if service is None:
        service = get_distribution_service()

    try:
        success = await service.unpublish_distribution(distribution_id)

        return PublishResponse(
            distribution_id=distribution_id,
            published=False,
            message="Course unpublished successfully",
        )
    except Exception as e:
        logger.error(f"Error unpublishing distribution {distribution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unpublish distribution",
        )


@router.post(
    "/distribution/micro-niche",
    response_model=CreateDistributionResponse,
    summary="Create micro-niche variant",
    description="Create micro-niche course variant from parent. Admin only.",
    status_code=status.HTTP_201_CREATED,
)
async def create_micro_niche_variant(
    request: MicroNicheDerivationRequest,
    service: DistributionService = None,
) -> CreateDistributionResponse:
    """
    Create micro-niche variant from parent course.

    **Admin endpoint** - Future: Requires authentication.

    Creates a derived course variant targeting specific niche audience
    (e.g., retirees, students, freelancers).

    Args:
        request: Derivation request

    Returns:
        Created variant info

    Raises:
        404: Parent course not found
        400: Invalid data
    """
    if service is None:
        service = get_distribution_service()

    try:
        variant = await service.create_micro_niche_variant(request)

        return CreateDistributionResponse(
            distribution_id=variant.distribution_id,
            slug=variant.slug,
            message=f"Micro-niche variant created (slug: {variant.slug})",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating micro-niche variant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create micro-niche variant",
        )


@router.post(
    "/distribution/{distribution_id}/version-bump",
    response_model=VersionBumpResponse,
    summary="Bump course version",
    description="Increment course version (e.g., v1 -> v2). Admin only.",
)
async def bump_course_version(
    distribution_id: str,
    service: DistributionService = None,
) -> VersionBumpResponse:
    """
    Bump course version.

    **Admin endpoint** - Future: Requires authentication.

    Increments version number (v1 -> v2, v2 -> v3, etc.).
    Required before publishing course changes.

    Args:
        distribution_id: Distribution ID

    Returns:
        Version bump confirmation

    Raises:
        404: Distribution not found
    """
    if service is None:
        service = get_distribution_service()

    try:
        # Get current version
        distribution = await service.get_distribution_by_id(distribution_id)
        if not distribution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Distribution {distribution_id} not found",
            )

        old_version = distribution.version

        # Bump version
        new_version = await service.bump_version(distribution_id)

        if not new_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Distribution {distribution_id} not found",
            )

        return VersionBumpResponse(
            distribution_id=distribution_id,
            old_version=old_version,
            new_version=new_version,
            message=f"Version bumped from {old_version} to {new_version}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bumping version for {distribution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bump version",
        )


# =========================================================================
# HEALTH & INFO
# =========================================================================

@router.get(
    "/distribution/health",
    response_model=HealthResponse,
    summary="Distribution system health",
    description="Health check for course distribution system.",
)
async def distribution_health(
    service: DistributionService = None,
) -> HealthResponse:
    """
    Health check for course distribution system.

    Returns:
        System health status
    """
    if service is None:
        service = get_distribution_service()

    try:
        # Count public courses
        public_courses = await service.list_public_courses(limit=1000)
        count = len(public_courses)

        return HealthResponse(
            name="Course Distribution System",
            version="1.0.0",
            status="healthy",
            public_courses_count=count,
        )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthResponse(
            name="Course Distribution System",
            version="1.0.0",
            status="degraded",
            public_courses_count=0,
        )
