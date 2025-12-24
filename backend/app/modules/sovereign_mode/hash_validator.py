"""
Hash Validator

SHA256 integrity validation for offline model bundles.
Provides secure, auditable file verification.
"""

import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from backend.app.modules.sovereign_mode.schemas import (
    ValidationResult,
    Bundle,
)


class HashValidator:
    """SHA256 hash validator for bundle integrity checks."""

    BUFFER_SIZE = 65536  # 64KB chunks for large files
    VALIDATOR_VERSION = "1.0.0"

    def __init__(self):
        """Initialize hash validator."""
        self.validation_cache: Dict[str, ValidationResult] = {}

    def compute_file_hash(self, file_path: str) -> Optional[str]:
        """
        Compute SHA256 hash of a file.

        Args:
            file_path: Path to file to hash

        Returns:
            Hexadecimal SHA256 hash or None if file not found
        """
        path = Path(file_path)

        if not path.exists():
            logger.warning(f"File not found for hashing: {file_path}")
            return None

        if not path.is_file():
            logger.warning(f"Path is not a file: {file_path}")
            return None

        try:
            sha256 = hashlib.sha256()

            with open(path, "rb") as f:
                while chunk := f.read(self.BUFFER_SIZE):
                    sha256.update(chunk)

            computed_hash = sha256.hexdigest()
            logger.debug(f"Computed hash for {file_path}: {computed_hash[:16]}...")

            return computed_hash

        except Exception as e:
            logger.error(f"Error computing hash for {file_path}: {e}")
            return None

    def compute_string_hash(self, content: str) -> str:
        """
        Compute SHA256 hash of string content.

        Args:
            content: String to hash

        Returns:
            Hexadecimal SHA256 hash
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def compute_json_hash(self, data: Dict[str, Any]) -> str:
        """
        Compute SHA256 hash of JSON data.

        Args:
            data: Dictionary to hash

        Returns:
            Hexadecimal SHA256 hash
        """
        # Sort keys for deterministic hashing
        json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return self.compute_string_hash(json_str)

    def validate_file(
        self,
        file_path: str,
        expected_hash: str,
        bundle_id: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate file against expected SHA256 hash.

        Args:
            file_path: Path to file to validate
            expected_hash: Expected SHA256 hash (hexadecimal)
            bundle_id: Optional bundle ID for audit trail

        Returns:
            ValidationResult with detailed validation info
        """
        errors = []
        warnings = []

        # Check file existence
        path = Path(file_path)
        file_exists = path.exists() and path.is_file()

        if not file_exists:
            errors.append(f"File not found: {file_path}")
            return ValidationResult(
                is_valid=False,
                bundle_id=bundle_id,
                hash_match=False,
                expected_hash=expected_hash,
                actual_hash=None,
                file_exists=False,
                manifest_valid=True,
                errors=errors,
                warnings=warnings,
                validator_version=self.VALIDATOR_VERSION,
            )

        # Compute actual hash
        actual_hash = self.compute_file_hash(file_path)

        if actual_hash is None:
            errors.append(f"Failed to compute hash for: {file_path}")
            return ValidationResult(
                is_valid=False,
                bundle_id=bundle_id,
                hash_match=False,
                expected_hash=expected_hash,
                actual_hash=None,
                file_exists=True,
                manifest_valid=True,
                errors=errors,
                warnings=warnings,
                validator_version=self.VALIDATOR_VERSION,
            )

        # Compare hashes (case-insensitive)
        hash_match = actual_hash.lower() == expected_hash.lower()

        if not hash_match:
            errors.append(
                f"Hash mismatch! Expected: {expected_hash[:16]}..., "
                f"Got: {actual_hash[:16]}..."
            )
            logger.error(
                f"Hash validation failed for {file_path}: "
                f"expected={expected_hash}, actual={actual_hash}"
            )
        else:
            logger.info(f"Hash validation passed for {file_path}")

        is_valid = hash_match and file_exists

        result = ValidationResult(
            is_valid=is_valid,
            bundle_id=bundle_id,
            hash_match=hash_match,
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            file_exists=file_exists,
            manifest_valid=True,
            errors=errors,
            warnings=warnings,
            validator_version=self.VALIDATOR_VERSION,
        )

        # Cache validation result
        if bundle_id:
            self.validation_cache[bundle_id] = result

        return result

    def validate_bundle(self, bundle: Bundle) -> ValidationResult:
        """
        Validate entire bundle (model file + manifest).

        Args:
            bundle: Bundle to validate

        Returns:
            ValidationResult with combined validation
        """
        errors = []
        warnings = []

        # Validate model file
        model_result = self.validate_file(
            file_path=bundle.file_path,
            expected_hash=bundle.sha256_hash,
            bundle_id=bundle.id,
        )

        if not model_result.is_valid:
            errors.extend(model_result.errors)
            errors.append("Model file validation failed")

        # Validate manifest file
        manifest_path = Path(bundle.manifest_path)
        manifest_valid = manifest_path.exists() and manifest_path.is_file()

        if not manifest_valid:
            errors.append(f"Manifest not found: {bundle.manifest_path}")
        else:
            # Validate manifest hash
            manifest_hash = self.compute_file_hash(bundle.manifest_path)

            if manifest_hash is None:
                errors.append("Failed to compute manifest hash")
                manifest_valid = False
            elif manifest_hash.lower() != bundle.sha256_manifest_hash.lower():
                errors.append(
                    f"Manifest hash mismatch! Expected: {bundle.sha256_manifest_hash[:16]}..., "
                    f"Got: {manifest_hash[:16]}..."
                )
                manifest_valid = False
            else:
                logger.info(f"Manifest validation passed for bundle {bundle.id}")

        # Overall validation
        is_valid = model_result.is_valid and manifest_valid

        result = ValidationResult(
            is_valid=is_valid,
            bundle_id=bundle.id,
            hash_match=model_result.hash_match,
            expected_hash=bundle.sha256_hash,
            actual_hash=model_result.actual_hash,
            file_exists=model_result.file_exists,
            manifest_valid=manifest_valid,
            errors=errors,
            warnings=warnings,
            validator_version=self.VALIDATOR_VERSION,
        )

        # Cache result
        self.validation_cache[bundle.id] = result

        if is_valid:
            logger.info(f"Bundle {bundle.id} validation: PASSED")
        else:
            logger.error(
                f"Bundle {bundle.id} validation: FAILED - {len(errors)} error(s)"
            )

        return result

    def get_cached_result(self, bundle_id: str) -> Optional[ValidationResult]:
        """
        Get cached validation result.

        Args:
            bundle_id: Bundle ID

        Returns:
            Cached ValidationResult or None
        """
        return self.validation_cache.get(bundle_id)

    def clear_cache(self, bundle_id: Optional[str] = None):
        """
        Clear validation cache.

        Args:
            bundle_id: Optional specific bundle to clear, or all if None
        """
        if bundle_id:
            self.validation_cache.pop(bundle_id, None)
            logger.debug(f"Cleared validation cache for bundle {bundle_id}")
        else:
            self.validation_cache.clear()
            logger.debug("Cleared all validation cache")

    def verify_bundle_integrity_batch(
        self, bundles: list[Bundle]
    ) -> Dict[str, ValidationResult]:
        """
        Validate multiple bundles in batch.

        Args:
            bundles: List of bundles to validate

        Returns:
            Dictionary mapping bundle_id to ValidationResult
        """
        results = {}

        for bundle in bundles:
            result = self.validate_bundle(bundle)
            results[bundle.id] = result

        passed = sum(1 for r in results.values() if r.is_valid)
        failed = len(results) - passed

        logger.info(
            f"Batch validation complete: {passed} passed, {failed} failed out of {len(bundles)}"
        )

        return results


# Singleton instance
_validator: Optional[HashValidator] = None


def get_hash_validator() -> HashValidator:
    """Get singleton hash validator instance."""
    global _validator
    if _validator is None:
        _validator = HashValidator()
    return _validator
