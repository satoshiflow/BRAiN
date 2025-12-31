"""
Course Factory Monetization Service - Sprint 14

Service layer for enrollment, certificates, analytics, and marketplace.
Privacy-first, backwards compatible, atomic operations.
"""

from __future__ import annotations

import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger

from app.modules.course_factory.monetization_models import (
    CourseEnrollment,
    CourseProgress,
    CourseCompletion,
    Certificate,
    CertificatePayload,
    CertificateVerificationResult,
    MicroNichePack,
    PackRenderResult,
    CourseAnalyticsSummary,
    EnrollmentStatus,
    CourseCatalogMetadata,
    CourseCatalogCard,
    PackOperation,
)
from app.modules.course_factory.monetization_storage import (
    get_monetization_storage,
    MonetizationStorage,
)
from app.modules.course_factory.certificate_signer import (
    get_certificate_signer,
    CertificateSigner,
)
from app.modules.course_factory.schemas import CourseOutline


# ========================================
# Monetization Service
# ========================================

class MonetizationService:
    """
    Monetization service for course factory.

    Responsibilities:
    - Enrollment and progress tracking
    - Certificate issuance and verification
    - Micro-niche pack rendering
    - Analytics aggregation (NO PII)
    - Catalog metadata
    """

    def __init__(
        self,
        storage: Optional[MonetizationStorage] = None,
        signer: Optional[CertificateSigner] = None,
    ):
        self.storage = storage or get_monetization_storage()
        self.signer = signer or get_certificate_signer()

    # ========================================
    # Enrollment & Progress
    # ========================================

    async def enroll_course(
        self,
        course_id: str,
        language: str,
        actor_id: str,
    ) -> CourseEnrollment:
        """
        Enroll user in course.

        Args:
            course_id: Course ID
            language: Course language
            actor_id: Pseudonymous actor ID

        Returns:
            CourseEnrollment
        """
        enrollment = CourseEnrollment(
            course_id=course_id,
            language=language,
            actor_id=actor_id,
        )

        success = self.storage.save_enrollment(enrollment)

        if not success:
            raise RuntimeError("Failed to save enrollment")

        logger.info(
            f"[MonetizationService] Enrollment created: {enrollment.enrollment_id} "
            f"(course={course_id}, actor={actor_id})"
        )

        return enrollment

    async def update_progress(
        self,
        enrollment_id: str,
        module_id: Optional[str],
        chapter_id: Optional[str],
        status: str,
    ) -> CourseProgress:
        """
        Update course progress.

        Args:
            enrollment_id: Enrollment ID
            module_id: Module ID (optional)
            chapter_id: Chapter ID (optional)
            status: Progress status (started/completed)

        Returns:
            CourseProgress
        """
        from app.modules.course_factory.monetization_models import ProgressStatus

        progress = CourseProgress(
            enrollment_id=enrollment_id,
            module_id=module_id,
            chapter_id=chapter_id,
            status=ProgressStatus(status),
        )

        success = self.storage.save_progress(progress)

        if not success:
            raise RuntimeError("Failed to save progress")

        logger.info(
            f"[MonetizationService] Progress updated: {progress.progress_id} "
            f"(enrollment={enrollment_id}, status={status})"
        )

        return progress

    async def get_enrollment_status(
        self,
        course_id: str,
        enrollment_id: str,
    ) -> Optional[EnrollmentStatus]:
        """
        Get combined enrollment status.

        Args:
            course_id: Course ID
            enrollment_id: Enrollment ID

        Returns:
            EnrollmentStatus or None
        """
        enrollment = self.storage.get_enrollment(enrollment_id)

        if not enrollment or enrollment.course_id != course_id:
            return None

        progress = self.storage.get_progress_by_enrollment(enrollment_id)
        completion = self.storage.get_completion(enrollment_id)

        # Calculate completion percentage
        completed_count = sum(1 for p in progress if p.status.value == "completed")
        total_count = len(progress) if progress else 1
        completion_percentage = (completed_count / total_count) * 100 if total_count > 0 else 0.0

        return EnrollmentStatus(
            enrollment=enrollment,
            progress=progress,
            completion=completion,
            completion_percentage=completion_percentage,
        )

    async def mark_complete(
        self,
        enrollment_id: str,
        course_id: str,
        actor_id: str,
        course_version: str = "1.0.0",
    ) -> CourseCompletion:
        """
        Mark course as completed.

        Args:
            enrollment_id: Enrollment ID
            course_id: Course ID
            actor_id: Actor ID
            course_version: Course version

        Returns:
            CourseCompletion
        """
        # Generate completion hash (deterministic)
        completed_at = datetime.utcnow().timestamp()
        hash_input = f"{course_id}:{actor_id}:{completed_at}:{course_version}"
        completion_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        completion = CourseCompletion(
            enrollment_id=enrollment_id,
            course_id=course_id,
            actor_id=actor_id,
            completed_at=completed_at,
            completion_hash=completion_hash,
            course_version=course_version,
        )

        success = self.storage.save_completion(completion)

        if not success:
            raise RuntimeError("Failed to save completion")

        logger.info(
            f"[MonetizationService] Course completed: {completion.completion_id} "
            f"(enrollment={enrollment_id})"
        )

        return completion

    # ========================================
    # Certificates
    # ========================================

    async def issue_certificate(
        self,
        enrollment_id: str,
        course_title: str,
    ) -> Certificate:
        """
        Issue certificate for completed course.

        Args:
            enrollment_id: Enrollment ID
            course_title: Course title

        Returns:
            Certificate

        Raises:
            ValueError: If course not completed
        """
        # Verify completion exists
        completion = self.storage.get_completion(enrollment_id)

        if not completion:
            raise ValueError(
                f"Cannot issue certificate: course not completed (enrollment={enrollment_id})"
            )

        # Get enrollment for language
        enrollment = self.storage.get_enrollment(enrollment_id)

        if not enrollment:
            raise ValueError(f"Enrollment not found: {enrollment_id}")

        # Create certificate payload
        payload = CertificatePayload(
            course_id=completion.course_id,
            course_title=course_title,
            language=enrollment.language,
            actor_id=completion.actor_id,
            completed_at=completion.completed_at,
            completion_hash=completion.completion_hash,
        )

        # Sign certificate
        certificate = self.signer.sign_certificate(payload)

        # Save certificate
        success = self.storage.save_certificate(
            course_id=completion.course_id,
            certificate=certificate
        )

        if not success:
            raise RuntimeError("Failed to save certificate")

        logger.info(
            f"[MonetizationService] Certificate issued: {certificate.payload.certificate_id} "
            f"(enrollment={enrollment_id})"
        )

        return certificate

    async def verify_certificate(
        self,
        certificate_payload: Dict[str, Any],
        signature_hex: str,
    ) -> CertificateVerificationResult:
        """
        Verify certificate signature.

        Args:
            certificate_payload: Certificate payload as dict
            signature_hex: Signature hex string

        Returns:
            CertificateVerificationResult
        """
        try:
            payload = CertificatePayload(**certificate_payload)
            result = self.signer.verify_certificate(payload, signature_hex)

            logger.info(
                f"[MonetizationService] Certificate verification: valid={result.valid}"
            )

            return result
        except Exception as e:
            logger.error(f"[MonetizationService] Certificate verification failed: {e}")
            return CertificateVerificationResult(
                valid=False,
                reason=f"Invalid payload: {str(e)}"
            )

    async def get_certificate(
        self,
        course_id: str,
        certificate_id: str,
    ) -> Optional[Certificate]:
        """Get certificate by ID."""
        return self.storage.get_certificate(course_id, certificate_id)

    # ========================================
    # Micro-Niche Packs
    # ========================================

    async def create_pack(
        self,
        course_id: str,
        pack: MicroNichePack,
    ) -> MicroNichePack:
        """
        Create micro-niche content pack.

        Args:
            course_id: Base course ID
            pack: MicroNichePack instance

        Returns:
            MicroNichePack
        """
        success = self.storage.save_pack(course_id, pack)

        if not success:
            raise RuntimeError("Failed to save pack")

        logger.info(
            f"[MonetizationService] Pack created: {pack.pack_id} "
            f"(course={course_id}, audience={pack.target_audience})"
        )

        return pack

    async def get_pack(
        self,
        course_id: str,
        pack_id: str,
    ) -> Optional[MicroNichePack]:
        """Get pack by ID."""
        return self.storage.get_pack(course_id, pack_id)

    async def get_packs(
        self,
        course_id: str,
    ) -> List[MicroNichePack]:
        """Get all packs for a course."""
        return self.storage.get_packs_by_course(course_id)

    async def render_course_with_pack(
        self,
        base_course: Dict[str, Any],
        pack: MicroNichePack,
    ) -> PackRenderResult:
        """
        Render course with pack overrides.

        Args:
            base_course: Base course structure (dict)
            pack: MicroNichePack with overrides

        Returns:
            PackRenderResult
        """
        # Deep copy base course
        import copy
        rendered = copy.deepcopy(base_course)

        applied_count = 0

        # Apply overrides
        for override in pack.overrides:
            try:
                if override.operation == PackOperation.REPLACE_TEXT:
                    # Find and replace text in target
                    self._apply_replace_text(rendered, override.target_id, override.value)
                    applied_count += 1

                elif override.operation == PackOperation.OVERRIDE_TITLE:
                    # Override title
                    self._apply_override_title(rendered, override.target_id, override.value)
                    applied_count += 1

                elif override.operation == PackOperation.OVERRIDE_DESCRIPTION:
                    # Override description
                    self._apply_override_description(rendered, override.target_id, override.value)
                    applied_count += 1

                elif override.operation == PackOperation.APPEND_MODULE:
                    # Append module
                    if "modules" in rendered:
                        rendered["modules"].append(override.value)
                        applied_count += 1

            except Exception as e:
                logger.warning(f"[MonetizationService] Failed to apply override: {e}")

        logger.info(
            f"[MonetizationService] Course rendered with pack: {pack.pack_id} "
            f"(applied={applied_count}/{len(pack.overrides)})"
        )

        return PackRenderResult(
            pack_id=pack.pack_id,
            base_course_id=pack.base_course_id,
            rendered_course=rendered,
            applied_overrides=applied_count,
        )

    def _apply_replace_text(self, course: Dict, target_id: str, value: str):
        """Apply text replacement."""
        # Simplified: replace in modules/lessons
        if "modules" in course:
            for module in course["modules"]:
                if module.get("id") == target_id:
                    module["content"] = value
                if "lessons" in module:
                    for lesson in module["lessons"]:
                        if lesson.get("id") == target_id:
                            lesson["content"] = value

    def _apply_override_title(self, course: Dict, target_id: str, value: str):
        """Apply title override."""
        if "modules" in course:
            for module in course["modules"]:
                if module.get("id") == target_id:
                    module["title"] = value
                if "lessons" in module:
                    for lesson in module["lessons"]:
                        if lesson.get("id") == target_id:
                            lesson["title"] = value

    def _apply_override_description(self, course: Dict, target_id: str, value: str):
        """Apply description override."""
        if "modules" in course:
            for module in course["modules"]:
                if module.get("id") == target_id:
                    module["description"] = value

    # ========================================
    # Analytics (NO PII)
    # ========================================

    async def get_analytics_summary(
        self,
        course_id: str,
    ) -> CourseAnalyticsSummary:
        """
        Get aggregated analytics for course (NO PII).

        Args:
            course_id: Course ID

        Returns:
            CourseAnalyticsSummary
        """
        enrollments = self.storage.get_enrollments_by_course(course_id)
        completions = self.storage.get_completions_by_course(course_id)

        # Aggregate by language
        enrollments_by_language: Dict[str, int] = {}
        for enrollment in enrollments:
            lang = enrollment.language
            enrollments_by_language[lang] = enrollments_by_language.get(lang, 0) + 1

        # Calculate completion rate
        total_enrollments = len(enrollments)
        total_completions = len(completions)
        completion_rate = (total_completions / total_enrollments * 100) if total_enrollments > 0 else 0.0

        # Calculate average completion time
        completion_times = []
        for completion in completions:
            enrollment = next(
                (e for e in enrollments if e.enrollment_id == completion.enrollment_id),
                None
            )
            if enrollment:
                time_diff = completion.completed_at - enrollment.enrolled_at
                completion_times.append(time_diff / 86400)  # days

        avg_completion_time_days = (
            sum(completion_times) / len(completion_times)
            if completion_times
            else None
        )

        summary = CourseAnalyticsSummary(
            course_id=course_id,
            total_enrollments=total_enrollments,
            enrollments_by_language=enrollments_by_language,
            total_completions=total_completions,
            completion_rate=completion_rate,
            certificate_issuance_count=total_completions,  # Assume 1:1 for now
            avg_completion_time_days=avg_completion_time_days,
        )

        logger.info(
            f"[MonetizationService] Analytics summary generated: course={course_id}, "
            f"enrollments={total_enrollments}, completions={total_completions}"
        )

        return summary

    # ========================================
    # Catalog
    # ========================================

    async def get_catalog_metadata(
        self,
        course_outline: CourseOutline,
        price_display: str = "Free",
        tags: List[str] = None,
    ) -> CourseCatalogMetadata:
        """
        Get catalog metadata for course.

        Args:
            course_outline: Course outline
            price_display: Price display string
            tags: Tags for course

        Returns:
            CourseCatalogMetadata
        """
        metadata = CourseCatalogMetadata(
            course_id=course_outline.metadata.course_id,
            title=course_outline.metadata.title,
            description=course_outline.metadata.description,
            price_display=price_display,
            target_audiences=[a.value for a in course_outline.metadata.target_audiences],
            languages=[course_outline.metadata.language.value],
            certificate_available=True,
            version="1.0.0",
            tags=tags or [],
            total_modules=len(course_outline.modules),
            total_lessons=course_outline.total_lessons,
            estimated_duration_minutes=course_outline.total_estimated_duration_minutes,
        )

        return metadata

    async def get_catalog_card(
        self,
        metadata: CourseCatalogMetadata,
    ) -> CourseCatalogCard:
        """
        Get catalog card (summary) from metadata.

        Args:
            metadata: CourseCatalogMetadata

        Returns:
            CourseCatalogCard
        """
        return CourseCatalogCard(
            course_id=metadata.course_id,
            title=metadata.title,
            description=metadata.description,
            price_display=metadata.price_display,
            languages=metadata.languages,
            certificate_available=metadata.certificate_available,
            tags=metadata.tags,
            estimated_duration_minutes=metadata.estimated_duration_minutes,
        )


# ========================================
# Singleton
# ========================================

_service: Optional[MonetizationService] = None


def get_monetization_service() -> MonetizationService:
    """Get MonetizationService singleton."""
    global _service
    if _service is None:
        _service = MonetizationService()
    return _service
