"""Sprint 17: Certificate Router (extends Sprint 14)"""
from fastapi import APIRouter, HTTPException
from backend.app.modules.course_factory.certificate_signer import CertificateSigner
from backend.app.modules.course_factory.monetization_models import CertificatePayload
from .certificate_models import *

router = APIRouter(prefix="/api/certificates/v2", tags=["certificates-v2"])

@router.post("/verify")
async def verify_certificate(payload: dict, signature: str):
    """Verify certificate signature."""
    signer = CertificateSigner()
    cert_payload = CertificatePayload(**payload)
    is_valid = signer.verify_certificate(cert_payload, signature)
    return CertificateVerificationResult(
        valid=is_valid,
        certificate_id=payload["certificate_id"],
        signature_valid=is_valid,
        revoked=False,  # TODO: Check revocation list
        reason=None if is_valid else "Invalid signature",
    )
