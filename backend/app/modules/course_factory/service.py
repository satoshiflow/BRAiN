"""
Course Factory Service - Sprint 12

Orchestrates course generation with IR governance.
"""

from typing import Optional
import time
from pathlib import Path
import json
from loguru import logger

from app.modules.course_factory.schemas import (
    CourseGenerationRequest,
    CourseGenerationResult,
    CourseOutline,
    CourseQuiz,
    CourseLandingPage,
    CourseMetadata,
)
from app.modules.course_factory.generators import (
    OutlineGenerator,
    LessonGenerator,
    QuizGenerator,
    LandingPageGenerator,
)
from app.modules.ir_governance import (
    IR,
    IRStep,
    IRAction,
    IRProvider,
)


class CourseFactoryService:
    """
    Course Factory orchestration service.

    Responsibilities:
    - Coordinate all generators
    - Generate IR for governance
    - Create evidence packs
    - Handle dry-run vs execute mode
    """

    def __init__(self):
        self.outline_gen = OutlineGenerator()
        self.lesson_gen = LessonGenerator()
        self.quiz_gen = QuizGenerator()
        self.landing_gen = LandingPageGenerator()

        # Storage paths
        self.storage_base = Path("storage/courses")
        self.storage_base.mkdir(parents=True, exist_ok=True)

    async def generate_course(
        self, request: CourseGenerationRequest
    ) -> CourseGenerationResult:
        """
        Generate complete course with IR governance.

        Args:
            request: Course generation request

        Returns:
            CourseGenerationResult

        Raises:
            ValueError: If validation fails
        """
        start_time = time.time()

        logger.info(
            f"[CourseFactory] Starting course generation: '{request.title}' "
            f"(dry_run={request.dry_run})"
        )

        try:
            # Step 1: Generate outline
            metadata = CourseMetadata(
                title=request.title,
                description=request.description,
                language=request.language,
                target_audiences=request.target_audiences,
                full_lessons_count=request.full_lessons_count,
            )

            # Determine template based on title
            template_id = self._detect_template(request.title)

            outline = self.outline_gen.generate_outline(
                metadata=metadata,
                template_id=template_id,
                dry_run=request.dry_run
            )

            # Step 2: Generate full lesson content
            if not request.dry_run:
                for lesson in outline.get_full_lessons():
                    lesson_content = self.lesson_gen.generate_lesson_content(
                        lesson=lesson,
                        language=request.language
                    )
                    lesson.content_markdown = lesson_content.content_markdown

            # Step 3: Generate quiz (if requested)
            quiz = None
            if request.generate_quiz:
                quiz = self.quiz_gen.generate_quiz(
                    outline=outline,
                    question_count=15,
                    language=request.language
                )

            # Step 4: Generate landing page (if requested)
            landing_page = None
            if request.generate_landing_page:
                landing_page = self.landing_gen.generate_landing_page(
                    outline=outline,
                    language=request.language
                )

            # Step 5: Save artifacts (if not dry-run)
            evidence_pack_path = None
            if not request.dry_run:
                evidence_pack_path = self._save_course_artifacts(
                    course_id=metadata.course_id,
                    outline=outline,
                    quiz=quiz,
                    landing_page=landing_page,
                )

            # Step 6: Deploy to staging (if requested)
            deployed = False
            staging_url = None
            if request.deploy_to_staging and not request.dry_run:
                staging_url = await self._deploy_to_staging(
                    request=request,
                    outline=outline,
                    landing_page=landing_page,
                )
                deployed = True

            # Compute execution time
            execution_time = time.time() - start_time

            # Create result
            result = CourseGenerationResult(
                success=True,
                course_id=metadata.course_id,
                outline=outline,
                quiz=quiz,
                landing_page=landing_page,
                deployed=deployed,
                staging_url=staging_url,
                evidence_pack_path=evidence_pack_path,
                ir_hash=None,  # Will be set by IR governance
                total_modules=len(outline.modules),
                total_lessons=outline.total_lessons,
                full_lessons_generated=len(outline.get_full_lessons()),
                quiz_questions_count=len(quiz.questions) if quiz else 0,
                execution_time_seconds=execution_time,
            )

            logger.info(
                f"[CourseFactory] Course generation completed: {result.course_id} "
                f"({execution_time:.2f}s)"
            )

            return result

        except Exception as e:
            logger.error(f"[CourseFactory] Course generation failed: {e}")

            # Return error result
            return CourseGenerationResult(
                success=False,
                course_id="",
                total_modules=0,
                total_lessons=0,
                full_lessons_generated=0,
                execution_time_seconds=time.time() - start_time,
                errors=[str(e)],
            )

    def generate_ir(
        self, request: CourseGenerationRequest
    ) -> IR:
        """
        Generate IR for course creation.

        Args:
            request: Course generation request

        Returns:
            IR (Intermediate Representation)
        """
        logger.info(f"[CourseFactory] Generating IR for course '{request.title}'")

        steps = []

        # Step 1: Create course metadata
        steps.append(
            IRStep(
                action=IRAction.COURSE_CREATE,
                provider=IRProvider.COURSE_FACTORY_V1,
                resource=f"course:{request.title}",
                idempotency_key=f"course_create_{request.tenant_id}_{request.title}",
                params={
                    "title": request.title,
                    "description": request.description,
                    "language": request.language.value,
                    "target_audiences": [a.value for a in request.target_audiences],
                },
                description="Create course metadata",
            )
        )

        # Step 2: Generate outline
        steps.append(
            IRStep(
                action=IRAction.COURSE_GENERATE_OUTLINE,
                provider=IRProvider.COURSE_FACTORY_V1,
                resource=f"course:{request.title}:outline",
                idempotency_key=f"course_outline_{request.tenant_id}_{request.title}",
                params={
                    "modules_count": "4-6",
                    "lessons_per_module": "3-5",
                },
                description="Generate course outline",
            )
        )

        # Step 3: Generate lessons
        steps.append(
            IRStep(
                action=IRAction.COURSE_GENERATE_LESSONS,
                provider=IRProvider.COURSE_FACTORY_V1,
                resource=f"course:{request.title}:lessons",
                idempotency_key=f"course_lessons_{request.tenant_id}_{request.title}",
                params={
                    "full_lessons_count": request.full_lessons_count,
                },
                description=f"Generate {request.full_lessons_count} full lessons",
            )
        )

        # Step 4: Generate quiz (if requested)
        if request.generate_quiz:
            steps.append(
                IRStep(
                    action=IRAction.COURSE_GENERATE_QUIZ,
                    provider=IRProvider.COURSE_FACTORY_V1,
                    resource=f"course:{request.title}:quiz",
                    idempotency_key=f"course_quiz_{request.tenant_id}_{request.title}",
                    params={
                        "question_count": 15,
                    },
                    description="Generate course assessment quiz",
                )
            )

        # Step 5: Generate landing page (if requested)
        if request.generate_landing_page:
            steps.append(
                IRStep(
                    action=IRAction.COURSE_GENERATE_LANDING,
                    provider=IRProvider.COURSE_FACTORY_V1,
                    resource=f"course:{request.title}:landing",
                    idempotency_key=f"course_landing_{request.tenant_id}_{request.title}",
                    params={},
                    description="Generate landing page",
                )
            )

        # Step 6: Deploy to staging (if requested)
        if request.deploy_to_staging and request.staging_domain:
            steps.append(
                IRStep(
                    action=IRAction.COURSE_DEPLOY_STAGING,
                    provider=IRProvider.COURSE_FACTORY_V1,
                    resource=f"course:{request.title}:staging",
                    idempotency_key=f"course_deploy_{request.tenant_id}_{request.title}",
                    params={
                        "staging_domain": request.staging_domain,
                    },
                    constraints={
                        "environment": "staging",
                    },
                    description="Deploy course to staging",
                )
            )

        ir = IR(
            tenant_id=request.tenant_id,
            steps=steps,
            intent_summary=f"Generate and deploy online course: {request.title}",
            labels={
                "module": "course_factory",
                "language": request.language.value,
                "dry_run": str(request.dry_run),
            },
        )

        logger.info(f"[CourseFactory] IR generated with {len(steps)} steps")
        return ir

    def _detect_template(self, title: str) -> Optional[str]:
        """Detect template ID from course title."""
        if "Banken" in title or "Banking" in title or "Sparkassen" in title:
            return "banking-alternatives-de"
        return None

    def _save_course_artifacts(
        self,
        course_id: str,
        outline: CourseOutline,
        quiz: Optional[CourseQuiz],
        landing_page: Optional[CourseLandingPage],
    ) -> str:
        """
        Save course artifacts to storage.

        Args:
            course_id: Course ID
            outline: Course outline
            quiz: Course quiz (optional)
            landing_page: Landing page (optional)

        Returns:
            Path to evidence pack
        """
        # Create course directory
        course_dir = self.storage_base / course_id
        course_dir.mkdir(parents=True, exist_ok=True)

        # Save outline
        outline_path = course_dir / "outline.json"
        with open(outline_path, "w", encoding="utf-8") as f:
            json.dump(outline.model_dump(), f, indent=2, ensure_ascii=False, default=str)

        # Save quiz
        if quiz:
            quiz_path = course_dir / "quiz.json"
            with open(quiz_path, "w", encoding="utf-8") as f:
                json.dump(quiz.model_dump(), f, indent=2, ensure_ascii=False, default=str)

        # Save landing page
        if landing_page:
            landing_path = course_dir / "landing.json"
            with open(landing_path, "w", encoding="utf-8") as f:
                json.dump(landing_page.model_dump(), f, indent=2, ensure_ascii=False, default=str)

        # Save full lesson content
        lessons_dir = course_dir / "lessons"
        lessons_dir.mkdir(exist_ok=True)

        for lesson in outline.get_full_lessons():
            if lesson.content_markdown:
                lesson_path = lessons_dir / f"{lesson.lesson_id}.md"
                with open(lesson_path, "w", encoding="utf-8") as f:
                    f.write(lesson.content_markdown)

        logger.info(f"[CourseFactory] Artifacts saved to {course_dir}")
        return str(course_dir)

    async def _deploy_to_staging(
        self,
        request: CourseGenerationRequest,
        outline: CourseOutline,
        landing_page: Optional[CourseLandingPage],
    ) -> str:
        """
        Deploy course to staging via WebGenesis.

        Args:
            request: Course generation request
            outline: Course outline
            landing_page: Landing page content

        Returns:
            Staging URL
        """
        logger.info(
            f"[CourseFactory] Deploying course to staging: {request.staging_domain}"
        )

        # For MVP: Return simulated URL
        # Future: Integrate with WebGenesis deployment
        staging_url = f"https://{request.staging_domain}"

        logger.warning(
            "[CourseFactory] Staging deployment simulated (WebGenesis integration pending)"
        )

        return staging_url


# Singleton
_service: Optional[CourseFactoryService] = None


def get_course_factory_service() -> CourseFactoryService:
    """Get CourseFactory service singleton."""
    global _service
    if _service is None:
        _service = CourseFactoryService()
    return _service
