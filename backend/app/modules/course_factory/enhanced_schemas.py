"""
Enhanced Course Schemas - Sprint 13

Extensions to Sprint 12 schemas for workflow, enhancements, and WebGenesis integration.
"""

from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
import uuid

from app.modules.course_factory.schemas import (
    CourseOutline,
    CourseLesson,
    CourseQuiz,
    CourseLandingPage,
    CourseMetadata,
)


class WorkflowState(str, Enum):
    """Course workflow states."""
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISH_READY = "publish_ready"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EnhancementType(str, Enum):
    """Types of LLM enhancements."""
    EXAMPLES = "examples"
    SUMMARIES = "summaries"
    FLASHCARDS = "flashcards"
    ANALOGIES = "analogies"


class ContentEnhancement(BaseModel):
    """Individual content enhancement."""

    enhancement_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    enhancement_type: EnhancementType = Field(...)
    target_lesson_id: str = Field(..., description="Lesson being enhanced")

    # Original vs Enhanced
    base_content: str = Field(..., description="Original content")
    enhanced_content: str = Field(..., description="LLM-enhanced content")

    # Validation
    validated: bool = Field(default=False)
    validation_passed: bool = Field(default=False)
    validation_errors: List[str] = Field(default_factory=list)

    # Diff audit
    content_diff_hash: Optional[str] = Field(None, description="Diff hash for audit")
    structural_changes: bool = Field(default=False, description="Whether structure was changed")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(None, description="User/system who created")

    class Config:
        extra = "forbid"


class Flashcard(BaseModel):
    """Learning flashcard."""

    flashcard_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str = Field(..., min_length=10, max_length=500)
    answer: str = Field(..., min_length=10, max_length=1000)

    # References
    lesson_id: str = Field(..., description="Source lesson")
    module_id: Optional[str] = Field(None, description="Source module")

    # Difficulty
    difficulty: Literal["easy", "medium", "hard"] = Field(default="medium")

    # Metadata
    keywords: List[str] = Field(default_factory=list, max_items=5)

    class Config:
        extra = "forbid"


class FlashcardDeck(BaseModel):
    """Collection of flashcards for a course."""

    deck_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    course_id: str = Field(...)
    title: str = Field(default="Course Flashcards")

    # Flashcards
    flashcards: List[Flashcard] = Field(..., min_items=1)

    # Statistics
    total_cards: int = Field(..., ge=1)
    easy_count: int = Field(default=0, ge=0)
    medium_count: int = Field(default=0, ge=0)
    hard_count: int = Field(default=0, ge=0)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        extra = "forbid"


class WebGenesisTheme(BaseModel):
    """WebGenesis theme configuration."""

    theme_id: str = Field(..., min_length=1, max_length=100)
    theme_name: str = Field(..., min_length=1, max_length=200)

    # Theme properties
    primary_color: str = Field(default="#0066cc")
    secondary_color: str = Field(default="#6c757d")
    font_family: str = Field(default="system-ui, -apple-system, sans-serif")

    # Features
    supports_dark_mode: bool = Field(default=True)
    supports_i18n: bool = Field(default=True)
    supports_seo: bool = Field(default=True)

    # Template paths
    template_path: str = Field(..., description="Path to theme template")
    assets_path: Optional[str] = Field(None, description="Path to theme assets")

    class Config:
        extra = "forbid"


class WebGenesisSection(BaseModel):
    """Website section built from course data."""

    section_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    section_type: Literal["hero", "syllabus", "lesson_preview", "faq", "cta", "footer"] = Field(...)

    # Content
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)

    # Styling
    background_color: Optional[str] = Field(None)
    text_color: Optional[str] = Field(None)

    # Order
    order_index: int = Field(..., ge=0)

    class Config:
        extra = "forbid"


