"""
Odoo Module Registry Service

Manages module storage, versioning, and release tracking.
Sprint IV: AXE × Odoo Integration
"""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from backend.app.modules.axe_odoo_generator.schemas import (
    GeneratedFile,
    OdooModuleGenerationResult,
)

from .schemas import (
    ModuleRegistryInfo,
    ModuleReleaseRecord,
    ModuleVersion,
)


class OdooModuleRegistry:
    """
    Registry for Odoo modules with version management.

    Storage structure:
    storage/odoo/
    ├── modules/
    │   └── {module_name}/
    │       ├── versions.json        # Version metadata
    │       ├── releases.json        # Release history
    │       ├── {version}/           # Module files
    │       │   ├── __manifest__.py
    │       │   ├── models/
    │       │   └── views/
    │       └── ...
    └── audit/                       # Audit logs (JSONL)
    """

    def __init__(self, storage_base: str = "storage/odoo"):
        """
        Initialize registry.

        Args:
            storage_base: Base path for Odoo storage
        """
        self.storage_base = Path(storage_base)
        self.modules_dir = self.storage_base / "modules"
        self.audit_dir = self.storage_base / "audit"

        # Ensure directories exist
        self.modules_dir.mkdir(parents=True, exist_ok=True)
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def store_module(
        self, generation_result: OdooModuleGenerationResult
    ) -> ModuleVersion:
        """
        Store generated module and create version record.

        Args:
            generation_result: Generated module result

        Returns:
            ModuleVersion record

        Raises:
            ValueError: If generation failed or module invalid
        """
        if not generation_result.success:
            raise ValueError(
                f"Cannot store failed generation: {generation_result.errors}"
            )

        module_name = generation_result.module_name
        version = generation_result.version
        module_hash = generation_result.module_hash

        # Module directory
        module_dir = self.modules_dir / module_name
        module_dir.mkdir(parents=True, exist_ok=True)

        # Version directory
        version_dir = module_dir / version

        # Check if version already exists
        if version_dir.exists():
            logger.warning(
                f"Version {version} of module {module_name} already exists - overwriting"
            )
            shutil.rmtree(version_dir)

        version_dir.mkdir(parents=True, exist_ok=True)

        # Write generated files
        for file in generation_result.files:
            file_path = version_dir / file.path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            file_path.write_text(file.content, encoding="utf-8")

        logger.info(
            f"Stored module {module_name} v{version} ({len(generation_result.files)} files)"
        )

        # Create version record
        version_record = ModuleVersion(
            module_name=module_name,
            version=version,
            module_hash=module_hash or "",
            storage_path=str(version_dir),
            file_count=len(generation_result.files),
            metadata={
                "warnings": generation_result.warnings,
                "generation_metadata": generation_result.metadata,
            },
        )

        # Update versions.json
        self._update_versions_json(module_name, version_record)

        # Cleanup old versions (keep last 3)
        self._cleanup_old_versions(module_name)

        return version_record

    def get_module_versions(self, module_name: str) -> List[ModuleVersion]:
        """
        Get all versions of a module.

        Args:
            module_name: Module technical name

        Returns:
            List of ModuleVersion records (newest first)
        """
        versions_file = self.modules_dir / module_name / "versions.json"

        if not versions_file.exists():
            return []

        with open(versions_file, "r") as f:
            data = json.load(f)

        versions = [ModuleVersion(**v) for v in data.get("versions", [])]

        # Sort by created_at descending
        versions.sort(key=lambda v: v.created_at, reverse=True)

        return versions

    def get_module_version(
        self, module_name: str, version: str
    ) -> Optional[ModuleVersion]:
        """
        Get specific version of a module.

        Args:
            module_name: Module technical name
            version: Version string

        Returns:
            ModuleVersion if found, None otherwise
        """
        versions = self.get_module_versions(module_name)
        return next((v for v in versions if v.version == version), None)

    def get_latest_version(self, module_name: str) -> Optional[ModuleVersion]:
        """
        Get latest version of a module.

        Args:
            module_name: Module technical name

        Returns:
            ModuleVersion if found, None otherwise
        """
        versions = self.get_module_versions(module_name)
        return versions[0] if versions else None

    def get_module_path(self, module_name: str, version: str) -> Optional[Path]:
        """
        Get filesystem path to module version.

        Args:
            module_name: Module technical name
            version: Version string

        Returns:
            Path to module directory if exists, None otherwise
        """
        version_dir = self.modules_dir / module_name / version

        if version_dir.exists():
            return version_dir

        return None

    def create_release_record(
        self, module_name: str, version: str, odoo_status: str
    ) -> ModuleReleaseRecord:
        """
        Create release record for installed module.

        Args:
            module_name: Module technical name
            version: Module version
            odoo_status: Odoo module state (e.g., "installed")

        Returns:
            ModuleReleaseRecord
        """
        # Get version info
        version_record = self.get_module_version(module_name, version)
        if not version_record:
            raise ValueError(
                f"Module {module_name} version {version} not found in registry"
            )

        # Generate release ID
        release_id = f"odoo_{module_name}_{version}_{uuid.uuid4().hex[:8]}"

        # Create release record
        release = ModuleReleaseRecord(
            release_id=release_id,
            module_name=module_name,
            version=version,
            module_hash=version_record.module_hash,
            installed_at=datetime.utcnow(),
            odoo_status=odoo_status,
            is_current=True,
        )

        # Update releases.json
        self._update_releases_json(module_name, release)

        logger.info(
            f"Created release record {release_id} for {module_name} v{version}"
        )

        return release

    def get_current_release(self, module_name: str) -> Optional[ModuleReleaseRecord]:
        """
        Get current deployed release for a module.

        Args:
            module_name: Module technical name

        Returns:
            ModuleReleaseRecord if found, None otherwise
        """
        releases = self._load_releases_json(module_name)
        return next((r for r in releases if r.is_current), None)

    def get_release_history(
        self, module_name: str, limit: int = 10
    ) -> List[ModuleReleaseRecord]:
        """
        Get release history for a module.

        Args:
            module_name: Module technical name
            limit: Maximum number of releases to return

        Returns:
            List of ModuleReleaseRecord (newest first)
        """
        releases = self._load_releases_json(module_name)

        # Sort by installed_at descending
        releases.sort(
            key=lambda r: r.installed_at or datetime.min, reverse=True
        )

        return releases[:limit]

    def list_all_modules(self) -> List[ModuleRegistryInfo]:
        """
        List all registered modules.

        Returns:
            List of ModuleRegistryInfo
        """
        modules_info = []

        for module_dir in self.modules_dir.iterdir():
            if not module_dir.is_dir():
                continue

            module_name = module_dir.name
            versions = self.get_module_versions(module_name)

            if not versions:
                continue

            current_release = self.get_current_release(module_name)
            current_version = current_release.version if current_release else None
            latest_version = versions[0].version
            created_at = versions[-1].created_at
            updated_at = versions[0].created_at

            modules_info.append(
                ModuleRegistryInfo(
                    module_name=module_name,
                    versions=versions,
                    current_version=current_version,
                    latest_version=latest_version,
                    total_versions=len(versions),
                    created_at=created_at,
                    updated_at=updated_at,
                )
            )

        # Sort by updated_at descending
        modules_info.sort(key=lambda m: m.updated_at, reverse=True)

        return modules_info

    def _update_versions_json(
        self, module_name: str, version_record: ModuleVersion
    ):
        """Update versions.json with new version."""
        versions_file = self.modules_dir / module_name / "versions.json"

        # Load existing versions
        if versions_file.exists():
            with open(versions_file, "r") as f:
                data = json.load(f)
            versions = data.get("versions", [])
        else:
            versions = []

        # Add new version (remove if already exists)
        versions = [
            v for v in versions if v.get("version") != version_record.version
        ]
        versions.append(version_record.model_dump(mode="json"))

        # Save
        with open(versions_file, "w") as f:
            json.dump({"versions": versions}, f, indent=2, default=str)

    def _update_releases_json(
        self, module_name: str, release_record: ModuleReleaseRecord
    ):
        """Update releases.json with new release."""
        releases_file = self.modules_dir / module_name / "releases.json"

        # Load existing releases
        releases = self._load_releases_json(module_name)

        # Mark all as not current
        for r in releases:
            r.is_current = False

        # Add new release
        releases.append(release_record)

        # Save
        with open(releases_file, "w") as f:
            json.dump(
                {"releases": [r.model_dump(mode="json") for r in releases]},
                f,
                indent=2,
                default=str,
            )

    def _load_releases_json(self, module_name: str) -> List[ModuleReleaseRecord]:
        """Load releases from releases.json."""
        releases_file = self.modules_dir / module_name / "releases.json"

        if not releases_file.exists():
            return []

        with open(releases_file, "r") as f:
            data = json.load(f)

        return [ModuleReleaseRecord(**r) for r in data.get("releases", [])]

    def _cleanup_old_versions(self, module_name: str, keep_count: int = 3):
        """
        Remove old versions, keeping the most recent {keep_count}.

        Args:
            module_name: Module technical name
            keep_count: Number of versions to keep
        """
        versions = self.get_module_versions(module_name)

        if len(versions) <= keep_count:
            return  # Nothing to clean up

        # Get versions to remove (oldest first)
        versions_to_remove = versions[keep_count:]

        for version in versions_to_remove:
            version_dir = Path(version.storage_path)

            if version_dir.exists():
                shutil.rmtree(version_dir)
                logger.info(
                    f"Removed old version {module_name} v{version.version}"
                )

        # Update versions.json (remove deleted versions)
        remaining_versions = versions[:keep_count]
        versions_file = self.modules_dir / module_name / "versions.json"

        with open(versions_file, "w") as f:
            json.dump(
                {"versions": [v.model_dump(mode="json") for v in remaining_versions]},
                f,
                indent=2,
                default=str,
            )


# Singleton instance
_registry: Optional[OdooModuleRegistry] = None


def get_odoo_registry() -> OdooModuleRegistry:
    """
    Get singleton Odoo module registry.

    Returns:
        OdooModuleRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = OdooModuleRegistry()
    return _registry
