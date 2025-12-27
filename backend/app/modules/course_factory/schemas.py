"""
Course Factory Schemas - Sprint 12

Pydantic models for course structure and generation.
"""

from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import uuid


class CourseLanguage(str, Enum):
    """Supported course languages."""
    DE = "de"  # German
    EN = "en"  # English
    FR = "fr"  # French
    ES = "es"  # Spanish


class CourseTargetAudience(str, Enum):
    """Course target audiences."""
    PRIVATE_INDIVIDUALS = "private_individuals"
    EMPLOYEES = "employees"
    CAREER_STARTERS = "career_starters"
    SME_ENTREPRENEURS = "sme_entrepreneurs"
    RETIREES = "retirees"
    SELF_EMPLOYED = "self_employed"
    STUDENTS = "students"
    PARENTS = "parents"
    MIGRANTS_EXPATS = "migrants_expats"


class LessonStatus(str, Enum):
    """Lesson content status."""
    FULL = "full"  # Fully developed lesson
    PLACEHOLDER = "placeholder"  # Structured placeholder (outline + bullets)
    TODO = "todo"  # Not yet generated


class CourseLesson(BaseModel):
    """Individual course lesson."""

    lesson_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    learning_objectives: List[str] = Field(default_factory=list, max_items=5)
    estimated_duration_minutes: int = Field(..., ge=5, le=120)

    # Content status
    status: LessonStatus = Field(default=LessonStatus.TODO)

    # Lesson content (only if status=FULL)
    content_markdown: Optional[str] = Field(None, description="Full lesson content in Markdown")

    # Placeholder content (if status=PLACEHOLDER)
    content_outline: Optional[List[str]] = Field(None, description="Bullet-point outline")

    # Examples and exercises
    examples: List[str] = Field(default_factory=list, max_items=5)
    exercises: List[str] = Field(default_factory=list, max_items=3)

    # Metadata
    keywords: List[str] = Field(default_factory=list, max_items=10)
    order_index: int = Field(..., ge=0)

    class Config:
        extra = "forbid"


class CourseModule(BaseModel):
    """Course module containing multiple lessons."""

    module_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    learning_objectives: List[str] = Field(default_factory=list, max_items=5)

    # Lessons
    lessons: List[CourseLesson] = Field(..., min_items=3, max_items=5)

    # Metadata
    order_index: int = Field(..., ge=0)
    estimated_total_duration_minutes: int = Field(..., ge=15, le=600)

    class Config:
        extra = "forbid"


class QuizQuestion(BaseModel):
    """Multiple-choice quiz question."""

    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question_text: str = Field(..., min_length=10, max_length=500)

    # Options
    option_a: str = Field(..., min_length=1, max_length=200)
    option_b: str = Field(..., min_length=1, max_length=200)
    option_c: str = Field(..., min_length=1, max_length=200)
    option_d: str = Field(..., min_length=1, max_length=200)

    # Correct answer
    correct_answer: Literal["a", "b", "c", "d"] = Field(...)
    explanation: str = Field(..., min_length=10, max_length=500, description="Why this answer is correct")

    # Metadata
    difficulty: Literal["easy", "medium", "hard"] = Field(default="medium")
    module_reference: Optional[str] = Field(None, description="Module ID this question relates to")

    class Config:
        extra = "forbid"


class CourseQuiz(BaseModel):
    """Course assessment quiz."""

    quiz_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(default="Course Assessment")
    description: str = Field(default="Test your knowledge")

    # Questions
    questions: List[QuizQuestion] = Field(..., min_items=10, max_items=15)

    # Scoring
    passing_score_percentage: int = Field(default=70, ge=50, le=100)
    time_limit_minutes: Optional[int] = Field(None, ge=10, le=120)

    class Config:
        extra = "forbid"


class CourseLandingPage(BaseModel):
    """Landing page content for the course."""

    # Hero section
    hero_title: str = Field(..., min_length=10, max_length=200)
    hero_subtitle: str = Field(..., min_length=10, max_length=500)
    hero_cta_text: str = Field(default="Course coming soon")

    # Value proposition
    value_proposition: str = Field(..., min_length=50, max_length=1000)

    # Target audience
    for_whom_title: str = Field(default="Who is this course for?")
    for_whom_points: List[str] = Field(..., min_items=3, max_items=5)

    not_for_whom_title: str = Field(default="Who is this course NOT for?")
    not_for_whom_points: List[str] = Field(..., min_items=2, max_items=4)

    # Course structure (auto-generated from outline)
    course_structure_title: str = Field(default="What you'll learn")

    # Features
    features: List[str] = Field(default_factory=list, max_items=6)

    # Footer
    disclaimer: str = Field(default="No payment required. Educational content only.")

    class Config:
        extra = "forbid"