class SEOPack(BaseModel):
    """SEO metadata pack for course website."""

    # Basic meta tags
    meta_title: str = Field(..., min_length=10, max_length=70)
    meta_description: str = Field(..., min_length=50, max_length=160)
    meta_keywords: List[str] = Field(default_factory=list, max_items=10)

    # Open Graph
    og_title: str = Field(..., min_length=10, max_length=70)
    og_description: str = Field(..., min_length=50, max_length=200)
    og_type: str = Field(default="website")
    og_image: Optional[str] = Field(None, description="OG image URL")

    # Twitter Card
    twitter_card: str = Field(default="summary_large_image")
    twitter_title: str = Field(..., min_length=10, max_length=70)
    twitter_description: str = Field(..., min_length=50, max_length=200)

    # JSON-LD (Course structured data)
    json_ld: Dict[str, Any] = Field(default_factory=dict)

    # Additional meta
    canonical_url: Optional[str] = Field(None)
    robots: str = Field(default="index, follow")

    class Config:
        extra = "forbid"


class i18nPlaceholders(BaseModel):
    """Internationalization placeholders for non-primary languages."""

    language: str = Field(..., min_length=2, max_length=5)  # e.g., "en", "fr", "es"

    # Placeholder structure
    modules_count: int = Field(..., ge=0)
    lessons_count: int = Field(..., ge=0)
    quiz_questions_count: int = Field(default=0, ge=0)

    # Translation markers
    translation_required: bool = Field(default=True)
    translation_status: Literal["pending", "in_progress", "completed"] = Field(default="pending")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        extra = "forbid"


class WorkflowTransition(BaseModel):
    """Workflow state transition record."""

    transition_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    course_id: str = Field(...)

    # Transition
    from_state: WorkflowState = Field(...)
    to_state: WorkflowState = Field(...)

    # Approval (for HITL gates)
    requires_approval: bool = Field(default=False)
    approval_token: Optional[str] = Field(None, description="HITL approval token if required")
    approved_by: Optional[str] = Field(None, description="User who approved")

    # Validation
    validation_passed: bool = Field(default=True)
    validation_errors: List[str] = Field(default_factory=list)

    # Metadata
    transitioned_at: datetime = Field(default_factory=datetime.utcnow)
    transitioned_by: str = Field(..., description="User/system who triggered transition")

    # Rollback support
    can_rollback: bool = Field(default=True)
    rollback_state: Optional[WorkflowState] = Field(None)

    class Config:
        extra = "forbid"


class EnhancedCourseMetadata(CourseMetadata):
    """Extended course metadata with workflow and enhancements."""

    # Workflow
    workflow_state: WorkflowState = Field(default=WorkflowState.DRAFT)
    workflow_history: List[WorkflowTransition] = Field(default_factory=list)

    # Enhancements
    enhancements_enabled: bool = Field(default=False, description="Whether LLM enhancements are enabled")
    enhancements: List[ContentEnhancement] = Field(default_factory=list)

    # WebGenesis
    webgenesis_theme_id: Optional[str] = Field(None, description="Bound theme ID")
    webgenesis_preview_url: Optional[str] = Field(None, description="Latest preview URL")
    webgenesis_sections: List[WebGenesisSection] = Field(default_factory=list)

    # SEO
    seo_pack: Optional[SEOPack] = Field(None, description="SEO metadata")

    # i18n
    i18n_placeholders: List[i18nPlaceholders] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class EnhancementRequest(BaseModel):
    """Request to enhance course content with LLM."""

    course_id: str = Field(...)
    lesson_ids: List[str] = Field(..., min_items=1, description="Lessons to enhance")
    enhancement_types: List[EnhancementType] = Field(..., min_items=1)

    # LLM configuration (optional overrides)
    llm_temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    llm_max_tokens: int = Field(default=2000, ge=100, le=4000)

    # Validation settings
    validate_enhancements: bool = Field(default=True, description="Run validation checks")
    fail_on_validation_error: bool = Field(default=False, description="Fail if validation fails")

    # Audit
    dry_run: bool = Field(default=True, description="Dry-run mode (no actual LLM calls)")

    class Config:
        extra = "forbid"


class EnhancementResult(BaseModel):
    """Result of content enhancement."""

    success: bool = Field(...)
    course_id: str = Field(...)

    # Enhanced content
    enhancements: List[ContentEnhancement] = Field(default_factory=list)

    # Statistics
    total_enhancements: int = Field(default=0, ge=0)
    validated_count: int = Field(default=0, ge=0)
    failed_count: int = Field(default=0, ge=0)

    # Errors
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    # Metadata
    execution_time_seconds: float = Field(..., ge=0)

    class Config:
        extra = "forbid"
