"""
Licensing Data Models

Sprint 17: Monetization, Licensing & Certificates
Models for course access licenses and rights management.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class LicenseType(str, Enum):
    """Types of licenses."""
    COURSE_ACCESS = "course_access"
    CERTIFICATE = "certificate"
    ENTERPRISE = "enterprise"
    TRIAL = "trial"
    PROMOTION = "promotion"


class LicenseStatus(str, Enum):
    """License status."""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class HolderType(str, Enum):
    """Type of license holder."""
    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"
    ANONYMOUS = "anonymous"


class LicenseRight(str, Enum):
    """Individual rights that can be granted."""
    VIEW = "view"
    DOWNLOAD = "download"
    CERTIFICATE_ISSUE = "certificate_issue"
    SHARE = "share"
    EMBED = "embed"


class IssuedReason(str, Enum):
    """Reason for license issuance."""
    PURCHASE = "purchase"
    GRANT = "grant"
    PARTNER = "partner"
    PROMOTION = "promotion"
    TRIAL = "trial"
    INTERNAL = "internal"


class LicenseScope(BaseModel):
    """
    Scope of license - what content it covers.

    Defines which course, version, and language the license grants access to.
    """
    course_id: str = Field(..., description="Course ID")
    version: str = Field(default="v1", description="Course version")
    language: str = Field(..., description="Course language (ISO code)")
    modules: Optional[List[str]] = Field(None, description="Specific modules (if not full course)")

    model_config = {"extra": "forbid"}


class LicenseHolder(BaseModel):
    """
    License holder information (privacy-preserving).

    NO PII stored directly. Uses hash or external reference.
    """
    type: HolderType
    reference: str = Field(..., description="Hash or external ID (NO PII)")
    display_name: Optional[str] = Field(None, description="Optional display name")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = {"extra": "forbid"}


class LicenseRights(BaseModel):
    """
    Rights granted by license.

    Defines what the holder can do with the licensed content.
    """
    rights: List[LicenseRight] = Field(default_factory=list, description="Granted rights")
    transferable: bool = Field(default=False, description="Can be transferred to another holder")
    sublicensable: bool = Field(default=False, description="Can sublicense to others")
    commercial_use: bool = Field(default=False, description="Allowed for commercial use")

    model_config = {"extra": "forbid"}


class License(BaseModel):
    """
    License record.

    Represents a license granting specific rights to access/use content.
    """
    # Identity
    license_id: str = Field(default_factory=lambda: f"license_{uuid4().hex[:16]}")

    # Type & Status
    type: LicenseType
    status: LicenseStatus = Field(default=LicenseStatus.ACTIVE)

    # Scope - What is licensed
    scope: LicenseScope

    # Holder - Who holds the license (NO PII)
    holder: LicenseHolder

    # Rights - What can be done
    rights: LicenseRights

    # Validity Period
    valid_from: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    valid_until: Optional[float] = Field(None, description="Expiry timestamp (null = perpetual)")

    # Issuance
    issued_reason: IssuedReason
    issued_by: str = Field(..., description="Actor who issued license")
    issued_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())

    # Revocation
    revocable: bool = Field(default=True, description="Can be revoked")
    revoked_at: Optional[float] = None
    revoked_by: Optional[str] = None
    revocation_reason: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    updated_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())

    model_config = {"extra": "forbid"}

    def is_active(self) -> bool:
        """Check if license is currently active."""
        if self.status != LicenseStatus.ACTIVE:
            return False

        now = datetime.utcnow().timestamp()

        # Check validity period
        if now < self.valid_from:
            return False

        if self.valid_until and now > self.valid_until:
            return False

        return True

    def is_expired(self) -> bool:
        """Check if license has expired."""
        if self.valid_until is None:
            return False  # Perpetual license

        now = datetime.utcnow().timestamp()
        return now > self.valid_until

    def has_right(self, right: LicenseRight) -> bool:
        """Check if license grants specific right."""
        return right in self.rights.rights

    def time_until_expiry(self) -> Optional[float]:
        """Get seconds until expiry (None if perpetual)."""
        if self.valid_until is None:
            return None

        now = datetime.utcnow().timestamp()
        return self.valid_until - now


# Request/Response Models for API

class LicenseIssueRequest(BaseModel):
    """Request to issue new license."""
    type: LicenseType
    scope: LicenseScope
    holder: LicenseHolder
    rights: LicenseRights
    valid_from: Optional[float] = None  # Default: now
    valid_until: Optional[float] = None  # Default: perpetual
    issued_reason: IssuedReason
    issued_by: str
    revocable: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class LicenseIssueResponse(BaseModel):
    """Response after issuing license."""
    license_id: str
    status: LicenseStatus
    valid_from: float
    valid_until: Optional[float]
    message: str

    model_config = {"extra": "forbid"}


class LicenseValidateRequest(BaseModel):
    """Request to validate license."""
    license_id: str
    required_right: Optional[LicenseRight] = None

    model_config = {"extra": "forbid"}


class LicenseValidateResponse(BaseModel):
    """Response after validating license."""
    valid: bool
    license_id: str
    status: LicenseStatus
    rights: List[LicenseRight]
    expires_at: Optional[float]
    time_until_expiry: Optional[float]
    reason: Optional[str] = None  # If invalid

    model_config = {"extra": "forbid"}


class LicenseRevokeRequest(BaseModel):
    """Request to revoke license."""
    license_id: str
    revoked_by: str
    reason: str = Field(..., min_length=10, description="Revocation reason (min 10 chars)")

    model_config = {"extra": "forbid"}


class LicenseRevokeResponse(BaseModel):
    """Response after revoking license."""
    license_id: str
    status: LicenseStatus
    revoked_at: float
    message: str

    model_config = {"extra": "forbid"}


class LicenseSummary(BaseModel):
    """Summary for license list."""
    license_id: str
    type: LicenseType
    status: LicenseStatus
    scope: LicenseScope
    holder_type: HolderType
    rights: List[LicenseRight]
    valid_from: float
    valid_until: Optional[float]
    is_active: bool

    model_config = {"extra": "forbid"}


class LicenseDetail(BaseModel):
    """Detailed license information."""
    license_id: str
    type: LicenseType
    status: LicenseStatus
    scope: LicenseScope
    holder: LicenseHolder
    rights: LicenseRights
    valid_from: float
    valid_until: Optional[float]
    issued_reason: IssuedReason
    issued_by: str
    issued_at: float
    revoked_at: Optional[float]
    revoked_by: Optional[str]
    revocation_reason: Optional[str]
    metadata: Dict[str, Any]
    is_active: bool
    time_until_expiry: Optional[float]

    model_config = {"extra": "forbid"}


class LicenseStats(BaseModel):
    """License system statistics."""
    total_licenses: int
    active_licenses: int
    revoked_licenses: int
    expired_licenses: int
    by_type: Dict[str, int]
    by_holder_type: Dict[str, int]
    by_issued_reason: Dict[str, int]

    model_config = {"extra": "forbid"}