class CourseMetadata(BaseModel):
    """Course metadata and configuration."""

    course_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Basic info
    title: str = Field(..., min_length=10, max_length=200)
    description: str = Field(..., min_length=50, max_length=2000)
    language: CourseLanguage = Field(...)
    target_audiences: List[CourseTargetAudience] = Field(..., min_items=1)

    # Content configuration
    full_lessons_count: int = Field(default=3, ge=1, le=10, description="Number of fully developed lessons")

    # Tone and style
    tone: Literal["sachlich", "empowernd", "neutral", "professiona"] = Field(
        default="sachlich",
        description="Tone of the course content"
    )
    avoid_ideology: bool = Field(default=True, description="Avoid ideological positioning")
    avoid_product_sales: bool = Field(default=True, description="Avoid product sales pitches")

    # Versioning
    version: str = Field(default="1.0.0")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        extra = "forbid"


class CourseOutline(BaseModel):
    """Complete course outline structure."""

    metadata: CourseMetadata = Field(...)
    modules: List[CourseModule] = Field(..., min_items=4, max_items=6)

    # Summary statistics
    total_lessons: int = Field(..., ge=12, le=30)
    total_estimated_duration_minutes: int = Field(..., ge=60, le=3600)

    class Config:
        extra = "forbid"

    def get_full_lessons(self) -> List[CourseLesson]:
        """Get all lessons with full content."""
        full_lessons = []
        for module in self.modules:
            for lesson in module.lessons:
                if lesson.status == LessonStatus.FULL:
                    full_lessons.append(lesson)
        return full_lessons

    def get_placeholder_lessons(self) -> List[CourseLesson]:
        """Get all placeholder lessons."""
        placeholders = []
        for module in self.modules:
            for lesson in module.lessons:
                if lesson.status == LessonStatus.PLACEHOLDER:
                    placeholders.append(lesson)
        return placeholders


class CourseLessonContent(BaseModel):
    """Full lesson content (for FULL status lessons)."""

    lesson_id: str = Field(...)
    content_markdown: str = Field(..., min_length=500, max_length=10000)

    # Generated assets
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    word_count: int = Field(..., ge=300)

    class Config:
        extra = "forbid"


class CourseGenerationRequest(BaseModel):
    """Request to generate a complete course."""

    # Required inputs
    tenant_id: str = Field(..., min_length=1, max_length=100)

    # Course configuration
    title: str = Field(..., min_length=10, max_length=200)
    description: str = Field(..., min_length=50, max_length=2000)
    language: CourseLanguage = Field(...)
    target_audiences: List[CourseTargetAudience] = Field(..., min_items=1)

    # Content generation settings
    full_lessons_count: int = Field(default=3, ge=1, le=10)
    generate_quiz: bool = Field(default=True)
    generate_landing_page: bool = Field(default=True)

    # Deployment settings
    deploy_to_staging: bool = Field(default=False)
    staging_domain: Optional[str] = Field(None, description="Staging domain (e.g., course-alt-banken.staging.brain)")

    # Governance
    dry_run: bool = Field(default=True, description="Dry-run mode (no actual generation)")

    class Config:
        extra = "forbid"


class CourseGenerationResult(BaseModel):
    """Result of course generation."""

    success: bool = Field(...)
    course_id: str = Field(...)

    # Generated artifacts
    outline: Optional[CourseOutline] = Field(None)
    quiz: Optional[CourseQuiz] = Field(None)
    landing_page: Optional[CourseLandingPage] = Field(None)

    # Deployment info
    deployed: bool = Field(default=False)
    staging_url: Optional[str] = Field(None)

    # Evidence
    evidence_pack_path: Optional[str] = Field(None)
    ir_hash: Optional[str] = Field(None)

    # Summary
    total_modules: int = Field(..., ge=0)
    total_lessons: int = Field(..., ge=0)
    full_lessons_generated: int = Field(..., ge=0)
    quiz_questions_count: int = Field(default=0)

    # Execution metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    execution_time_seconds: float = Field(..., ge=0)

    # Errors (if any)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"
