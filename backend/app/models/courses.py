"""
Course Factory Database Models

SQLAlchemy models for course creation, curriculum management, and learning resources.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class CourseTemplate(Base):
    """Master course template with curriculum structure"""
    __tablename__ = "course_templates"

    id = Column(String(50), primary_key=True)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # e.g., "programming", "business", "design", "science"
    difficulty_level = Column(String(50))  # "beginner", "intermediate", "advanced", "expert"

    # Course metadata
    language = Column(String(10), default="en")
    estimated_duration_hours = Column(Float)
    prerequisites = Column(JSON)  # List of prerequisite course IDs or skills

    # Content structure
    modules = relationship("CourseModule", back_populates="course", cascade="all, delete-orphan")

    # Publishing status
    status = Column(String(50), default="draft")  # "draft", "review", "published", "archived"
    published_at = Column(DateTime)
    version = Column(Integer, default=1)

    # Enrollment and statistics
    total_enrollments = Column(Integer, default=0)
    completion_rate = Column(Float, default=0.0)
    avg_rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)

    # Pricing (optional)
    is_free = Column(Boolean, default=True)
    price = Column(Float, default=0.0)
    currency = Column(String(10), default="EUR")

    # Metadata
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # AI Generation metadata
    generated_by_ai = Column(Boolean, default=False)
    generation_prompt = Column(Text)  # Original prompt used for AI generation
    ai_model = Column(String(100))  # Model used for generation


class CourseModule(Base):
    """Module/chapter within a course"""
    __tablename__ = "course_modules"

    id = Column(String(50), primary_key=True)
    course_id = Column(String(50), ForeignKey("course_templates.id"), nullable=False)
    course = relationship("CourseTemplate", back_populates="modules")

    # Module definition
    module_number = Column(Integer, nullable=False)  # Order in course
    title = Column(String(300), nullable=False)
    description = Column(Text)
    learning_objectives = Column(JSON)  # List of learning objectives

    # Content
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan")

    # Timing
    estimated_duration_hours = Column(Float)

    # Completion requirements
    requires_quiz = Column(Boolean, default=False)
    requires_project = Column(Boolean, default=False)
    min_passing_score = Column(Float, default=70.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Lesson(Base):
    """Individual lesson within a course module"""
    __tablename__ = "lessons"

    id = Column(String(50), primary_key=True)
    module_id = Column(String(50), ForeignKey("course_modules.id"), nullable=False)
    module = relationship("CourseModule", back_populates="lessons")

    # Lesson definition
    lesson_number = Column(Integer, nullable=False)  # Order in module
    title = Column(String(300), nullable=False)
    lesson_type = Column(String(50), nullable=False)  # "video", "text", "quiz", "exercise", "project"

    # Content
    content = Column(Text)  # Markdown or HTML content
    video_url = Column(String(500))
    duration_minutes = Column(Integer)

    # Resources
    resources = relationship("LessonResource", back_populates="lesson", cascade="all, delete-orphan")

    # Interactive elements
    has_quiz = Column(Boolean, default=False)
    quiz_questions = Column(JSON)  # List of quiz questions
    has_exercise = Column(Boolean, default=False)
    exercise_config = Column(JSON)  # Exercise configuration

    # Completion tracking
    is_required = Column(Boolean, default=True)
    allows_skip = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LessonResource(Base):
    """Downloadable or reference resources for lessons"""
    __tablename__ = "lesson_resources"

    id = Column(String(50), primary_key=True)
    lesson_id = Column(String(50), ForeignKey("lessons.id"), nullable=False)
    lesson = relationship("Lesson", back_populates="resources")

    # Resource details
    title = Column(String(200), nullable=False)
    resource_type = Column(String(50), nullable=False)  # "pdf", "code", "dataset", "link", "image"
    description = Column(Text)

    # Storage
    file_url = Column(String(500))  # URL or path to file
    file_size_bytes = Column(Integer)
    mime_type = Column(String(100))

    # External link
    external_url = Column(String(500))

    # Access control
    is_downloadable = Column(Boolean, default=True)
    requires_enrollment = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CourseEnrollment(Base):
    """User enrollment in a course (for future multi-user support)"""
    __tablename__ = "course_enrollments"

    id = Column(String(50), primary_key=True)
    course_id = Column(String(50), ForeignKey("course_templates.id"), nullable=False)
    user_id = Column(String(100), nullable=False)

    # Enrollment status
    status = Column(String(50), default="active")  # "active", "completed", "dropped", "suspended"
    enrolled_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    # Progress tracking
    progress_percentage = Column(Float, default=0.0)
    current_module_id = Column(String(50))
    current_lesson_id = Column(String(50))
    completed_lessons = Column(JSON)  # List of completed lesson IDs

    # Performance
    total_quiz_score = Column(Float, default=0.0)
    total_quizzes = Column(Integer, default=0)
    avg_quiz_score = Column(Float, default=0.0)

    # Time tracking
    total_time_spent_minutes = Column(Integer, default=0)
    last_accessed_at = Column(DateTime)

    # Certification
    certificate_issued = Column(Boolean, default=False)
    certificate_issued_at = Column(DateTime)
    certificate_url = Column(String(500))

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
