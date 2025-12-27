"""Sprint 17: Licensing Service - Compact but complete"""
from datetime import datetime
from typing import List, Optional
from loguru import logger
from .licensing_models import *
from .licensing_storage import LicensingStorage

class LicensingService:
    def __init__(self, storage: Optional[LicensingStorage] = None):
        self.storage = storage or LicensingStorage()

    async def issue_license(self, request: LicenseIssueRequest) -> License:
        """Issue new license."""
        license = License(
            type=request.type,
            scope=request.scope,
            holder=request.holder,
            rights=request.rights,
            valid_from=request.valid_from or datetime.utcnow().timestamp(),
            valid_until=request.valid_until,
            issued_reason=request.issued_reason,
            issued_by=request.issued_by,
            revocable=request.revocable,
            metadata=request.metadata,
        )
        self.storage.save_license(license)
        logger.info(f"License issued: {license.license_id}")
        return license

    async def validate_license(self, license_id: str, required_right: Optional[LicenseRight] = None) -> dict:
        """Validate license and optionally check specific right."""
        license = self.storage.get_license(license_id)
        if not license:
            return {"valid": False, "reason": "License not found"}

        if not license.is_active():
            return {
                "valid": False,
                "reason": f"License not active (status: {license.status})",
                "status": license.status,
            }

        if required_right and not license.has_right(required_right):
            return {
                "valid": False,
                "reason": f"License does not grant right: {required_right}",
                "rights": [r.value for r in license.rights.rights],
            }

        return {
            "valid": True,
            "license_id": license.license_id,
            "status": license.status,
            "rights": [r.value for r in license.rights.rights],
            "expires_at": license.valid_until,
            "time_until_expiry": license.time_until_expiry(),
        }

    async def revoke_license(self, license_id: str, revoked_by: str, reason: str) -> License:
        """Revoke license."""
        license = self.storage.get_license(license_id)
        if not license:
            raise ValueError(f"License {license_id} not found")

        if not license.revocable:
            raise ValueError("License is not revocable")

        if license.status == LicenseStatus.REVOKED:
            raise ValueError("License already revoked")

        license.status = LicenseStatus.REVOKED
        license.revoked_at = datetime.utcnow().timestamp()
        license.revoked_by = revoked_by
        license.revocation_reason = reason

        self.storage.save_license(license)
        logger.info(f"License revoked: {license_id} by {revoked_by}")
        return license

    async def get_license(self, license_id: str) -> Optional[License]:
        """Get license details."""
        return self.storage.get_license(license_id)

    async def list_licenses(self, **filters) -> List[License]:
        """List licenses with filters."""
        return self.storage.list_licenses(**filters)

    async def get_stats(self) -> dict:
        """Get licensing statistics."""
        return self.storage.get_stats()
