"""
Course Factory Module - Sprint 12

Generates complete online courses with IR governance.

Components:
- schemas: Course models (outline, lessons, quiz, landing page)
- generators: Content generation (outline, lessons, quiz, landing)
- ir_actions: IR-governed course creation actions
- service: Course orchestration service
- evidence: Evidence pack generation
- router: API endpoints
"""

from app.modules.course_factory.schemas import (
    CourseOutline,
    CourseModule,
    CourseLesson,
    CourseLessonContent,
    CourseQuiz,
    QuizQuestion,
    CourseLandingPage,
    CourseMetadata,
    CourseGenerationRequest,
    CourseGenerationResult,
)
from app.modules.course_factory.service import (
    CourseFactoryService,
    get_course_factory_service,
)

__all__ = [
    # Schemas
    "CourseOutline",
    "CourseModule",
    "CourseLesson",
    "CourseLessonContent",
    "CourseQuiz",
    "QuizQuestion",
    "CourseLandingPage",
    "CourseMetadata",
    "CourseGenerationRequest",
    "CourseGenerationResult",
    # Service
    "CourseFactoryService",
    "get_course_factory_service",
]
