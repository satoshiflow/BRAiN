"""
Course Distribution Data Models

Sprint 15: Course Distribution & Growth Layer
Handles public course distribution, SEO, micro-niche variants.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class CourseVisibility(str, Enum):
    """Course visibility levels."""
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


class CourseSEO(BaseModel):
    """SEO metadata for course."""
    meta_title: str = Field(..., min_length=10, max_length=60, description="SEO title (50-60 chars)")
    meta_description: str = Field(..., min_length=50, max_length=160, description="SEO description (150-160 chars)")
    keywords: List[str] = Field(default_factory=list, description="SEO keywords")
    og_image_url: Optional[str] = Field(None, description="OpenGraph image URL")
    hreflang_alternates: Dict[str, str] = Field(
        default_factory=dict,
        description="Language alternates: {lang_code: url}"
    )

    model_config = {"extra": "forbid"}

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: List[str]) -> List[str]:
        """Validate keywords."""
        if len(v) > 10:
            raise ValueError("Maximum 10 keywords allowed")
        return v


class CourseCTA(BaseModel):
    """Call-to-action configuration."""
    label: str = Field(..., min_length=5, max_length=50, description="CTA button label")
    action: str = Field(..., description="Action type: open_course, download_outline, contact")
    url: Optional[str] = Field(None, description="Optional external URL")

    model_config = {"extra": "forbid"}

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Validate action type."""
        allowed_actions = ["open_course", "download_outline", "contact", "custom"]
        if v not in allowed_actions:
            raise ValueError(f"Action must be one of: {allowed_actions}")
        return v


class CourseDistribution(BaseModel):
    """
    Course distribution model.

    Represents a publicly distributable course with SEO, CTA, and micro-niche capabilities.
    """
    # Identity
    distribution_id: str = Field(default_factory=lambda: f"dist_{uuid4().hex[:16]}")
    course_id: str = Field(..., description="Reference to base course")
    slug: str = Field(..., min_length=5, max_length=100, description="URL-safe slug")

    # Content
    language: str = Field(..., min_length=2, max_length=5, description="ISO language code")
    title: str = Field(..., min_length=10, max_length=200)
    description: str = Field(..., min_length=50, max_length=1000)
    target_group: List[str] = Field(
        default_factory=list,
        description="Target audiences: private, angestellte, freelancer, studenten, rentner, etc."
    )

    # Versioning & Derivation
    version: str = Field(default="v1", description="Course version")
    derived_from: Optional[str] = Field(None, description="Parent course_id if micro-niche variant")

    # SEO & CTA
    seo: CourseSEO
    cta: CourseCTA

    # Visibility
    visibility: CourseVisibility = Field(default=CourseVisibility.PRIVATE)

    # Metadata
    published_at: Optional[float] = Field(None, description="Publication timestamp")
    updated_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    created_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())

    # Statistics (aggregated, no PII)
    view_count: int = Field(default=0, description="Total views")
    enrollment_count: int = Field(default=0, description="Total enrollments")

    model_config = {"extra": "forbid"}

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug format."""
        import re
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError("Slug must be lowercase alphanumeric with hyphens only")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate language code."""
        # Support ISO 639-1 (2-letter) and extended (e.g., de-DE)
        import re
        if not re.match(r"^[a-z]{2}(-[A-Z]{2})?$", v):
            raise ValueError("Language must be ISO 639-1 format (e.g., 'de', 'en', 'de-DE')")
        return v

    def is_public(self) -> bool:
        """Check if course is publicly visible."""
        return self.visibility == CourseVisibility.PUBLIC and self.published_at is not None

    def is_micro_niche(self) -> bool:
        """Check if this is a micro-niche variant."""
        return self.derived_from is not None


class PublicCourseListItem(BaseModel):
    """
    Public course list item (minimal data).

    Used for GET /api/courses/public
    """
    slug: str
    language: str
    title: str
    description: str
    target_group: List[str]
    version: str
    view_count: int
    enrollment_count: int
    published_at: Optional[float]

    model_config = {"extra": "forbid"}


class PublicCourseDetail(BaseModel):
    """
    Public course detail (full data except internal IDs).

    Used for GET /api/courses/public/{slug}
    """
    slug: str
    language: str
    title: str
    description: str
    target_group: List[str]
    version: str
    derived_from_slug: Optional[str] = Field(None, description="Parent course slug if variant")
    seo: CourseSEO
    cta: CourseCTA
    view_count: int
    enrollment_count: int
    published_at: Optional[float]
    updated_at: float

    model_config = {"extra": "forbid"}


class CourseOutlineModule(BaseModel):
    """Course module outline."""
    module_id: str
    title: str
    description: str
    chapter_count: int
    estimated_duration_minutes: int

    model_config = {"extra": "forbid"}


class PublicCourseOutline(BaseModel):
    """
    Public course outline (structure only, no content).

    Used for GET /api/courses/public/{slug}/outline
    """
    slug: str
    title: str
    language: str
    version: str
    modules: List[CourseOutlineModule]
    total_chapters: int
    total_duration_minutes: int
    prerequisites: List[str] = Field(default_factory=list)
    learning_outcomes: List[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


# Micro-Niche Derivation Models

class MicroNicheDerivedContent(BaseModel):
    """
    Content overrides for micro-niche variants.

    Defines what changes from parent course.
    """
    title_override: Optional[str] = None
    description_override: Optional[str] = None
    target_group_override: Optional[List[str]] = None
    example_replacements: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of original example IDs to replacement examples"
    )
    module_filters: Optional[List[str]] = Field(
        None,
        description="If set, only include these module IDs"
    )
    additional_context: Optional[str] = Field(
        None,
        description="Additional context for this niche (e.g., 'Optimiert für Rentner')"
    )

    model_config = {"extra": "forbid"}


class MicroNicheDerivationRequest(BaseModel):
    """
    Request to create micro-niche variant from parent course.
    """
    parent_course_id: str
    new_slug: str
    language: str  # Can be different from parent
    derived_content: MicroNicheDerivedContent
    seo: CourseSEO
    cta: CourseCTA
    target_group: List[str]

    model_config = {"extra": "forbid"}
