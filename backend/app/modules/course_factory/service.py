"""
Course Factory Service - Sprint 12 + Sprint 13

Orchestrates course generation with IR governance, workflow management,
content enhancements, and WebGenesis integration.
"""

from typing import Optional, List
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
    CourseLesson,
)
from app.modules.course_factory.generators import (
    OutlineGenerator,
    LessonGenerator,
    QuizGenerator,
    LandingPageGenerator,
)
from app.modules.course_factory.enhanced_schemas import (
    WorkflowState,
    WorkflowTransition,
    EnhancementType,
    EnhancementRequest,
    EnhancementResult,
    EnhancedCourseMetadata,
    WebGenesisTheme,
    WebGenesisSection,
    SEOPack,
    FlashcardDeck,
)
from app.modules.course_factory.workflow import WorkflowStateMachine
from app.modules.course_factory.enhancements import get_enhancement_service
from app.modules.course_factory.webgenesis_integration import (
    get_theme_registry,
    SectionBuilder,
    SEOGenerator,
    PreviewURLGenerator,
)
from app.modules.ir_governance import (
    IR,
    IRStep,
    IRAction,
    IRProvider,
)

# EventStream Integration (Sprint 1)
from backend.mission_control_core.core.event_stream import EventStream, Event, EventType
from datetime import datetime
import uuid


