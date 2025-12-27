"""
Licensing Storage Adapter

Sprint 17: Monetization, Licensing & Certificates
File-based atomic storage for licenses.
"""

from __future__ import annotations

import fcntl
import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .licensing_models import License, LicenseStatus, LicenseType


STORAGE_BASE = Path("storage/licensing")
LICENSES_FILE = STORAGE_BASE / "licenses.json"
AUDIT_LOG_FILE = STORAGE_BASE / "audit.jsonl"
STATS_FILE = STORAGE_BASE / "stats.json"


@contextmanager
def file_lock(file_path: Path, mode: str = 'r'):
    """Atomic file operations with exclusive locking."""
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if mode == 'r' and not file_path.exists():
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({} if file_path.suffix == '.json' else [], f)

    with open(file_path, mode, encoding='utf-8') as f:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            yield f
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class LicensingStorage:
    """Storage adapter for licenses."""

    def __init__(self, storage_path: Path = STORAGE_BASE):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._initialize_storage()

    def _initialize_storage(self):
        """Initialize storage files."""
        files = [
            (LICENSES_FILE, {}),
            (STATS_FILE, {"total": 0, "active": 0, "revoked": 0, "expired": 0}),
        ]
        for file_path, default_content in files:
            if not file_path.exists():
                with file_lock(file_path, 'w') as f:
                    json.dump(default_content, f, indent=2)

        if not AUDIT_LOG_FILE.exists():
            AUDIT_LOG_FILE.touch()

    def save_license(self, license: License) -> bool:
        """Save or update license."""
        license.updated_at = datetime.utcnow().timestamp()

        with file_lock(LICENSES_FILE, 'r') as f:
            licenses = json.load(f)

        licenses[license.license_id] = license.model_dump()

        with file_lock(LICENSES_FILE, 'w') as f:
            json.dump(licenses, f, indent=2)

        self._update_stats()
        return True

    def get_license(self, license_id: str) -> Optional[License]:
        """Get license by ID."""
        with file_lock(LICENSES_FILE, 'r') as f:
            licenses = json.load(f)

        data = licenses.get(license_id)
        if not data:
            return None

        license = License(**data)

        # Auto-expire if needed
        if license.is_expired() and license.status == LicenseStatus.ACTIVE:
            license.status = LicenseStatus.EXPIRED
            self.save_license(license)

        return license

    def list_licenses(
        self,
        status: Optional[LicenseStatus] = None,
        license_type: Optional[LicenseType] = None,
        holder_reference: Optional[str] = None,
    ) -> List[License]:
        """List licenses with filters."""
        with file_lock(LICENSES_FILE, 'r') as f:
            licenses = json.load(f)

        results = []
        for data in licenses.values():
            license = License(**data)

            # Auto-expire
            if license.is_expired() and license.status == LicenseStatus.ACTIVE:
                license.status = LicenseStatus.EXPIRED
                self.save_license(license)

            # Apply filters
            if status and license.status != status:
                continue
            if license_type and license.type != license_type:
                continue
            if holder_reference and license.holder.reference != holder_reference:
                continue

            results.append(license)

        results.sort(key=lambda x: x.issued_at, reverse=True)
        return results

    def _update_stats(self):
        """Update statistics."""
        with file_lock(LICENSES_FILE, 'r') as f:
            licenses = json.load(f)

        stats = {
            "total": len(licenses),
            "active": 0,
            "revoked": 0,
            "expired": 0,
            "by_type": {},
            "by_holder_type": {},
            "by_issued_reason": {},
        }

        for data in licenses.values():
            license = License(**data)

            if license.status == LicenseStatus.ACTIVE and not license.is_expired():
                stats["active"] += 1
            elif license.status == LicenseStatus.REVOKED:
                stats["revoked"] += 1
            elif license.is_expired():
                stats["expired"] += 1

            type_key = license.type.value
            stats["by_type"][type_key] = stats["by_type"].get(type_key, 0) + 1

            holder_key = license.holder.type.value
            stats["by_holder_type"][holder_key] = stats["by_holder_type"].get(holder_key, 0) + 1

            reason_key = license.issued_reason.value
            stats["by_issued_reason"][reason_key] = stats["by_issued_reason"].get(reason_key, 0) + 1

        with file_lock(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)

    def get_stats(self):
        """Get statistics."""
        with file_lock(STATS_FILE, 'r') as f:
            return json.load(f)
