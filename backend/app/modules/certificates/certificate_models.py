"""Sprint 17: Enhanced Certificate Models (extends Sprint 14)"""
from pydantic import BaseModel, Field
from typing import Optional

class EnhancedCertificate(BaseModel):
    """Enhanced certificate with licensing integration."""
    certificate_id: str
    course_id: str
    course_version: str
    issued_at: float
    holder_reference: str  # Links to license holder (NO PII)
    issuer: str = "BRAiN"
    signature_hex: str
    license_id: Optional[str] = None  # Linked license
    revocable: bool = True
    revoked_at: Optional[float] = None
    metadata: dict = Field(default_factory=dict)
    model_config = {"extra": "forbid"}

class CertificateVerificationResult(BaseModel):
    """Certificate verification result."""
    valid: bool
    certificate_id: str
    signature_valid: bool
    revoked: bool
    reason: Optional[str] = None
    model_config = {"extra": "forbid"}