class CourseFactoryService:
    """
    Course Factory orchestration service.

    Responsibilities:
    - Coordinate all generators
    - Generate IR for governance
    - Create evidence packs
    - Handle dry-run vs execute mode
    """

    def __init__(self, event_stream: Optional[EventStream] = None):
        # Sprint 12 generators
        self.outline_gen = OutlineGenerator()
        self.lesson_gen = LessonGenerator()
        self.quiz_gen = QuizGenerator()
        self.landing_gen = LandingPageGenerator()

        # Sprint 13 services
        self.workflow_machine = WorkflowStateMachine()
        self.enhancement_service = get_enhancement_service()
        self.theme_registry = get_theme_registry()
        self.section_builder = SectionBuilder()
        self.seo_generator = SEOGenerator()
        self.preview_generator = PreviewURLGenerator()

        # Storage paths
        self.storage_base = Path("storage/courses")
        self.storage_base.mkdir(parents=True, exist_ok=True)

        # EventStream (Sprint 1 Migration)
        self.event_stream = event_stream

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

            # EVENT: course.generation.requested
            await self._publish_generation_requested(metadata.course_id, request)

            outline = self.outline_gen.generate_outline(
                metadata=metadata,
                template_id=template_id,
                dry_run=request.dry_run
            )

            # EVENT: course.outline.created
            await self._publish_outline_created(metadata.course_id, outline, template_id)

            # Step 2: Generate full lesson content
            if not request.dry_run:
                for idx, lesson in enumerate(outline.get_full_lessons(), start=1):
                    lesson_content = self.lesson_gen.generate_lesson_content(
                        lesson=lesson,
                        language=request.language
                    )
                    lesson.content_markdown = lesson_content.content_markdown

                    # EVENT: course.lesson.generated (for each lesson)
                    await self._publish_lesson_generated(metadata.course_id, lesson, idx)

            # Step 3: Generate quiz (if requested)
            quiz = None
            if request.generate_quiz:
                quiz = self.quiz_gen.generate_quiz(
                    outline=outline,
                    question_count=15,
                    language=request.language
                )

                # EVENT: course.quiz.created
                await self._publish_quiz_created(metadata.course_id, quiz)

            # Step 4: Generate landing page (if requested)
            landing_page = None
            if request.generate_landing_page:
                landing_page = self.landing_gen.generate_landing_page(
                    outline=outline,
                    language=request.language
                )

                # EVENT: course.landing_page.created
                await self._publish_landing_page_created(metadata.course_id, landing_page)

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

                # EVENT: course.deployed.staging
                await self._publish_deployed_staging(
                    metadata.course_id,
                    staging_url,
                    request.staging_domain or "unknown"
                )

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

            # EVENT: course.generation.completed
            await self._publish_generation_completed(result, request.tenant_id)

            return result

        except Exception as e:
            logger.error(f"[CourseFactory] Course generation failed: {e}")

            # EVENT: course.generation.failed
            execution_time = time.time() - start_time
            await self._publish_generation_failed(
                course_id="",  # May not have been created yet
                title=request.title,
                error=e,
                execution_time=execution_time,
                tenant_id=request.tenant_id
            )

            # Return error result
            return CourseGenerationResult(
                success=False,
                course_id="",
                total_modules=0,
                total_lessons=0,
                full_lessons_generated=0,
                execution_time_seconds=execution_time,
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

    # ========================================
    # Sprint 13: Workflow Management
    # ========================================

    async def transition_workflow(
        self,
        course_id: str,
        from_state: WorkflowState,
        to_state: WorkflowState,
        actor: str,
        reason: Optional[str] = None,
        hitl_approval: bool = False,
    ) -> WorkflowTransition:
        """
        Transition course workflow state.

        Args:
            course_id: Course ID
            from_state: Current state
            to_state: Target state
            actor: Who triggered the transition
            reason: Optional reason for transition
            hitl_approval: Whether human approved (for review→publish_ready)

        Returns:
            WorkflowTransition

        Raises:
            ValueError: If transition is invalid
        """
        logger.info(
            f"[CourseFactory] Workflow transition requested: {course_id} "
            f"{from_state.value} → {to_state.value} (actor={actor})"
        )

        # Perform transition
        transition = self.workflow_machine.transition(
            current_state=from_state,
            target_state=to_state,
            actor=actor,
            reason=reason,
            hitl_approval=hitl_approval,
        )

        # Save transition to evidence pack
        self._save_workflow_transition(course_id, transition)

        logger.info(
            f"[CourseFactory] Workflow transition completed: {transition.transition_id}"
        )

        return transition

    async def rollback_workflow(
        self,
        course_id: str,
        transition_id: str,
        actor: str,
        reason: str,
    ) -> WorkflowTransition:
        """
        Rollback a workflow transition.

        Args:
            course_id: Course ID
            transition_id: Transition to rollback
            actor: Who triggered the rollback
            reason: Reason for rollback

        Returns:
            WorkflowTransition (rollback)
        """
        logger.info(
            f"[CourseFactory] Workflow rollback requested: {course_id} "
            f"(transition={transition_id}, actor={actor})"
        )

        # Load original transition (from evidence pack)
        original_transition = self._load_workflow_transition(course_id, transition_id)

        # Perform rollback
        rollback_transition = self.workflow_machine.rollback_transition(
            original_transition=original_transition,
            actor=actor,
            reason=reason,
        )

        # Save rollback transition
        self._save_workflow_transition(course_id, rollback_transition)

        logger.info(
            f"[CourseFactory] Workflow rollback completed: {rollback_transition.transition_id}"
        )

        return rollback_transition

    # ========================================
    # Sprint 13: Content Enhancements
    # ========================================

    async def enhance_content(
        self,
        request: EnhancementRequest,
        lessons: List[CourseLesson],
    ) -> EnhancementResult:
        """
        Enhance course content with LLM-generated additions.

        Args:
            request: Enhancement request
            lessons: Lessons to enhance

        Returns:
            EnhancementResult
        """
        logger.info(
            f"[CourseFactory] Content enhancement requested: {request.course_id} "
            f"(types={[t.value for t in request.enhancement_types]})"
        )

        # Process enhancement request
        result = await self.enhancement_service.process_enhancement_request(
            request=request,
            lessons=lessons,
        )

        # Save enhancements to evidence pack (if not dry-run)
        if not request.dry_run:
            self._save_enhancements(request.course_id, result)

        logger.info(
            f"[CourseFactory] Content enhancement completed: {result.total_enhancements} "
            f"enhancements generated (validated: {result.validated_count})"
        )

        return result

    # ========================================
    # Sprint 13: WebGenesis Integration
    # ========================================

    async def bind_theme(
        self,
        course_id: str,
        theme_id: str,
        custom_colors: Optional[dict] = None,
    ) -> WebGenesisTheme:
        """
        Bind WebGenesis theme to course.

        Args:
            course_id: Course ID
            theme_id: Theme ID from registry
            custom_colors: Optional color overrides

        Returns:
            WebGenesisTheme

        Raises:
            ValueError: If theme not found
        """
        logger.info(
            f"[CourseFactory] Binding theme to course: {course_id} (theme={theme_id})"
        )

        # Get theme from registry
        theme = self.theme_registry.get_theme(theme_id)

        if not theme:
            raise ValueError(f"Theme '{theme_id}' not found in registry")

        # Apply custom colors (if provided)
        if custom_colors:
            theme.primary_color = custom_colors.get("primary", theme.primary_color)
            theme.secondary_color = custom_colors.get("secondary", theme.secondary_color)
            theme.accent_color = custom_colors.get("accent", theme.accent_color)

        # Save theme binding to evidence pack
        self._save_theme_binding(course_id, theme)

        logger.info(f"[CourseFactory] Theme bound successfully: {theme_id}")

        return theme

    async def build_sections(
        self,
        course_id: str,
        outline: CourseOutline,
        landing_page: Optional[CourseLandingPage] = None,
    ) -> List[WebGenesisSection]:
        """
        Build WebGenesis sections from course data.

        Args:
            course_id: Course ID
            outline: Course outline
            landing_page: Optional landing page data

        Returns:
            List of WebGenesisSection
        """
        logger.info(
            f"[CourseFactory] Building WebGenesis sections: {course_id}"
        )

        # Build sections
        sections = self.section_builder.build_sections(outline, landing_page)

        # Save sections to evidence pack
        self._save_sections(course_id, sections)

        logger.info(
            f"[CourseFactory] Sections built: {len(sections)} sections"
        )

        return sections

    async def generate_seo_pack(
        self,
        course_id: str,
        outline: CourseOutline,
        keywords: Optional[List[str]] = None,
    ) -> SEOPack:
        """
        Generate SEO pack for course.

        Args:
            course_id: Course ID
            outline: Course outline
            keywords: Optional additional keywords

        Returns:
            SEOPack
        """
        logger.info(
            f"[CourseFactory] Generating SEO pack: {course_id}"
        )

        # Generate SEO metadata
        seo_pack = self.seo_generator.generate_seo_pack(outline, keywords)

        # Save SEO pack to evidence pack
        self._save_seo_pack(course_id, seo_pack)

        logger.info(
            f"[CourseFactory] SEO pack generated: {len(seo_pack.keywords)} keywords"
        )

        return seo_pack

    async def generate_preview_url(
        self,
        course_id: str,
        version: str = "latest",
    ) -> str:
        """
        Generate preview URL for course.

        Args:
            course_id: Course ID
            version: Version identifier (default: "latest")

        Returns:
            Preview URL
        """
        logger.info(
            f"[CourseFactory] Generating preview URL: {course_id} (version={version})"
        )

        # Generate preview URL
        preview_url = self.preview_generator.generate_preview_url(
            course_id=course_id,
            version=version,
        )

        logger.info(f"[CourseFactory] Preview URL: {preview_url}")

        return preview_url

    # ========================================
    # Sprint 13: Evidence Pack Helpers
    # ========================================

    def _save_workflow_transition(
        self,
        course_id: str,
        transition: WorkflowTransition,
    ):
        """Save workflow transition to evidence pack."""
        course_dir = self.storage_base / course_id
        transitions_dir = course_dir / "workflow_transitions"
        transitions_dir.mkdir(parents=True, exist_ok=True)

        transition_path = transitions_dir / f"{transition.transition_id}.json"
        with open(transition_path, "w", encoding="utf-8") as f:
            json.dump(transition.model_dump(), f, indent=2, ensure_ascii=False, default=str)

        logger.debug(f"[CourseFactory] Workflow transition saved: {transition_path}")

    def _load_workflow_transition(
        self,
        course_id: str,
        transition_id: str,
    ) -> WorkflowTransition:
        """Load workflow transition from evidence pack."""
        transition_path = (
            self.storage_base / course_id / "workflow_transitions" / f"{transition_id}.json"
        )

        if not transition_path.exists():
            raise ValueError(f"Transition '{transition_id}' not found")

        with open(transition_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return WorkflowTransition(**data)

    def _save_enhancements(
        self,
        course_id: str,
        result: EnhancementResult,
    ):
        """Save enhancement result to evidence pack."""
        course_dir = self.storage_base / course_id
        enhancements_dir = course_dir / "enhancements"
        enhancements_dir.mkdir(parents=True, exist_ok=True)

        result_path = enhancements_dir / f"enhancement_{int(time.time())}.json"
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, indent=2, ensure_ascii=False, default=str)

        logger.debug(f"[CourseFactory] Enhancements saved: {result_path}")

    def _save_theme_binding(
        self,
        course_id: str,
        theme: WebGenesisTheme,
    ):
        """Save theme binding to evidence pack."""
        course_dir = self.storage_base / course_id
        course_dir.mkdir(parents=True, exist_ok=True)

        theme_path = course_dir / "webgenesis_theme.json"
        with open(theme_path, "w", encoding="utf-8") as f:
            json.dump(theme.model_dump(), f, indent=2, ensure_ascii=False, default=str)

        logger.debug(f"[CourseFactory] Theme binding saved: {theme_path}")

    def _save_sections(
        self,
        course_id: str,
        sections: List[WebGenesisSection],
    ):
        """Save WebGenesis sections to evidence pack."""
        course_dir = self.storage_base / course_id
        course_dir.mkdir(parents=True, exist_ok=True)

        sections_path = course_dir / "webgenesis_sections.json"
        sections_data = [s.model_dump() for s in sections]

        with open(sections_path, "w", encoding="utf-8") as f:
            json.dump(sections_data, f, indent=2, ensure_ascii=False, default=str)

        logger.debug(f"[CourseFactory] Sections saved: {sections_path}")

    def _save_seo_pack(
        self,
        course_id: str,
        seo_pack: SEOPack,
    ):
        """Save SEO pack to evidence pack."""
        course_dir = self.storage_base / course_id
        course_dir.mkdir(parents=True, exist_ok=True)

        seo_path = course_dir / "seo_pack.json"
        with open(seo_path, "w", encoding="utf-8") as f:
            json.dump(seo_pack.model_dump(), f, indent=2, ensure_ascii=False, default=str)

        logger.debug(f"[CourseFactory] SEO pack saved: {seo_path}")

    # ========================================================================
    # EventStream Integration (Sprint 1)
    # ========================================================================

    async def _publish_event_safe(self, event: Event) -> None:
        """
        Publish event with error handling (non-blocking).

        Event publishing failures MUST NOT break business logic.
        """
        if self.event_stream is None:
            logger.debug("[CourseFactory] EventStream not available, skipping event publish")
            return

        try:
            await self.event_stream.publish_event(event)
            logger.info(f"[CourseFactory] Event published: {event.type.value} (id={event.id})")
        except Exception as e:
            # Log error, but DO NOT raise
            logger.error(
                f"[CourseFactory] Event publishing failed: {event.type.value} (id={event.id})",
                exc_info=True,
                extra={"event_id": event.id, "event_type": event.type.value}
            )

    async def _publish_generation_requested(
        self,
        course_id: str,
        request: CourseGenerationRequest
    ) -> None:
        """Publish course.generation.requested event."""
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.COURSE_GENERATION_REQUESTED,
            source="course_factory_service",
            target=None,
            payload={
                "course_id": course_id,
                "title": request.title,
                "description": request.description,
                "language": request.language.value,
                "target_audiences": [a.value for a in request.target_audiences],
                "tenant_id": request.tenant_id,
                "dry_run": request.dry_run,
                "full_lessons_count": request.full_lessons_count,
            },
            timestamp=datetime.utcnow(),
            tenant_id=request.tenant_id,
            meta={
                "schema_version": 1,
                "producer": "course_factory_service",
                "source_module": "course_factory"
            }
        )
        await self._publish_event_safe(event)

    async def _publish_outline_created(
        self,
        course_id: str,
        outline: CourseOutline,
        template_id: str
    ) -> None:
        """Publish course.outline.created event."""
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.COURSE_OUTLINE_CREATED,
            source="course_factory_service",
            target=None,
            payload={
                "course_id": course_id,
                "modules_count": len(outline.modules),
                "total_lessons": outline.total_lessons,
                "template_id": template_id,
            },
            timestamp=datetime.utcnow(),
            meta={
                "schema_version": 1,
                "producer": "course_factory_service",
                "source_module": "course_factory"
            }
        )
        await self._publish_event_safe(event)

    async def _publish_lesson_generated(
        self,
        course_id: str,
        lesson: CourseLesson,
        lesson_index: int
    ) -> None:
        """Publish course.lesson.generated event."""
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.COURSE_LESSON_GENERATED,
            source="course_factory_service",
            target=None,
            payload={
                "course_id": course_id,
                "lesson_id": lesson.lesson_id,
                "lesson_title": lesson.title,
                "module_id": lesson.module_id,
                "content_length": len(lesson.content_markdown or ""),
                "lesson_index": lesson_index,
            },
            timestamp=datetime.utcnow(),
            meta={
                "schema_version": 1,
                "producer": "course_factory_service",
                "source_module": "course_factory"
            }
        )
        await self._publish_event_safe(event)

    async def _publish_quiz_created(
        self,
        course_id: str,
        quiz: CourseQuiz
    ) -> None:
        """Publish course.quiz.created event."""
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.COURSE_QUIZ_CREATED,
            source="course_factory_service",
            target=None,
            payload={
                "course_id": course_id,
                "quiz_id": quiz.quiz_id,
                "question_count": len(quiz.questions),
                "question_ids": [q.question_id for q in quiz.questions],
            },
            timestamp=datetime.utcnow(),
            meta={
                "schema_version": 1,
                "producer": "course_factory_service",
                "source_module": "course_factory"
            }
        )
        await self._publish_event_safe(event)

    async def _publish_landing_page_created(
        self,
        course_id: str,
        landing_page: CourseLandingPage
    ) -> None:
        """Publish course.landing_page.created event."""
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.COURSE_LANDING_PAGE_CREATED,
            source="course_factory_service",
            target=None,
            payload={
                "course_id": course_id,
                "landing_page_id": landing_page.landing_page_id,
                "sections_count": len(landing_page.sections),
                "has_hero": hasattr(landing_page, 'hero_section'),
                "has_pricing": hasattr(landing_page, 'pricing_section'),
            },
            timestamp=datetime.utcnow(),
            meta={
                "schema_version": 1,
                "producer": "course_factory_service",
                "source_module": "course_factory"
            }
        )
        await self._publish_event_safe(event)

    async def _publish_generation_completed(
        self,
        result: CourseGenerationResult,
        tenant_id: str
    ) -> None:
        """Publish course.generation.completed event."""
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.COURSE_GENERATION_COMPLETED,
            source="course_factory_service",
            target=None,
            payload={
                "course_id": result.course_id,
                "total_modules": result.total_modules,
                "total_lessons": result.total_lessons,
                "full_lessons_generated": result.full_lessons_generated,
                "quiz_questions_count": result.quiz_questions_count,
                "evidence_pack_path": result.evidence_pack_path,
                "execution_time_seconds": result.execution_time_seconds,
                "deployed": result.deployed,
                "staging_url": result.staging_url,
            },
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id,
            meta={
                "schema_version": 1,
                "producer": "course_factory_service",
                "source_module": "course_factory"
            }
        )
        await self._publish_event_safe(event)

    async def _publish_generation_failed(
        self,
        course_id: str,
        title: str,
        error: Exception,
        execution_time: float,
        tenant_id: str
    ) -> None:
        """Publish course.generation.failed event."""
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.COURSE_GENERATION_FAILED,
            source="course_factory_service",
            target=None,
            payload={
                "course_id": course_id,
                "title": title,
                "error_message": str(error),
                "error_type": type(error).__name__,
                "execution_time_seconds": execution_time,
            },
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id,
            severity="ERROR",
            meta={
                "schema_version": 1,
                "producer": "course_factory_service",
                "source_module": "course_factory"
            }
        )
        await self._publish_event_safe(event)

    async def _publish_deployed_staging(
        self,
        course_id: str,
        staging_url: str,
        staging_domain: str
    ) -> None:
        """Publish course.deployed.staging event."""
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.COURSE_DEPLOYED_STAGING,
            source="course_factory_service",
            target=None,
            payload={
                "course_id": course_id,
                "staging_url": staging_url,
                "staging_domain": staging_domain,
                "deployed_at": datetime.utcnow().isoformat(),
            },
            timestamp=datetime.utcnow(),
            meta={
                "schema_version": 1,
                "producer": "course_factory_service",
                "source_module": "course_factory"
            }
        )
        await self._publish_event_safe(event)


# Singleton
_service: Optional[CourseFactoryService] = None


def get_course_factory_service() -> CourseFactoryService:
    """Get CourseFactory service singleton."""
    global _service
    if _service is None:
        _service = CourseFactoryService()
    return _service
