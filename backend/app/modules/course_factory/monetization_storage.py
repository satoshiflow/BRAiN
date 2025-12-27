"""
Course Factory Monetization Storage - Sprint 14

Atomic, thread-safe storage adapter for enrollments, certificates, and packs.
File-based storage with append-only JSONL and atomic writes.
"""

from __future__ import annotations

import json
import fcntl
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from loguru import logger

from app.modules.course_factory.monetization_models import (
    CourseEnrollment,
    CourseProgress,
    CourseCompletion,
    Certificate,
    CertificatePayload,
    MicroNichePack,
    EnrollmentStatus,
)


# ========================================
# File Locking Context Manager
# ========================================

@contextmanager
def file_lock(file_path: Path, mode: str = 'a'):
    """
    Context manager for atomic file operations with exclusive locking.

    Args:
        file_path: Path to file
        mode: File open mode ('a' for append, 'w' for write, 'r' for read)

    Yields:
        File handle with exclusive lock
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, mode, encoding='utf-8') as f:
        try:
            # Acquire exclusive lock
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            yield f
        finally:
            # Release lock
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


# ========================================
# Storage Adapter
# ========================================

class MonetizationStorage:
    """
    Atomic storage adapter for course monetization features.

    Storage layout:
    - storage/courses/enrollments.jsonl (append-only)
    - storage/courses/progress.jsonl (append-only)
    - storage/courses/completions.jsonl (append-only)
    - storage/courses/certificates/{course_id}/{certificate_id}/certificate.json
    - storage/courses/certificates/{course_id}/{certificate_id}/certificate.sig
    - storage/courses/packs/{course_id}/packs.json
    """

    def __init__(self, base_path: str = "storage/courses"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # JSONL files
        self.enrollments_file = self.base_path / "enrollments.jsonl"
        self.progress_file = self.base_path / "progress.jsonl"
        self.completions_file = self.base_path / "completions.jsonl"

        # Directories
        self.certificates_dir = self.base_path / "certificates"
        self.packs_dir = self.base_path / "packs"

    # ========================================
    # Enrollment Operations
    # ========================================

    def save_enrollment(self, enrollment: CourseEnrollment) -> bool:
        """
        Save enrollment to append-only JSONL.

        Args:
            enrollment: CourseEnrollment instance

        Returns:
            bool: Success
        """
        try:
            with file_lock(self.enrollments_file, 'a') as f:
                f.write(json.dumps(enrollment.model_dump(), ensure_ascii=False) + '\n')
            logger.info(f"[MonetizationStorage] Enrollment saved: {enrollment.enrollment_id}")
            return True
        except Exception as e:
            logger.error(f"[MonetizationStorage] Failed to save enrollment: {e}")
            return False

    def get_enrollment(self, enrollment_id: str) -> Optional[CourseEnrollment]:
        """Get enrollment by ID."""
        try:
            if not self.enrollments_file.exists():
                return None

            with file_lock(self.enrollments_file, 'r') as f:
                for line in f:
                    data = json.loads(line.strip())
                    if data.get('enrollment_id') == enrollment_id:
                        return CourseEnrollment(**data)
            return None
        except Exception as e:
            logger.error(f"[MonetizationStorage] Failed to get enrollment: {e}")
            return None

    def get_enrollments_by_course(self, course_id: str) -> List[CourseEnrollment]:
        """Get all enrollments for a course."""
        enrollments = []
        try:
            if not self.enrollments_file.exists():
                return enrollments

            with file_lock(self.enrollments_file, 'r') as f:
                for line in f:
                    data = json.loads(line.strip())
                    if data.get('course_id') == course_id:
                        enrollments.append(CourseEnrollment(**data))
            return enrollments
        except Exception as e:
            logger.error(f"[MonetizationStorage] Failed to get enrollments: {e}")
            return enrollments

    # ========================================
    # Progress Operations
    # ========================================

    def save_progress(self, progress: CourseProgress) -> bool:
        """Save progress to append-only JSONL."""
        try:
            with file_lock(self.progress_file, 'a') as f:
                f.write(json.dumps(progress.model_dump(), ensure_ascii=False) + '\n')
            logger.info(f"[MonetizationStorage] Progress saved: {progress.progress_id}")
            return True
        except Exception as e:
            logger.error(f"[MonetizationStorage] Failed to save progress: {e}")
            return False

    def get_progress_by_enrollment(self, enrollment_id: str) -> List[CourseProgress]:
        """Get all progress records for an enrollment."""
        progress_records = []
        try:
            if not self.progress_file.exists():
                return progress_records

            with file_lock(self.progress_file, 'r') as f:
                for line in f:
                    data = json.loads(line.strip())
                    if data.get('enrollment_id') == enrollment_id:
                        progress_records.append(CourseProgress(**data))
            return progress_records
        except Exception as e:
            logger.error(f"[MonetizationStorage] Failed to get progress: {e}")
            return progress_records

    # ========================================
    # Completion Operations
    # ========================================

    def save_completion(self, completion: CourseCompletion) -> bool:
        """Save completion to append-only JSONL."""
        try:
            with file_lock(self.completions_file, 'a') as f:
                f.write(json.dumps(completion.model_dump(), ensure_ascii=False) + '\n')
            logger.info(f"[MonetizationStorage] Completion saved: {completion.completion_id}")
            return True
        except Exception as e:
            logger.error(f"[MonetizationStorage] Failed to save completion: {e}")
            return False

    def get_completion(self, enrollment_id: str) -> Optional[CourseCompletion]:
        """Get completion by enrollment ID."""
        try:
            if not self.completions_file.exists():
                return None

            with file_lock(self.completions_file, 'r') as f:
                for line in f:
                    data = json.loads(line.strip())
                    if data.get('enrollment_id') == enrollment_id:
                        return CourseCompletion(**data)
            return None
        except Exception as e:
            logger.error(f"[MonetizationStorage] Failed to get completion: {e}")
            return None

    def get_completions_by_course(self, course_id: str) -> List[CourseCompletion]:
        """Get all completions for a course."""
        completions = []
        try:
            if not self.completions_file.exists():
                return completions

            with file_lock(self.completions_file, 'r') as f:
                for line in f:
                    data = json.loads(line.strip())
                    if data.get('course_id') == course_id:
                        completions.append(CourseCompletion(**data))
            return completions
        except Exception as e:
            logger.error(f"[MonetizationStorage] Failed to get completions: {e}")
            return completions

    # ========================================
    # Certificate Operations
    # ========================================

    def save_certificate(
        self,
        course_id: str,
        certificate: Certificate
    ) -> bool:
        """
        Save certificate with atomic write.

        Args:
            course_id: Course ID
            certificate: Certificate instance

        Returns:
            bool: Success
        """
        try:
            cert_dir = self.certificates_dir / course_id / certificate.payload.certificate_id
            cert_dir.mkdir(parents=True, exist_ok=True)

            # Save payload
            payload_path = cert_dir / "certificate.json"
            with open(payload_path, 'w', encoding='utf-8') as f:
                f.write(certificate.payload.to_canonical_json())

            # Save signature
            sig_path = cert_dir / "certificate.sig"
            with open(sig_path, 'w', encoding='utf-8') as f:
                f.write(certificate.signature_hex)

            logger.info(f"[MonetizationStorage] Certificate saved: {certificate.payload.certificate_id}")
            return True
        except Exception as e:
            logger.error(f"[MonetizationStorage] Failed to save certificate: {e}")
            return False

    def get_certificate(
        self,
        course_id: str,
        certificate_id: str
    ) -> Optional[Certificate]:
        """Get certificate by ID."""
        try:
            cert_dir = self.certificates_dir / course_id / certificate_id

            if not cert_dir.exists():
                return None

            # Load payload
            payload_path = cert_dir / "certificate.json"
            if not payload_path.exists():
                return None

            with open(payload_path, 'r', encoding='utf-8') as f:
                payload_data = json.load(f)
            payload = CertificatePayload(**payload_data)

            # Load signature
            sig_path = cert_dir / "certificate.sig"
            if not sig_path.exists():
                return None

            with open(sig_path, 'r', encoding='utf-8') as f:
                signature_hex = f.read().strip()

            return Certificate(payload=payload, signature_hex=signature_hex)
        except Exception as e:
            logger.error(f"[MonetizationStorage] Failed to get certificate: {e}")
            return None

    # ========================================
    # Pack Operations
    # ========================================

    def save_pack(self, course_id: str, pack: MicroNichePack) -> bool:
        """Save pack with atomic write."""
        try:
            pack_dir = self.packs_dir / course_id
            pack_dir.mkdir(parents=True, exist_ok=True)

            packs_file = pack_dir / "packs.json"

            # Load existing packs
            packs = []
            if packs_file.exists():
                with file_lock(packs_file, 'r') as f:
                    packs = json.load(f)

            # Add or update pack
            pack_data = pack.model_dump()
            existing_idx = next(
                (i for i, p in enumerate(packs) if p.get('pack_id') == pack.pack_id),
                None
            )

            if existing_idx is not None:
                packs[existing_idx] = pack_data
            else:
                packs.append(pack_data)

            # Atomic write
            with file_lock(packs_file, 'w') as f:
                json.dump(packs, f, indent=2, ensure_ascii=False)

            logger.info(f"[MonetizationStorage] Pack saved: {pack.pack_id}")
            return True
        except Exception as e:
            logger.error(f"[MonetizationStorage] Failed to save pack: {e}")
            return False

    def get_pack(self, course_id: str, pack_id: str) -> Optional[MicroNichePack]:
        """Get pack by ID."""
        try:
            packs_file = self.packs_dir / course_id / "packs.json"

            if not packs_file.exists():
                return None

            with file_lock(packs_file, 'r') as f:
                packs = json.load(f)

            pack_data = next((p for p in packs if p.get('pack_id') == pack_id), None)

            if pack_data:
                return MicroNichePack(**pack_data)
            return None
        except Exception as e:
            logger.error(f"[MonetizationStorage] Failed to get pack: {e}")
            return None

    def get_packs_by_course(self, course_id: str) -> List[MicroNichePack]:
        """Get all packs for a course."""
        try:
            packs_file = self.packs_dir / course_id / "packs.json"

            if not packs_file.exists():
                return []

            with file_lock(packs_file, 'r') as f:
                packs_data = json.load(f)

            return [MicroNichePack(**p) for p in packs_data]
        except Exception as e:
            logger.error(f"[MonetizationStorage] Failed to get packs: {e}")
            return []


# ========================================
# Singleton
# ========================================

_storage: Optional[MonetizationStorage] = None


def get_monetization_storage() -> MonetizationStorage:
    """Get MonetizationStorage singleton."""
    global _storage
    if _storage is None:
        _storage = MonetizationStorage()
    return _storage
