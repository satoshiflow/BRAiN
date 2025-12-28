"""
Course Factory API Router - Sprint 12 + Sprint 13

FastAPI endpoints for course generation with IR governance,
workflow management, content enhancements, and WebGenesis integration.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
from loguru import logger

# EventStream Integration (Sprint 1)
from backend.mission_control_core.core.event_stream import EventStream

from app.modules.course_factory.schemas import (
    CourseGenerationRequest,
    CourseGenerationResult,
    CourseOutline,
    CourseLandingPage,
)
from app.modules.course_factory.enhanced_schemas import (
    WorkflowState,
    WorkflowTransition,
    EnhancementType,
    EnhancementRequest,
    EnhancementResult,
    WebGenesisTheme,
    WebGenesisSection,
    SEOPack,
)
from app.modules.course_factory.service import (
    CourseFactoryService,
    get_course_factory_service,
)
from app.modules.ir_governance import (
    IR,
    IRValidationResult,
    get_validator,
)
from app.modules.autonomous_pipeline.ir_gateway import (
    get_ir_gateway,
    IRGatewayResult,
)

router = APIRouter(prefix="/api/course-factory", tags=["course-factory"])


# Dependency Injection (Sprint 1)
def get_course_factory_service_with_events(request: Request) -> CourseFactoryService:
    """
    Get CourseFactoryService with EventStream injection.

    EventStream is retrieved from app.state (set in main.py startup).
    """
    event_stream: Optional[EventStream] = getattr(request.app.state, "event_stream", None)
    return CourseFactoryService(event_stream=event_stream)


@router.get("/info")
async def get_info() -> Dict[str, Any]:
    """Get CourseFactory module information."""
    return {
        "name": "CourseFactory",
        "version": "2.0.0",
        "description": "Online course generation with IR governance, workflow, enhancements, and WebGenesis",
        "sprint": "Sprint 12 + Sprint 13",
        "features": [
            # Sprint 12
            "Course outline generation (4-6 modules, 3-5 lessons each)",
            "Full lesson content generation (Markdown)",
            "Quiz generation (10-15 MCQs)",
            "Landing page generation",
            "IR governance integration",
            "Dry-run support",
            "Evidence pack generation",
            # Sprint 13
            "Author workflow (draft → review → publish_ready → published)",
            "LLM-enhanced content (examples, summaries, flashcards)",
            "Content validation and diff-audit",
            "WebGenesis deep integration (themes, sections, SEO)",
            "Preview URL generation",
        ],
        "supported_languages": ["de", "en", "fr", "es"],
        "ir_actions": [
            # Sprint 12
            "course.create",
            "course.generate_outline",
            "course.generate_lessons",
            "course.generate_quiz",
            "course.generate_landing",
            "course.deploy_staging",
            # Sprint 13
            "course.enhance_examples",
            "course.enhance_summaries",
            "course.generate_flashcards",
            "course.workflow_transition",
            "webgenesis.bind_theme",
            "webgenesis.build_sections",
            "webgenesis.apply_seo",
            "webgenesis.preview",
        ],
        "endpoints": {
            # Sprint 12
            "GET /api/course-factory/info": "Module information",
            "POST /api/course-factory/generate": "Generate course (with IR)",
            "POST /api/course-factory/generate-ir": "Generate IR only (dry-run)",
            "POST /api/course-factory/validate-ir": "Validate IR without execution",
            "POST /api/course-factory/dry-run": "Dry-run course generation",
            "GET /api/course-factory/health": "Health check",
            # Sprint 13
            "POST /api/course-factory/workflow/transition": "Transition workflow state",
            "POST /api/course-factory/workflow/rollback": "Rollback workflow transition",
            "POST /api/course-factory/enhance": "Enhance content with LLM",
            "POST /api/course-factory/webgenesis/bind-theme": "Bind WebGenesis theme",
            "POST /api/course-factory/webgenesis/build-sections": "Build WebGenesis sections",
            "POST /api/course-factory/webgenesis/generate-seo": "Generate SEO pack",
            "POST /api/course-factory/webgenesis/preview": "Generate preview URL",
        },
    }


@router.post("/generate-ir")
async def generate_ir_only(
    request: CourseGenerationRequest,
    service: CourseFactoryService = Depends(get_course_factory_service_with_events),
) -> IR:
    """
    Generate IR for course creation (dry-run mode).

    Returns canonical IR without executing the course generation.
    Useful for inspecting what will be done before approval.

    Args:
        request: Course generation request

    Returns:
        IR (Intermediate Representation)
    """
    try:
        logger.info(f"[CourseFactory API] Generating IR for '{request.title}'")
        ir = service.generate_ir(request)
        return ir

    except Exception as e:
        logger.error(f"[CourseFactory API] IR generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"IR generation failed: {str(e)}")


@router.post("/validate-ir")
async def validate_ir(
    ir: IR,
) -> IRValidationResult:
    """
    Validate IR without executing.

    Checks:
    - Schema compliance
    - Policy violations
    - Risk tier computation
    - Approval requirements

    Args:
        ir: IR to validate

    Returns:
        IRValidationResult (PASS|ESCALATE|REJECT)
    """
    try:
        logger.info(f"[CourseFactory API] Validating IR for tenant={ir.tenant_id}")

        validator = get_validator()
        result = validator.validate_ir(ir)

        logger.info(
            f"[CourseFactory API] IR validation: status={result.status}, "
            f"risk_tier={result.risk_tier}, requires_approval={result.requires_approval}"
        )

        return result

    except Exception as e:
        logger.error(f"[CourseFactory API] IR validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"IR validation failed: {str(e)}")


@router.post("/generate")
async def generate_course(
    request: CourseGenerationRequest,
    approval_token: str | None = None,
    service: CourseFactoryService = Depends(get_course_factory_service_with_events),
) -> CourseGenerationResult:
    """
    Generate complete course with IR governance.

    Process:
    1. Generate IR from request
    2. Validate IR (policy enforcement)
    3. Check if approval required (Tier 2+)
    4. Execute course generation (if allowed)
    5. Return result with evidence pack

    Args:
        request: Course generation request
        approval_token: Optional approval token (for Tier 2+ operations)

    Returns:
        CourseGenerationResult

    Raises:
        HTTPException: If IR validation fails or approval missing
    """
    try:
        logger.info(
            f"[CourseFactory API] Course generation request: '{request.title}' "
            f"(dry_run={request.dry_run})"
        )

        # Step 1: Generate IR
        ir = service.generate_ir(request)

        # Step 2: IR Gateway validation
        gateway = get_ir_gateway()
        gateway_result: IRGatewayResult = gateway.validate_request(
            ir=ir,
            approval_token=approval_token,
            legacy_request=False,
        )

        if not gateway_result.allowed:
            logger.error(
                f"[CourseFactory API] IR gateway blocked: {gateway_result.block_reason}"
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Course generation blocked by IR governance",
                    "reason": gateway_result.block_reason,
                    "ir_hash": gateway_result.ir_hash,
                    "validation_result": (
                        gateway_result.validation_result.model_dump()
                        if gateway_result.validation_result
                        else None
                    ),
                },
            )

        # Step 3: Execute course generation
        logger.info(
            f"[CourseFactory API] IR validation passed, executing course generation"
        )
        result = await service.generate_course(request)

        # Add IR hash to result
        if gateway_result.ir:
            from app.modules.ir_governance import ir_hash
            result.ir_hash = ir_hash(gateway_result.ir)

        logger.info(
            f"[CourseFactory API] Course generation completed: success={result.success}"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CourseFactory API] Course generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Course generation failed: {str(e)}"
        )


@router.post("/dry-run")
async def dry_run_course(
    request: CourseGenerationRequest,
    service: CourseFactoryService = Depends(get_course_factory_service_with_events),
) -> CourseGenerationResult:
    """
    Dry-run course generation (no actual execution, no IR validation).

    Simulates course generation to preview structure without creating files.
    Always sets request.dry_run = True.

    Args:
        request: Course generation request (dry_run will be overridden)

    Returns:
        CourseGenerationResult (simulated)
    """
    try:
        logger.info(f"[CourseFactory API] Dry-run request: '{request.title}'")

        # Force dry-run mode
        request.dry_run = True

        # Generate without IR validation
        result = await service.generate_course(request)

        logger.info("[CourseFactory API] Dry-run completed")
        return result

    except Exception as e:
        logger.error(f"[CourseFactory API] Dry-run failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dry-run failed: {str(e)}")


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "module": "course_factory",
        "ir_enabled": True,
        "sprint": "Sprint 12 + Sprint 13",
        "workflow_enabled": True,
        "enhancements_enabled": True,
        "webgenesis_enabled": True,
    }


# ========================================
# Sprint 13: Workflow Management Endpoints
# ========================================

@router.post("/workflow/transition")
async def transition_workflow(
    course_id: str,
    from_state: WorkflowState,
    to_state: WorkflowState,
    actor: str,
    reason: Optional[str] = None,
    hitl_approval: bool = False,
    service: CourseFactoryService = Depends(get_course_factory_service_with_events),
) -> WorkflowTransition:
    """
    Transition course workflow state.

    Args:
        course_id: Course ID
        from_state: Current workflow state
        to_state: Target workflow state
        actor: Who is triggering the transition
        reason: Optional reason for transition
        hitl_approval: Whether human approved (required for review→publish_ready)

    Returns:
        WorkflowTransition

    Raises:
        HTTPException: If transition is invalid
    """
    try:
        logger.info(
            f"[CourseFactory API] Workflow transition: {course_id} "
            f"{from_state.value} → {to_state.value}"
        )

        transition = await service.transition_workflow(
            course_id=course_id,
            from_state=from_state,
            to_state=to_state,
            actor=actor,
            reason=reason,
            hitl_approval=hitl_approval,
        )

        return transition

    except ValueError as e:
        logger.error(f"[CourseFactory API] Invalid transition: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[CourseFactory API] Transition failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transition failed: {str(e)}")


@router.post("/workflow/rollback")
async def rollback_workflow(
    course_id: str,
    transition_id: str,
    actor: str,
    reason: str,
    service: CourseFactoryService = Depends(get_course_factory_service_with_events),
) -> WorkflowTransition:
    """
    Rollback a workflow transition.

    Args:
        course_id: Course ID
        transition_id: ID of transition to rollback
        actor: Who is triggering the rollback
        reason: Reason for rollback

    Returns:
        WorkflowTransition (rollback)

    Raises:
        HTTPException: If rollback fails
    """
    try:
        logger.info(
            f"[CourseFactory API] Workflow rollback: {course_id} "
            f"(transition={transition_id})"
        )

        rollback = await service.rollback_workflow(
            course_id=course_id,
            transition_id=transition_id,
            actor=actor,
            reason=reason,
        )

        return rollback

    except ValueError as e:
        logger.error(f"[CourseFactory API] Rollback failed: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[CourseFactory API] Rollback error: {e}")
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")


# ========================================
# Sprint 13: Content Enhancement Endpoints
# ========================================

@router.post("/enhance")
async def enhance_content(
    request: EnhancementRequest,
    service: CourseFactoryService = Depends(get_course_factory_service_with_events),
) -> EnhancementResult:
    """
    Enhance course content with LLM-generated additions.

    Features:
    - Examples enhancement
    - Summaries generation
    - Flashcards creation
    - Content validation and diff-audit

    Args:
        request: Enhancement request

    Returns:
        EnhancementResult

    Note:
        MVP uses placeholder enhancements. Future versions will integrate
        with actual LLM for real content generation.
    """
    try:
        logger.info(
            f"[CourseFactory API] Content enhancement: {request.course_id} "
            f"(types={[t.value for t in request.enhancement_types]})"
        )

        # For MVP, we need to load lessons from storage
        # In production, this would be part of the course service
        lessons = []  # TODO: Load from storage/DB

        result = await service.enhance_content(
            request=request,
            lessons=lessons,
        )

        return result

    except Exception as e:
        logger.error(f"[CourseFactory API] Enhancement failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Enhancement failed: {str(e)}"
        )


# ========================================
# Sprint 13: WebGenesis Integration Endpoints
# ========================================

@router.post("/webgenesis/bind-theme")
async def bind_theme(
    course_id: str,
    theme_id: str,
    custom_colors: Optional[Dict[str, str]] = None,
    service: CourseFactoryService = Depends(get_course_factory_service_with_events),
) -> WebGenesisTheme:
    """
    Bind WebGenesis theme to course.

    Available themes:
    - course-minimal: Clean, minimal design
    - course-professional: Professional corporate look
    - course-modern: Modern, vibrant design

    Args:
        course_id: Course ID
        theme_id: Theme identifier
        custom_colors: Optional color overrides (primary, secondary, accent)

    Returns:
        WebGenesisTheme

    Raises:
        HTTPException: If theme not found
    """
    try:
        logger.info(
            f"[CourseFactory API] Theme binding: {course_id} (theme={theme_id})"
        )

        theme = await service.bind_theme(
            course_id=course_id,
            theme_id=theme_id,
            custom_colors=custom_colors,
        )

        return theme

    except ValueError as e:
        logger.error(f"[CourseFactory API] Theme not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[CourseFactory API] Theme binding failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Theme binding failed: {str(e)}"
        )


@router.post("/webgenesis/build-sections")
async def build_sections(
    course_id: str,
    outline: CourseOutline,
    landing_page: Optional[CourseLandingPage] = None,
    service: CourseFactoryService = Depends(get_course_factory_service_with_events),
) -> List[WebGenesisSection]:
    """
    Build WebGenesis sections from course data.

    Generates 6 section types:
    - Hero (title, subtitle, CTA)
    - Syllabus (course modules and lessons)
    - Lesson Preview (featured lessons)
    - FAQ (common questions)
    - CTA (call-to-action)
    - Footer (legal, credits)

    Args:
        course_id: Course ID
        outline: Course outline
        landing_page: Optional landing page data

    Returns:
        List of WebGenesisSection
    """
    try:
        logger.info(f"[CourseFactory API] Building sections: {course_id}")

        sections = await service.build_sections(
            course_id=course_id,
            outline=outline,
            landing_page=landing_page,
        )

        return sections

    except Exception as e:
        logger.error(f"[CourseFactory API] Section building failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Section building failed: {str(e)}"
        )


@router.post("/webgenesis/generate-seo")
async def generate_seo_pack(
    course_id: str,
    outline: CourseOutline,
    keywords: Optional[List[str]] = None,
    service: CourseFactoryService = Depends(get_course_factory_service_with_events),
) -> SEOPack:
    """
    Generate SEO pack for course.

    Includes:
    - Meta tags (title, description)
    - Open Graph tags (Facebook, LinkedIn)
    - Twitter Card tags
    - JSON-LD structured data (schema.org/Course)
    - Keywords

    Args:
        course_id: Course ID
        outline: Course outline
        keywords: Optional additional keywords

    Returns:
        SEOPack
    """
    try:
        logger.info(f"[CourseFactory API] Generating SEO pack: {course_id}")

        seo_pack = await service.generate_seo_pack(
            course_id=course_id,
            outline=outline,
            keywords=keywords,
        )

        return seo_pack

    except Exception as e:
        logger.error(f"[CourseFactory API] SEO generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"SEO generation failed: {str(e)}"
        )


@router.post("/webgenesis/preview")
async def generate_preview_url(
    course_id: str,
    version: str = "latest",
    service: CourseFactoryService = Depends(get_course_factory_service_with_events),
) -> Dict[str, str]:
    """
    Generate preview URL for course.

    Args:
        course_id: Course ID
        version: Version identifier (default: "latest")

    Returns:
        Dict with preview_url
    """
    try:
        logger.info(
            f"[CourseFactory API] Generating preview URL: {course_id} (version={version})"
        )

        preview_url = await service.generate_preview_url(
            course_id=course_id,
            version=version,
        )

        return {"preview_url": preview_url}

    except Exception as e:
        logger.error(f"[CourseFactory API] Preview URL generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Preview URL generation failed: {str(e)}"
        )
