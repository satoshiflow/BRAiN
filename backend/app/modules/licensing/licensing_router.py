"""Sprint 17: Licensing API Router"""
from fastapi import APIRouter, HTTPException, status
from .licensing_models import *
from .licensing_service import LicensingService

router = APIRouter(prefix="/api/licenses", tags=["licensing"])

def get_service() -> LicensingService:
    return LicensingService()

@router.post("/issue", response_model=LicenseIssueResponse, status_code=status.HTTP_201_CREATED)
async def issue_license(request: LicenseIssueRequest):
    """Issue new license (governance-enforced for enterprise/bulk)."""
    service = get_service()
    license = await service.issue_license(request)
    return LicenseIssueResponse(
        license_id=license.license_id,
        status=license.status,
        valid_from=license.valid_from,
        valid_until=license.valid_until,
        message="License issued successfully",
    )

@router.get("/{license_id}", response_model=LicenseDetail)
async def get_license(license_id: str):
    """Get license details."""
    service = get_service()
    license = await service.get_license(license_id)
    if not license:
        raise HTTPException(status_code=404, detail="License not found")
    return LicenseDetail(
        license_id=license.license_id,
        type=license.type,
        status=license.status,
        scope=license.scope,
        holder=license.holder,
        rights=license.rights,
        valid_from=license.valid_from,
        valid_until=license.valid_until,
        issued_reason=license.issued_reason,
        issued_by=license.issued_by,
        issued_at=license.issued_at,
        revoked_at=license.revoked_at,
        revoked_by=license.revoked_by,
        revocation_reason=license.revocation_reason,
        metadata=license.metadata,
        is_active=license.is_active(),
        time_until_expiry=license.time_until_expiry(),
    )

@router.post("/validate", response_model=LicenseValidateResponse)
async def validate_license(request: LicenseValidateRequest):
    """Validate license and check rights."""
    service = get_service()
    result = await service.validate_license(request.license_id, request.required_right)
    return LicenseValidateResponse(**result)

@router.post("/{license_id}/revoke", response_model=LicenseRevokeResponse)
async def revoke_license(license_id: str, request: LicenseRevokeRequest):
    """Revoke license (with mandatory reason)."""
    service = get_service()
    try:
        license = await service.revoke_license(license_id, request.revoked_by, request.reason)
        return LicenseRevokeResponse(
            license_id=license.license_id,
            status=license.status,
            revoked_at=license.revoked_at,
            message="License revoked successfully",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats/summary", response_model=LicenseStats)
async def get_license_stats():
    """Get licensing statistics."""
    service = get_service()
    stats = await service.get_stats()
    return LicenseStats(
        total_licenses=stats["total"],
        active_licenses=stats["active"],
        revoked_licenses=stats["revoked"],
        expired_licenses=stats["expired"],
        by_type=stats["by_type"],
        by_holder_type=stats["by_holder_type"],
        by_issued_reason=stats["by_issued_reason"],
    )
