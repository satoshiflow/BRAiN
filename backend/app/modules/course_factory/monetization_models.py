"""
Course Factory Monetization Models - Sprint 14

Data models for enrollment, progress tracking, certificates, and micro-niche packs.
Privacy-first, backwards compatible, fail-closed.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator


# ========================================
# Enrollment & Progress Models
# ========================================

class ProgressStatus(str, Enum):
    """Progress status for chapters/modules."""
    STARTED = "started"
    COMPLETED = "completed"


class CourseEnrollment(BaseModel):
    """Course enrollment record."""
    enrollment_id: str = Field(default_factory=lambda: f"enr_{uuid4().hex[:16]}")
    course_id: str
    language: str = "de"  # de/en/fr/es
    actor_id: str  # Pseudonymous internal ID or hashed ID
    enrolled_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())

    class Config:
        extra = "forbid"


class CourseProgress(BaseModel):
    """Progress tracking for course modules/chapters."""
    progress_id: str = Field(default_factory=lambda: f"prg_{uuid4().hex[:16]}")
    enrollment_id: str
    module_id: Optional[str] = None
    chapter_id: Optional[str] = None
    status: ProgressStatus
    updated_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())

    class Config:
        extra = "forbid"


class CourseCompletion(BaseModel):
    """Course completion record."""
    completion_id: str = Field(default_factory=lambda: f"cmp_{uuid4().hex[:16]}")
    enrollment_id: str
    course_id: str
    actor_id: str
    completed_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    completion_hash: str  # SHA-256 over course_id + actor_id + completed_at + course_version
    course_version: str = "1.0.0"

    class Config:
        extra = "forbid"


class EnrollmentStatus(BaseModel):
    """Combined enrollment status."""
    enrollment: CourseEnrollment
    progress: List[CourseProgress]
    completion: Optional[CourseCompletion] = None
    completion_percentage: float = 0.0

    class Config:
        extra = "forbid"


# ========================================
# Certificate Models
# ========================================

class CertificatePayload(BaseModel):
    """
    Canonical certificate payload.

    This payload is signed with Ed25519 for offline verification.
    MUST use stable canonical JSON (sorted keys, separators, utf-8).
    """
    certificate_id: str = Field(default_factory=lambda: f"cert_{uuid4().hex[:16]}")
    course_id: str
    course_title: str
    language: str
    actor_id: str  # Pseudonymous
    completed_at: float
    completion_hash: str
    issuer: str = "BRAiN"
    issued_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    schema_version: str = "cert-v1"

    class Config:
        extra = "forbid"

    def to_canonical_json(self) -> str:
        """
        Convert to canonical JSON for signing.

        Ensures deterministic output:
        - Sorted keys
        - No whitespace
        - UTF-8 encoding
        """
        import json
        return json.dumps(
            self.model_dump(),
            sort_keys=True,
            separators=(',', ':'),
            ensure_ascii=False
        )


class Certificate(BaseModel):
    """Complete certificate with payload and signature."""
    payload: CertificatePayload
    signature_hex: str  # 128 chars hex (Ed25519 signature)

    class Config:
        extra = "forbid"


class CertificateVerificationResult(BaseModel):
    """Certificate verification result."""
    valid: bool
    reason: Optional[str] = None
    certificate_id: Optional[str] = None
    issued_at: Optional[float] = None

    class Config:
        extra = "forbid"


# ========================================
# Micro-Niche Content Pack Models
# ========================================

class PackOperation(str, Enum):
    """Allowed pack operations."""
    REPLACE_TEXT = "replace_text"
    APPEND_MODULE = "append_module"
    OVERRIDE_TITLE = "override_title"
    OVERRIDE_DESCRIPTION = "override_description"


class ContentOverride(BaseModel):
    """Single content override operation."""
    operation: PackOperation
    target_id: str  # Module/lesson/section ID
    value: Any  # Replacement value (string, dict, etc.)

    class Config:
        extra = "forbid"


class MicroNichePack(BaseModel):
    """Micro-niche content pack for course variants."""
    pack_id: str = Field(default_factory=lambda: f"pack_{uuid4().hex[:16]}")
    base_course_id: str
    target_audience: str  # e.g., "retirees", "students", "freelancers"
    language: str = "de"
    overrides: List[ContentOverride] = []
    created_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    version: str = "1.0.0"
    description: Optional[str] = None

    class Config:
        extra = "forbid"


class PackRenderResult(BaseModel):
    """Result of rendering a course with a pack."""
    pack_id: str
    base_course_id: str
    rendered_course: Dict[str, Any]  # Rendered course structure
    applied_overrides: int
    render_timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp())

    class Config:
        extra = "forbid"


# ========================================
# Analytics Models
# ========================================

class CourseAnalyticsSummary(BaseModel):
    """
    Aggregated course analytics (NO PII).

    Privacy-first: only aggregate statistics, no individual user data.
    """
    course_id: str
    total_enrollments: int = 0
    enrollments_by_language: Dict[str, int] = {}
    total_completions: int = 0
    completion_rate: float = 0.0
    certificate_issuance_count: int = 0
    chapter_dropoff: Dict[str, int] = {}  # chapter_id -> started_but_not_completed
    avg_completion_time_days: Optional[float] = None
    last_updated: float = Field(default_factory=lambda: datetime.utcnow().timestamp())

    class Config:
        extra = "forbid"


class AnalyticsExport(BaseModel):
    """Analytics export format."""
    course_id: str
    export_format: str  # "csv" or "json"
    summary: CourseAnalyticsSummary
    exported_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())

    class Config:
        extra = "forbid"


# ========================================
# Marketplace Models
# ========================================

class CourseCatalogMetadata(BaseModel):
    """
    Course catalog metadata for marketplace.

    Read-only, no payments.
    """
    course_id: str
    title: str
    description: str
    price_display: str = "Free"  # e.g., "49€" or "Free"
    target_audiences: List[str] = []
    languages: List[str] = ["de"]
    certificate_available: bool = True
    version: str = "1.0.0"
    tags: List[str] = []
    total_modules: int = 0
    total_lessons: int = 0
    estimated_duration_minutes: int = 0
    created_at: Optional[float] = None
    updated_at: Optional[float] = None

    class Config:
        extra = "forbid"


class CourseCatalogCard(BaseModel):
    """Course catalog card (summary view)."""
    course_id: str
    title: str
    description: str
    price_display: str
    languages: List[str]
    certificate_available: bool
    tags: List[str]
    estimated_duration_minutes: int

    class Config:
        extra = "forbid"


# ========================================
# API Request/Response Models
# ========================================

class EnrollRequest(BaseModel):
    """Enrollment request."""
    language: str = "de"
    actor_id: Optional[str] = None  # Optional if derived from auth context

    class Config:
        extra = "forbid"


class ProgressUpdateRequest(BaseModel):
    """Progress update request."""
    enrollment_id: str
    chapter_id: Optional[str] = None
    module_id: Optional[str] = None
    status: ProgressStatus

    @field_validator('chapter_id', 'module_id')
    @classmethod
    def validate_identifier(cls, v, info):
        """Ensure at least one identifier is provided."""
        if info.data.get('chapter_id') is None and info.data.get('module_id') is None:
            raise ValueError("Either chapter_id or module_id must be provided")
        return v

    class Config:
        extra = "forbid"


class CertificateIssueRequest(BaseModel):
    """Certificate issuance request."""
    enrollment_id: str

    class Config:
        extra = "forbid"


class CertificateVerifyRequest(BaseModel):
    """Certificate verification request."""
    certificate_payload: Dict[str, Any]  # CertificatePayload as dict
    signature_hex: str

    class Config:
        extra = "forbid"


class PackCreateRequest(BaseModel):
    """Pack creation request."""
    target_audience: str
    language: str = "de"
    overrides: List[ContentOverride]
    description: Optional[str] = None

    class Config:
        extra = "forbid"
