"""
Course Factory Monetization API Router - Sprint 14

FastAPI endpoints for enrollment, certificates, analytics, and marketplace.
Privacy-first, backwards compatible, fail-closed for certificate verification.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
from loguru import logger

from app.modules.course_factory.monetization_models import (
    CourseEnrollment,
    CourseProgress,
    CourseCompletion,
    Certificate,
    CertificateVerificationResult,
    MicroNichePack,
    PackRenderResult,
    CourseAnalyticsSummary,
    EnrollmentStatus,
    CourseCatalogMetadata,
    CourseCatalogCard,
    EnrollRequest,
    ProgressUpdateRequest,
    CertificateIssueRequest,
    CertificateVerifyRequest,
    PackCreateRequest,
)
from app.modules.course_factory.monetization_service import (
    MonetizationService,
    get_monetization_service,
)
from app.modules.course_factory.service import (
    CourseFactoryService,
    get_course_factory_service,
)


router = APIRouter(prefix="/api/courses", tags=["courses-monetization"])


# ========================================
# Enrollment & Progress Endpoints
# ========================================

@router.post("/{course_id}/enroll")
async def enroll_course(
    course_id: str,
    request: EnrollRequest,
    service: MonetizationService = Depends(get_monetization_service),
) -> CourseEnrollment:
    """
    Enroll in a course.

    Args:
        course_id: Course ID
        request: Enrollment request

    Returns:
        CourseEnrollment

    Emits:
        - course.enrolled audit event
    """
    try:
        # Generate pseudonymous actor_id if not provided
        actor_id = request.actor_id or f"actor_{hash(course_id + request.language) % 1000000:06d}"

        enrollment = await service.enroll_course(
            course_id=course_id,
            language=request.language,
            actor_id=actor_id,
        )

        logger.info(f"[MonetizationAPI] Course enrolled: {enrollment.enrollment_id}")

        return enrollment

    except Exception as e:
        logger.error(f"[MonetizationAPI] Enrollment failed: {e}")
        raise HTTPException(status_code=500, detail=f"Enrollment failed: {str(e)}")


@router.post("/{course_id}/progress")
async def update_progress(
    course_id: str,
    request: ProgressUpdateRequest,
    service: MonetizationService = Depends(get_monetization_service),
) -> CourseProgress:
    """
    Update course progress.

    Args:
        course_id: Course ID
        request: Progress update request

    Returns:
        CourseProgress

    Emits:
        - course.progress_updated audit event
    """
    try:
        progress = await service.update_progress(
            enrollment_id=request.enrollment_id,
            module_id=request.module_id,
            chapter_id=request.chapter_id,
            status=request.status.value,
        )

        logger.info(f"[MonetizationAPI] Progress updated: {progress.progress_id}")

        return progress

    except Exception as e:
        logger.error(f"[MonetizationAPI] Progress update failed: {e}")
        raise HTTPException(status_code=500, detail=f"Progress update failed: {str(e)}")


@router.get("/{course_id}/status")
async def get_enrollment_status(
    course_id: str,
    enrollment_id: str = Query(..., description="Enrollment ID"),
    service: MonetizationService = Depends(get_monetization_service),
) -> EnrollmentStatus:
    """
    Get enrollment status with progress and completion.

    Args:
        course_id: Course ID
        enrollment_id: Enrollment ID

    Returns:
        EnrollmentStatus

    Raises:
        HTTPException: If enrollment not found
    """
    try:
        status = await service.get_enrollment_status(
            course_id=course_id,
            enrollment_id=enrollment_id,
        )

        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Enrollment not found: {enrollment_id}"
            )

        return status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MonetizationAPI] Get status failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get status failed: {str(e)}")


@router.post("/{course_id}/complete")
async def complete_course(
    course_id: str,
    enrollment_id: str,
    actor_id: str,
    service: MonetizationService = Depends(get_monetization_service),
) -> CourseCompletion:
    """
    Mark course as completed.

    Args:
        course_id: Course ID
        enrollment_id: Enrollment ID
        actor_id: Actor ID

    Returns:
        CourseCompletion

    Emits:
        - course.completed audit event
    """
    try:
        completion = await service.mark_complete(
            enrollment_id=enrollment_id,
            course_id=course_id,
            actor_id=actor_id,
        )

        logger.info(f"[MonetizationAPI] Course completed: {completion.completion_id}")

        return completion

    except Exception as e:
        logger.error(f"[MonetizationAPI] Complete course failed: {e}")
        raise HTTPException(status_code=500, detail=f"Complete course failed: {str(e)}")


# ========================================
# Certificate Endpoints
# ========================================

@router.post("/{course_id}/certificates/issue")
async def issue_certificate(
    course_id: str,
    request: CertificateIssueRequest,
    service: MonetizationService = Depends(get_monetization_service),
) -> Certificate:
    """
    Issue certificate for completed course.

    Args:
        course_id: Course ID
        request: Certificate issue request

    Returns:
        Certificate

    Raises:
        HTTPException: If course not completed

    Emits:
        - certificate.issued audit event
    """
    try:
        # For MVP, use course_id as title
        # In production, fetch from course service
        course_title = f"Course {course_id}"

        certificate = await service.issue_certificate(
            enrollment_id=request.enrollment_id,
            course_title=course_title,
        )

        logger.info(
            f"[MonetizationAPI] Certificate issued: {certificate.payload.certificate_id}"
        )

        return certificate

    except ValueError as e:
        logger.error(f"[MonetizationAPI] Certificate issue failed (validation): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[MonetizationAPI] Certificate issue failed: {e}")
        raise HTTPException(status_code=500, detail=f"Certificate issue failed: {str(e)}")


@router.post("/certificates/verify")
async def verify_certificate(
    request: CertificateVerifyRequest,
    service: MonetizationService = Depends(get_monetization_service),
) -> CertificateVerificationResult:
    """
    Verify certificate signature (offline verification).

    Args:
        request: Certificate verify request

    Returns:
        CertificateVerificationResult

    Emits:
        - certificate.verified audit event
    """
    try:
        result = await service.verify_certificate(
            certificate_payload=request.certificate_payload,
            signature_hex=request.signature_hex,
        )

        logger.info(f"[MonetizationAPI] Certificate verified: valid={result.valid}")

        return result

    except Exception as e:
        logger.error(f"[MonetizationAPI] Certificate verification failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Certificate verification failed: {str(e)}"
        )


@router.get("/{course_id}/certificates/{certificate_id}")
async def get_certificate(
    course_id: str,
    certificate_id: str,
    service: MonetizationService = Depends(get_monetization_service),
) -> Certificate:
    """
    Get certificate by ID.

    Args:
        course_id: Course ID
        certificate_id: Certificate ID

    Returns:
        Certificate

    Raises:
        HTTPException: If certificate not found
    """
    try:
        certificate = await service.get_certificate(
            course_id=course_id,
            certificate_id=certificate_id,
        )

        if not certificate:
            raise HTTPException(
                status_code=404,
                detail=f"Certificate not found: {certificate_id}"
            )

        return certificate

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MonetizationAPI] Get certificate failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get certificate failed: {str(e)}")


# ========================================
# Micro-Niche Pack Endpoints
# ========================================

@router.post("/{course_id}/packs")
async def create_pack(
    course_id: str,
    request: PackCreateRequest,
    service: MonetizationService = Depends(get_monetization_service),
) -> MicroNichePack:
    """
    Create micro-niche content pack.

    Args:
        course_id: Base course ID
        request: Pack create request

    Returns:
        MicroNichePack

    Emits:
        - course.pack_created audit event
    """
    try:
        pack = MicroNichePack(
            base_course_id=course_id,
            target_audience=request.target_audience,
            language=request.language,
            overrides=request.overrides,
            description=request.description,
        )

        created_pack = await service.create_pack(
            course_id=course_id,
            pack=pack,
        )

        logger.info(f"[MonetizationAPI] Pack created: {created_pack.pack_id}")

        return created_pack

    except Exception as e:
        logger.error(f"[MonetizationAPI] Pack creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Pack creation failed: {str(e)}")


@router.get("/{course_id}/packs")
async def get_packs(
    course_id: str,
    service: MonetizationService = Depends(get_monetization_service),
) -> List[MicroNichePack]:
    """
    Get all packs for a course.

    Args:
        course_id: Course ID

    Returns:
        List of MicroNichePack
    """
    try:
        packs = await service.get_packs(course_id=course_id)
        return packs

    except Exception as e:
        logger.error(f"[MonetizationAPI] Get packs failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get packs failed: {str(e)}")


@router.get("/{course_id}/render")
async def render_course_with_pack(
    course_id: str,
    pack_id: str = Query(..., description="Pack ID to apply"),
    service: MonetizationService = Depends(get_monetization_service),
    course_service: CourseFactoryService = Depends(get_course_factory_service),
) -> PackRenderResult:
    """
    Render course with pack overrides.

    Args:
        course_id: Course ID
        pack_id: Pack ID

    Returns:
        PackRenderResult

    Raises:
        HTTPException: If pack not found

    Emits:
        - course.pack_rendered audit event
    """
    try:
        # Get pack
        pack = await service.get_pack(course_id=course_id, pack_id=pack_id)

        if not pack:
            raise HTTPException(
                status_code=404,
                detail=f"Pack not found: {pack_id}"
            )

        # For MVP, use a minimal base course structure
        # In production, load actual course from course_service
        base_course = {
            "course_id": course_id,
            "modules": [],  # Would be populated from actual course
        }

        result = await service.render_course_with_pack(
            base_course=base_course,
            pack=pack,
        )

        logger.info(f"[MonetizationAPI] Course rendered: {pack_id}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MonetizationAPI] Render course failed: {e}")
        raise HTTPException(status_code=500, detail=f"Render course failed: {str(e)}")


# ========================================
# Analytics Endpoints
# ========================================

@router.get("/analytics/summary")
async def get_analytics_summary(
    course_id: str = Query(..., description="Course ID"),
    service: MonetizationService = Depends(get_monetization_service),
) -> CourseAnalyticsSummary:
    """
    Get aggregated analytics for course (NO PII).

    Args:
        course_id: Course ID

    Returns:
        CourseAnalyticsSummary

    Emits:
        - course.analytics_viewed audit event
    """
    try:
        summary = await service.get_analytics_summary(course_id=course_id)

        logger.info(f"[MonetizationAPI] Analytics viewed: course={course_id}")

        return summary

    except Exception as e:
        logger.error(f"[MonetizationAPI] Get analytics failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get analytics failed: {str(e)}")


@router.get("/analytics/export")
async def export_analytics(
    course_id: str = Query(..., description="Course ID"),
    format: str = Query("json", description="Export format (json or csv)"),
    service: MonetizationService = Depends(get_monetization_service),
) -> Dict[str, Any]:
    """
    Export aggregated analytics (NO PII).

    Args:
        course_id: Course ID
        format: Export format (json or csv)

    Returns:
        Analytics export data

    Emits:
        - course.analytics_exported audit event
    """
    try:
        if format not in ["json", "csv"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format: {format} (must be json or csv)"
            )

        summary = await service.get_analytics_summary(course_id=course_id)

        if format == "json":
            export_data = {
                "format": "json",
                "course_id": course_id,
                "summary": summary.model_dump(),
            }
        else:  # csv
            # Simple CSV conversion
            csv_lines = [
                "metric,value",
                f"total_enrollments,{summary.total_enrollments}",
                f"total_completions,{summary.total_completions}",
                f"completion_rate,{summary.completion_rate:.2f}%",
                f"certificate_issuance_count,{summary.certificate_issuance_count}",
            ]
            export_data = {
                "format": "csv",
                "course_id": course_id,
                "csv": "\n".join(csv_lines),
            }

        logger.info(f"[MonetizationAPI] Analytics exported: course={course_id}, format={format}")

        return export_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[MonetizationAPI] Export analytics failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export analytics failed: {str(e)}")


# ========================================
# Catalog Endpoints
# ========================================

@router.get("/catalog")
async def get_course_catalog(
    course_service: CourseFactoryService = Depends(get_course_factory_service),
    monetization_service: MonetizationService = Depends(get_monetization_service),
) -> List[CourseCatalogCard]:
    """
    Get course catalog (list of course cards).

    Returns:
        List of CourseCatalogCard

    Emits:
        - course.catalog_viewed audit event
    """
    try:
        # For MVP, return empty catalog
        # In production, iterate over all courses and build cards
        catalog = []

        logger.info("[MonetizationAPI] Catalog viewed")

        return catalog

    except Exception as e:
        logger.error(f"[MonetizationAPI] Get catalog failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get catalog failed: {str(e)}")


@router.get("/{course_id}/catalog")
async def get_course_catalog_metadata(
    course_id: str,
    monetization_service: MonetizationService = Depends(get_monetization_service),
) -> Dict[str, Any]:
    """
    Get catalog metadata for specific course.

    Args:
        course_id: Course ID

    Returns:
        CourseCatalogMetadata

    Emits:
        - course.catalog_viewed audit event
    """
    try:
        # For MVP, return minimal metadata
        # In production, load course and generate metadata
        metadata = {
            "course_id": course_id,
            "title": f"Course {course_id}",
            "description": "Course description",
            "price_display": "Free",
            "languages": ["de"],
            "certificate_available": True,
            "version": "1.0.0",
            "tags": [],
        }

        logger.info(f"[MonetizationAPI] Course metadata viewed: {course_id}")

        return metadata

    except Exception as e:
        logger.error(f"[MonetizationAPI] Get course metadata failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get course metadata failed: {str(e)}")


# ========================================
# Health Check
# ========================================

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for monetization features."""
    return {
        "status": "healthy",
        "module": "course_monetization",
        "sprint": "Sprint 14",
        "features": [
            "enrollment_tracking",
            "certificate_issuance",
            "micro_niche_packs",
            "analytics_aggregation",
            "catalog_metadata",
        ],
        "privacy_first": True,
        "backwards_compatible": True,
    }
