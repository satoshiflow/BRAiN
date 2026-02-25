"""
Course Factory API - Course creation and curriculum management

Provides 8 endpoints for creating, managing, and publishing courses.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from app.models.courses import CourseTemplate, CourseModule, Lesson, LessonResource
from app.core.database import get_db
from app.core.auth_deps import require_auth

router = APIRouter(prefix="/api/courses", tags=["course-factory"])


# Pydantic Schemas
class LessonCreate(BaseModel):
    lesson_number: int
    title: str
    lesson_type: str  # "video", "text", "quiz", "exercise", "project"
    content: Optional[str] = None
    video_url: Optional[str] = None
    duration_minutes: Optional[int] = None
    has_quiz: bool = False
    quiz_questions: Optional[list] = None
    has_exercise: bool = False
    exercise_config: Optional[dict] = None
    is_required: bool = True
    allows_skip: bool = False


class LessonResponse(BaseModel):
    id: str
    module_id: str
    lesson_number: int
    title: str
    lesson_type: str
    content: Optional[str]
    video_url: Optional[str]
    duration_minutes: Optional[int]
    has_quiz: bool
    quiz_questions: Optional[list]
    has_exercise: bool
    exercise_config: Optional[dict]
    is_required: bool
    allows_skip: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModuleCreate(BaseModel):
    module_number: int
    title: str
    description: Optional[str] = None
    learning_objectives: Optional[list] = None
    estimated_duration_hours: Optional[float] = None
    requires_quiz: bool = False
    requires_project: bool = False
    min_passing_score: float = 70.0
    lessons: List[LessonCreate] = Field(default_factory=list)


class ModuleResponse(BaseModel):
    id: str
    course_id: str
    module_number: int
    title: str
    description: Optional[str]
    learning_objectives: Optional[list]
    estimated_duration_hours: Optional[float]
    requires_quiz: bool
    requires_project: bool
    min_passing_score: float
    created_at: datetime
    updated_at: datetime
    lessons: List[LessonResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class CourseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    category: Optional[str] = None
    difficulty_level: Optional[str] = "beginner"
    language: str = "en"
    estimated_duration_hours: Optional[float] = None
    prerequisites: Optional[list] = None
    modules: List[ModuleCreate] = Field(default_factory=list)
    is_free: bool = True
    price: float = 0.0
    currency: str = "EUR"
    generated_by_ai: bool = False
    generation_prompt: Optional[str] = None
    ai_model: Optional[str] = None


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    difficulty_level: Optional[str] = None
    language: Optional[str] = None
    estimated_duration_hours: Optional[float] = None
    prerequisites: Optional[list] = None
    status: Optional[str] = None
    is_free: Optional[bool] = None
    price: Optional[float] = None


class CourseResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    category: Optional[str]
    difficulty_level: Optional[str]
    language: str
    estimated_duration_hours: Optional[float]
    prerequisites: Optional[list]
    status: str
    published_at: Optional[datetime]
    version: int
    total_enrollments: int
    completion_rate: float
    avg_rating: float
    total_reviews: int
    is_free: bool
    price: float
    currency: str
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    generated_by_ai: bool
    generation_prompt: Optional[str]
    ai_model: Optional[str]
    modules: List[ModuleResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class CourseListResponse(BaseModel):
    total: int
    courses: List[CourseResponse]


class PublishRequest(BaseModel):
    publish: bool = True


# Helper Functions
def generate_id(prefix: str) -> str:
    """Generate unique ID with prefix"""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# API Endpoints

@router.post("/templates", response_model=CourseResponse, status_code=201)
async def create_course(
    course: CourseCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_auth)
):
    """
    Create a new course template with modules and lessons

    **Category:** CRUD
    **Example:**
    ```json
    {
      "title": "Python Programming Fundamentals",
      "description": "Learn Python from scratch",
      "category": "programming",
      "difficulty_level": "beginner",
      "modules": [
        {
          "module_number": 1,
          "title": "Getting Started",
          "lessons": [
            {
              "lesson_number": 1,
              "title": "Installing Python",
              "lesson_type": "video",
              "duration_minutes": 15
            }
          ]
        }
      ]
    }
    ```
    """
    try:
        # Create course template
        db_course = CourseTemplate(
            id=generate_id("course"),
            title=course.title,
            description=course.description,
            category=course.category,
            difficulty_level=course.difficulty_level,
            language=course.language,
            estimated_duration_hours=course.estimated_duration_hours,
            prerequisites=course.prerequisites,
            is_free=course.is_free,
            price=course.price,
            currency=course.currency,
            generated_by_ai=course.generated_by_ai,
            generation_prompt=course.generation_prompt,
            ai_model=course.ai_model,
            created_by="api_user"
        )
        db.add(db_course)

        # Create modules and lessons
        db_modules = []
        for module in course.modules:
            db_module = CourseModule(
                id=generate_id("module"),
                course_id=db_course.id,
                module_number=module.module_number,
                title=module.title,
                description=module.description,
                learning_objectives=module.learning_objectives,
                estimated_duration_hours=module.estimated_duration_hours,
                requires_quiz=module.requires_quiz,
                requires_project=module.requires_project,
                min_passing_score=module.min_passing_score
            )
            db.add(db_module)
            db_modules.append(db_module)

            # Create lessons for this module
            for lesson in module.lessons:
                db_lesson = Lesson(
                    id=generate_id("lesson"),
                    module_id=db_module.id,
                    lesson_number=lesson.lesson_number,
                    title=lesson.title,
                    lesson_type=lesson.lesson_type,
                    content=lesson.content,
                    video_url=lesson.video_url,
                    duration_minutes=lesson.duration_minutes,
                    has_quiz=lesson.has_quiz,
                    quiz_questions=lesson.quiz_questions,
                    has_exercise=lesson.has_exercise,
                    exercise_config=lesson.exercise_config,
                    is_required=lesson.is_required,
                    allows_skip=lesson.allows_skip
                )
                db.add(db_lesson)

        await db.commit()
        await db.refresh(db_course)

        # Load modules and lessons
        modules_result = await db.execute(
            select(CourseModule).where(CourseModule.course_id == db_course.id).order_by(CourseModule.module_number)
        )
        db_course.modules = modules_result.scalars().all()

        for module in db_course.modules:
            lessons_result = await db.execute(
                select(Lesson).where(Lesson.module_id == module.id).order_by(Lesson.lesson_number)
            )
            module.lessons = lessons_result.scalars().all()

        return db_course
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create course: {str(e)}")


@router.get("/templates", response_model=CourseListResponse)
async def list_courses(
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_auth)
):
    """
    List all course templates with optional filtering

    **Query Parameters:**
    - category: Filter by course category
    - difficulty: Filter by difficulty level
    - status: Filter by publishing status
    - limit: Max results (default 50)
    - offset: Pagination offset (default 0)
    """
    try:
        # Build query
        query = select(CourseTemplate)
        if category:
            query = query.where(CourseTemplate.category == category)
        if difficulty:
            query = query.where(CourseTemplate.difficulty_level == difficulty)
        if status:
            query = query.where(CourseTemplate.status == status)

        # Get total count
        count_query = select(func.count()).select_from(CourseTemplate)
        if category:
            count_query = count_query.where(CourseTemplate.category == category)
        if difficulty:
            count_query = count_query.where(CourseTemplate.difficulty_level == difficulty)
        if status:
            count_query = count_query.where(CourseTemplate.status == status)

        total = await db.scalar(count_query)

        # Get courses with pagination
        query = query.offset(offset).limit(limit).order_by(CourseTemplate.created_at.desc())
        result = await db.execute(query)
        courses = result.scalars().all()

        # Load modules and lessons for each course
        for course in courses:
            modules_result = await db.execute(
                select(CourseModule).where(CourseModule.course_id == course.id).order_by(CourseModule.module_number)
            )
            course.modules = modules_result.scalars().all()

            for module in course.modules:
                lessons_result = await db.execute(
                    select(Lesson).where(Lesson.module_id == module.id).order_by(Lesson.lesson_number)
                )
                module.lessons = lessons_result.scalars().all()

        return CourseListResponse(total=total or 0, courses=courses)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list courses: {str(e)}")


@router.get("/templates/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_auth)
):
    """Get course template by ID with all modules and lessons"""
    try:
        result = await db.execute(
            select(CourseTemplate).where(CourseTemplate.id == course_id)
        )
        course = result.scalar_one_or_none()

        if not course:
            raise HTTPException(status_code=404, detail=f"Course {course_id} not found")

        # Load modules and lessons
        modules_result = await db.execute(
            select(CourseModule).where(CourseModule.course_id == course_id).order_by(CourseModule.module_number)
        )
        course.modules = modules_result.scalars().all()

        for module in course.modules:
            lessons_result = await db.execute(
                select(Lesson).where(Lesson.module_id == module.id).order_by(Lesson.lesson_number)
            )
            module.lessons = lessons_result.scalars().all()

        return course
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get course: {str(e)}")


@router.put("/templates/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    course_update: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_auth)
):
    """Update course template metadata (not modules/lessons)"""
    try:
        # Check course exists
        result = await db.execute(
            select(CourseTemplate).where(CourseTemplate.id == course_id)
        )
        course = result.scalar_one_or_none()

        if not course:
            raise HTTPException(status_code=404, detail=f"Course {course_id} not found")

        # Update fields
        update_data = course_update.model_dump(exclude_unset=True)
        if update_data:
            await db.execute(
                update(CourseTemplate).where(CourseTemplate.id == course_id).values(**update_data)
            )
            await db.commit()
            await db.refresh(course)

        # Load modules and lessons
        modules_result = await db.execute(
            select(CourseModule).where(CourseModule.course_id == course_id).order_by(CourseModule.module_number)
        )
        course.modules = modules_result.scalars().all()

        for module in course.modules:
            lessons_result = await db.execute(
                select(Lesson).where(Lesson.module_id == module.id).order_by(Lesson.lesson_number)
            )
            module.lessons = lessons_result.scalars().all()

        return course
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update course: {str(e)}")


@router.delete("/templates/{course_id}", status_code=204)
async def delete_course(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_auth)
):
    """Delete course template (cascades to modules, lessons, resources)"""
    try:
        result = await db.execute(
            select(CourseTemplate).where(CourseTemplate.id == course_id)
        )
        course = result.scalar_one_or_none()

        if not course:
            raise HTTPException(status_code=404, detail=f"Course {course_id} not found")

        await db.execute(
            delete(CourseTemplate).where(CourseTemplate.id == course_id)
        )
        await db.commit()

        return None
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete course: {str(e)}")


@router.post("/templates/{course_id}/publish", response_model=CourseResponse)
async def publish_course(
    course_id: str,
    publish_request: PublishRequest,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_auth)
):
    """
    Publish or unpublish a course template

    **Example:**
    ```json
    {
      "publish": true
    }
    ```
    """
    try:
        result = await db.execute(
            select(CourseTemplate).where(CourseTemplate.id == course_id)
        )
        course = result.scalar_one_or_none()

        if not course:
            raise HTTPException(status_code=404, detail=f"Course {course_id} not found")

        new_status = "published" if publish_request.publish else "draft"
        published_at = datetime.utcnow() if publish_request.publish else None

        await db.execute(
            update(CourseTemplate)
            .where(CourseTemplate.id == course_id)
            .values(status=new_status, published_at=published_at)
        )
        await db.commit()
        await db.refresh(course)

        # Load modules and lessons
        modules_result = await db.execute(
            select(CourseModule).where(CourseModule.course_id == course_id).order_by(CourseModule.module_number)
        )
        course.modules = modules_result.scalars().all()

        for module in course.modules:
            lessons_result = await db.execute(
                select(Lesson).where(Lesson.module_id == module.id).order_by(Lesson.lesson_number)
            )
            module.lessons = lessons_result.scalars().all()

        return course
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to publish course: {str(e)}")


@router.get("/stats")
async def get_course_stats(db: AsyncSession = Depends(get_db)):
    """Get course factory statistics"""
    try:
        # Count courses by status
        total = await db.scalar(select(func.count()).select_from(CourseTemplate))
        published = await db.scalar(
            select(func.count()).select_from(CourseTemplate).where(CourseTemplate.status == "published")
        )
        draft = await db.scalar(
            select(func.count()).select_from(CourseTemplate).where(CourseTemplate.status == "draft")
        )

        # Count modules and lessons
        total_modules = await db.scalar(select(func.count()).select_from(CourseModule))
        total_lessons = await db.scalar(select(func.count()).select_from(Lesson))

        return {
            "total_courses": total or 0,
            "published_courses": published or 0,
            "draft_courses": draft or 0,
            "total_modules": total_modules or 0,
            "total_lessons": total_lessons or 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/info")
async def get_course_factory_info():
    """Get Course Factory system information"""
    return {
        "name": "Course Factory",
        "version": "1.0.0",
        "description": "Course creation and curriculum management",
        "features": [
            "Course template builder",
            "Module and lesson management",
            "Multi-format content support",
            "Quiz and exercise integration",
            "AI-powered course generation"
        ],
        "endpoints": 8,
        "database": "PostgreSQL"
    }
