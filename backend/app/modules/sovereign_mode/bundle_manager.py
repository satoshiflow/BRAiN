"""
Bundle Manager

Offline model bundle discovery, validation, and management.
Handles bundle lifecycle from discovery to loading.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from backend.app.modules.sovereign_mode.schemas import (
    Bundle,
    BundleStatus,
    ValidationResult,
    AuditEventType,
)
from backend.app.modules.sovereign_mode.hash_validator import get_hash_validator
from backend.app.modules.sovereign_mode.signature_validator import (
    get_signature_validator,
    SignaturePolicy,
)
from backend.app.modules.sovereign_mode.governance_metrics import (
    get_governance_metrics,
)


class BundleManager:
    """Manages offline model bundles."""

    DEFAULT_BUNDLES_DIR = "storage/models/bundles"
    DEFAULT_QUARANTINE_DIR = "storage/quarantine"
    MANIFEST_FILENAME = "manifest.json"

    def __init__(
        self,
        bundles_dir: Optional[str] = None,
        quarantine_dir: Optional[str] = None,
        signature_policy: Optional[SignaturePolicy] = None,
    ):
        """
        Initialize bundle manager.

        Args:
            bundles_dir: Directory containing bundles (default: storage/models/bundles)
            quarantine_dir: Directory for quarantined bundles (default: storage/quarantine)
            signature_policy: Signature validation policy (default: strict)
        """
        self.bundles_dir = Path(bundles_dir or self.DEFAULT_BUNDLES_DIR)
        self.quarantine_dir = Path(quarantine_dir or self.DEFAULT_QUARANTINE_DIR)

        # Validators
        self.validator = get_hash_validator()
        self.signature_validator = get_signature_validator(policy=signature_policy)

        # Bundle registry
        self.bundles: Dict[str, Bundle] = {}
        self.active_bundle_id: Optional[str] = None

        # Ensure directories exist
        self.bundles_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Bundle manager initialized: {self.bundles_dir}")

    def discover_bundles(self) -> List[Bundle]:
        """
        Discover all bundles in bundles directory.

        Scans for manifest.json files and loads bundle metadata.

        Returns:
            List of discovered bundles
        """
        discovered = []

        if not self.bundles_dir.exists():
            logger.warning(f"Bundles directory not found: {self.bundles_dir}")
            return discovered

        # Find all manifest files
        manifest_files = list(self.bundles_dir.rglob(self.MANIFEST_FILENAME))

        logger.info(f"Found {len(manifest_files)} manifest files")

        for manifest_path in manifest_files:
            try:
                bundle = self._load_bundle_from_manifest(manifest_path)
                if bundle:
                    discovered.append(bundle)
                    self.bundles[bundle.id] = bundle
                    logger.info(f"Discovered bundle: {bundle.id} ({bundle.name})")

            except Exception as e:
                logger.error(f"Error loading manifest {manifest_path}: {e}")

        logger.info(f"Bundle discovery complete: {len(discovered)} bundles")
        return discovered

    def _load_bundle_from_manifest(self, manifest_path: Path) -> Optional[Bundle]:
        """
        Load bundle metadata from manifest file.

        Args:
            manifest_path: Path to manifest.json

        Returns:
            Bundle object or None if invalid
        """
        try:
            with open(manifest_path, "r") as f:
                data = json.load(f)

            # Resolve paths relative to manifest directory
            bundle_dir = manifest_path.parent

            # Get model file path from manifest
            model_filename = data.get("model_file", "model.gguf")
            file_path = bundle_dir / model_filename

            # Create Bundle object
            bundle = Bundle(
                id=data["id"],
                name=data["name"],
                version=data["version"],
                model_type=data.get("model_type", "unknown"),
                model_size=data.get("model_size", "unknown"),
                file_path=str(file_path),
                manifest_path=str(manifest_path),
                sha256_hash=data["sha256_hash"],
                sha256_manifest_hash=data.get("sha256_manifest_hash", ""),
                description=data.get("description"),
                capabilities=data.get("capabilities", []),
                requirements=data.get("requirements", {}),
                status=BundleStatus.PENDING,
            )

            return bundle

        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            logger.error(f"Invalid manifest {manifest_path}: {e}")
            return None

    def get_bundle(self, bundle_id: str) -> Optional[Bundle]:
        """
        Get bundle by ID.

        Args:
            bundle_id: Bundle identifier

        Returns:
            Bundle object or None if not found
        """
        return self.bundles.get(bundle_id)

    def list_bundles(
        self, status: Optional[BundleStatus] = None
    ) -> List[Bundle]:
        """
        List all bundles, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of bundles
        """
        bundles = list(self.bundles.values())

        if status:
            bundles = [b for b in bundles if b.status == status]

        return bundles

    def validate_bundle(
        self, bundle_id: str, force: bool = False
    ) -> ValidationResult:
        """
        Validate bundle integrity.

        Args:
            bundle_id: Bundle to validate
            force: Force revalidation even if cached

        Returns:
            ValidationResult with validation status
        """
        bundle = self.get_bundle(bundle_id)

        if not bundle:
            return ValidationResult(
                is_valid=False,
                bundle_id=bundle_id,
                hash_match=False,
                file_exists=False,
                manifest_valid=False,
                errors=[f"Bundle not found: {bundle_id}"],
                warnings=[],
            )

        # Check cache unless forced
        if not force:
            cached = self.validator.get_cached_result(bundle_id)
            if cached:
                logger.debug(f"Using cached validation for {bundle_id}")
                return cached

        # Perform hash validation
        result = self.validator.validate_bundle(bundle)

        # G1: Perform signature validation (modifies result in place)
        if result.is_valid:  # Only check signature if hash is valid
            result = self.signature_validator.validate_bundle_signature(bundle, result)

        # Update bundle status
        if result.is_valid:
            bundle.status = BundleStatus.VALIDATED
            bundle.last_validated = datetime.utcnow()
            logger.info(f"Bundle {bundle_id} validated successfully")
        else:
            # Check if quarantine is required
            should_quarantine = (
                self.signature_validator.policy.quarantine_on_failure
                and bundle.status != BundleStatus.QUARANTINED
            )

            if should_quarantine:
                # Quarantine bundle with detailed reason
                reason_parts = []
                if not result.signature_valid:
                    reason_parts.append("invalid signature")
                    # G4: Record bundle signature failure
                    try:
                        metrics = get_governance_metrics()
                        metrics.record_bundle_signature_failure()
                    except Exception as e:
                        logger.warning(f"[G4] Failed to record signature failure metric: {e}")
                if not result.key_trusted:
                    reason_parts.append("untrusted key")
                if not result.signature_present and not self.signature_validator.policy.allow_unsigned_bundles:
                    reason_parts.append("missing signature")
                if not result.hash_match:
                    reason_parts.append("hash mismatch")

                reason = "Validation failed: " + ", ".join(reason_parts)
                self.quarantine_bundle(bundle_id, reason)
            else:
                if bundle.status != BundleStatus.QUARANTINED:
                    bundle.status = BundleStatus.FAILED

            logger.error(
                f"Bundle {bundle_id} validation failed: {result.errors}"
            )

        return result

    def quarantine_bundle(self, bundle_id: str, reason: str):
        """
        Quarantine a bundle.

        Moves bundle files to quarantine directory and marks status.

        Args:
            bundle_id: Bundle to quarantine
            reason: Reason for quarantine
        """
        bundle = self.get_bundle(bundle_id)

        if not bundle:
            logger.warning(f"Cannot quarantine unknown bundle: {bundle_id}")
            return

        bundle.status = BundleStatus.QUARANTINED
        bundle.quarantine_reason = reason
        bundle.quarantine_timestamp = datetime.utcnow()

        # Unload if active
        if self.active_bundle_id == bundle_id:
            self.active_bundle_id = None
            logger.warning(f"Unloaded quarantined bundle: {bundle_id}")

        # Move bundle to quarantine directory
        try:
            import shutil

            # Create quarantine subdirectory for this bundle
            quarantine_bundle_dir = self.quarantine_dir / bundle_id
            quarantine_bundle_dir.mkdir(parents=True, exist_ok=True)

            # Move manifest file
            manifest_path = Path(bundle.manifest_path)
            if manifest_path.exists():
                dest_manifest = quarantine_bundle_dir / manifest_path.name
                shutil.copy2(manifest_path, dest_manifest)
                logger.debug(f"Copied manifest to quarantine: {dest_manifest}")

            # Move model file
            file_path = Path(bundle.file_path)
            if file_path.exists():
                dest_file = quarantine_bundle_dir / file_path.name
                shutil.copy2(file_path, dest_file)
                logger.debug(f"Copied model file to quarantine: {dest_file}")

            # Write quarantine metadata
            quarantine_meta = {
                "bundle_id": bundle_id,
                "reason": reason,
                "quarantined_at": bundle.quarantine_timestamp.isoformat(),
                "original_manifest_path": str(manifest_path),
                "original_file_path": str(file_path),
            }

            meta_file = quarantine_bundle_dir / "quarantine_metadata.json"
            with open(meta_file, "w") as f:
                json.dump(quarantine_meta, f, indent=2)

            logger.info(f"Bundle {bundle_id} files copied to quarantine: {quarantine_bundle_dir}")

        except Exception as e:
            logger.error(f"Failed to move bundle {bundle_id} to quarantine: {e}")

        # Emit audit event
        self._emit_quarantine_audit_event(bundle_id, reason)

        # G4: Record bundle quarantine metric
        try:
            metrics = get_governance_metrics()
            metrics.record_bundle_quarantine()
        except Exception as e:
            logger.warning(f"[G4] Failed to record bundle quarantine metric: {e}")

        logger.warning(f"Bundle {bundle_id} quarantined: {reason}")

    def _emit_quarantine_audit_event(self, bundle_id: str, reason: str):
        """Emit BUNDLE_QUARANTINED audit event."""
        try:
            from backend.app.modules.sovereign_mode.service import (
                get_sovereign_mode_service,
            )

            service = get_sovereign_mode_service()
            service._emit_audit_event(
                event_type=AuditEventType.BUNDLE_QUARANTINED,
                success=True,
                reason=reason,
                bundle_id=bundle_id,
            )

        except Exception as e:
            logger.error(f"Failed to emit quarantine audit event: {e}")

    def load_bundle(
        self, bundle_id: str, skip_validation: bool = False
    ) -> bool:
        """
        Load bundle for use.

        Args:
            bundle_id: Bundle to load
            skip_validation: Skip validation (unsafe!)

        Returns:
            True if loaded successfully
        """
        bundle = self.get_bundle(bundle_id)

        if not bundle:
            logger.error(f"Cannot load unknown bundle: {bundle_id}")
            return False

        # Check quarantine
        if bundle.status == BundleStatus.QUARANTINED:
            logger.error(
                f"Cannot load quarantined bundle {bundle_id}: {bundle.quarantine_reason}"
            )
            return False

        # Validate unless skipped
        if not skip_validation:
            result = self.validate_bundle(bundle_id, force=True)

            if not result.is_valid:
                logger.error(f"Bundle {bundle_id} validation failed, cannot load")
                self.quarantine_bundle(
                    bundle_id, f"Validation failed: {result.errors}"
                )
                return False

        # Unload current bundle if any
        if self.active_bundle_id:
            self.unload_bundle()

        # Mark as loaded
        bundle.status = BundleStatus.LOADED
        bundle.last_loaded = datetime.utcnow()
        bundle.load_count += 1
        self.active_bundle_id = bundle_id

        logger.info(
            f"Bundle {bundle_id} loaded successfully "
            f"(load_count={bundle.load_count})"
        )

        return True

    def unload_bundle(self):
        """Unload currently active bundle."""
        if not self.active_bundle_id:
            return

        bundle = self.get_bundle(self.active_bundle_id)

        if bundle:
            bundle.status = BundleStatus.VALIDATED
            logger.info(f"Bundle {self.active_bundle_id} unloaded")

        self.active_bundle_id = None

    def get_active_bundle(self) -> Optional[Bundle]:
        """
        Get currently active bundle.

        Returns:
            Active Bundle or None
        """
        if not self.active_bundle_id:
            return None

        return self.get_bundle(self.active_bundle_id)

    def get_statistics(self) -> dict:
        """
        Get bundle statistics.

        Returns:
            Dictionary with bundle stats
        """
        total = len(self.bundles)
        by_status = {status: 0 for status in BundleStatus}

        for bundle in self.bundles.values():
            by_status[bundle.status] += 1

        return {
            "total_bundles": total,
            "validated": by_status[BundleStatus.VALIDATED],
            "loaded": by_status[BundleStatus.LOADED],
            "quarantined": by_status[BundleStatus.QUARANTINED],
            "failed": by_status[BundleStatus.FAILED],
            "pending": by_status[BundleStatus.PENDING],
            "active_bundle_id": self.active_bundle_id,
        }

    def export_bundle_manifest(self, bundle_id: str) -> Optional[Dict]:
        """
        Export bundle manifest for distribution.

        Args:
            bundle_id: Bundle to export

        Returns:
            Manifest dictionary or None
        """
        bundle = self.get_bundle(bundle_id)

        if not bundle:
            return None

        return {
            "id": bundle.id,
            "name": bundle.name,
            "version": bundle.version,
            "model_type": bundle.model_type,
            "model_size": bundle.model_size,
            "model_file": Path(bundle.file_path).name,
            "sha256_hash": bundle.sha256_hash,
            "sha256_manifest_hash": bundle.sha256_manifest_hash,
            "description": bundle.description,
            "capabilities": bundle.capabilities,
            "requirements": bundle.requirements,
            "signed_by": bundle.signed_by,
        }

    def create_bundle_manifest(
        self,
        bundle_dir: str,
        bundle_id: str,
        name: str,
        version: str,
        model_file: str,
        model_type: str = "unknown",
        model_size: str = "unknown",
        description: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        requirements: Optional[Dict] = None,
    ) -> bool:
        """
        Create a new bundle manifest.

        Args:
            bundle_dir: Directory to create bundle in
            bundle_id: Unique bundle ID
            name: Human-readable name
            version: Semantic version
            model_file: Model filename
            model_type: Model type
            model_size: Model size
            description: Optional description
            capabilities: Optional capabilities list
            requirements: Optional requirements dict

        Returns:
            True if created successfully
        """
        try:
            bundle_path = Path(bundle_dir)
            bundle_path.mkdir(parents=True, exist_ok=True)

            model_path = bundle_path / model_file
            manifest_path = bundle_path / self.MANIFEST_FILENAME

            # Check if model file exists
            if not model_path.exists():
                logger.error(f"Model file not found: {model_path}")
                return False

            # Compute hashes
            model_hash = self.validator.compute_file_hash(str(model_path))
            if not model_hash:
                logger.error("Failed to compute model hash")
                return False

            # Create manifest
            manifest = {
                "id": bundle_id,
                "name": name,
                "version": version,
                "model_type": model_type,
                "model_size": model_size,
                "model_file": model_file,
                "sha256_hash": model_hash,
                "sha256_manifest_hash": "",  # Will update after writing
                "description": description,
                "capabilities": capabilities or [],
                "requirements": requirements or {},
                "created_at": datetime.utcnow().isoformat(),
            }

            # Write manifest
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2, sort_keys=True)

            # Compute manifest hash
            manifest_hash = self.validator.compute_file_hash(str(manifest_path))

            # Update manifest with its own hash
            manifest["sha256_manifest_hash"] = manifest_hash

            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2, sort_keys=True)

            logger.info(f"Created bundle manifest: {manifest_path}")
            return True

        except Exception as e:
            logger.error(f"Error creating bundle manifest: {e}")
            return False


# Singleton instance
_manager: Optional[BundleManager] = None


def get_bundle_manager() -> BundleManager:
    """Get singleton bundle manager instance."""
    global _manager
    if _manager is None:
        _manager = BundleManager()
    return _manager
