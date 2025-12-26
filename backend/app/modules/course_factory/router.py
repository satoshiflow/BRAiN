"""
Course Factory API Router - Sprint 12

FastAPI endpoints for course generation with IR governance.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any
from loguru import logger

from app.modules.course_factory.schemas import (
    CourseGenerationRequest,
    CourseGenerationResult,
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


@router.get("/info")
async def get_info() -> Dict[str, Any]:
    """Get CourseFactory module information."""
    return {
        "name": "CourseFactory",
        "version": "1.0.0",
        "description": "Online course generation with IR governance",
        "sprint": "Sprint 12",
        "features": [
            "Course outline generation (4-6 modules, 3-5 lessons each)",
            "Full lesson content generation (Markdown)",
            "Quiz generation (10-15 MCQs)",
            "Landing page generation",
            "IR governance integration",
            "Dry-run support",
            "Evidence pack generation",
            "Staging deployment (WebGenesis integration)",
        ],
        "supported_languages": ["de", "en", "fr", "es"],
        "ir_actions": [
            "course.create",
            "course.generate_outline",
            "course.generate_lessons",
            "course.generate_quiz",
            "course.generate_landing",
            "course.deploy_staging",
        ],
        "endpoints": {
            "GET /api/course-factory/info": "Module information",
            "POST /api/course-factory/generate": "Generate course (with IR)",
            "POST /api/course-factory/generate-ir": "Generate IR only (dry-run)",
            "POST /api/course-factory/validate-ir": "Validate IR without execution",
        },
    }


@router.post("/generate-ir")
async def generate_ir_only(
    request: CourseGenerationRequest,
    service: CourseFactoryService = Depends(get_course_factory_service),
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
    service: CourseFactoryService = Depends(get_course_factory_service),
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
    service: CourseFactoryService = Depends(get_course_factory_service),
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
    }
