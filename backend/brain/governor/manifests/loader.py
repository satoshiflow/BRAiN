"""
Governance Manifest Loader (Phase 2b)

Loads and validates governance manifests from YAML files.

Features:
- Load manifests from file or dict
- Pydantic validation
- Manifest versioning
- Error handling with clear messages

Author: Governor v1 System (Phase 2b)
Version: 2b.1
Created: 2026-01-02
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

import yaml
from pydantic import ValidationError

from backend.brain.governor.manifests.schema import GovernanceManifest


logger = logging.getLogger(__name__)


# ============================================================================
# Manifest Loader
# ============================================================================

class ManifestLoader:
    """
    Loader for governance manifests.

    Responsibilities:
    - Load manifests from YAML files
    - Validate manifest schema (Pydantic)
    - Cache loaded manifests
    - Provide clear error messages

    Example:
        >>> loader = ManifestLoader()
        >>> manifest = loader.load_from_file("manifests/defaults.yaml")
        >>> print(manifest.name)
        'default'
    """

    def __init__(self):
        """Initialize manifest loader."""
        self._cache: Dict[str, GovernanceManifest] = {}

    def load_from_file(
        self,
        file_path: str | Path,
        use_cache: bool = True
    ) -> GovernanceManifest:
        """
        Load manifest from YAML file.

        Args:
            file_path: Path to YAML file
            use_cache: Use cached manifest if available

        Returns:
            Validated GovernanceManifest

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is invalid
            ValidationError: If manifest schema is invalid

        Example:
            >>> manifest = loader.load_from_file("manifests/defaults.yaml")
        """
        file_path = Path(file_path)

        # Check cache
        if use_cache and str(file_path) in self._cache:
            logger.debug(f"Manifest loaded from cache: {file_path}")
            return self._cache[str(file_path)]

        # Check file exists
        if not file_path.exists():
            raise FileNotFoundError(
                f"Manifest file not found: {file_path}"
            )

        # Load YAML
        try:
            with open(file_path, "r") as f:
                manifest_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Failed to parse YAML in {file_path}: {e}"
            )

        # Validate and parse
        try:
            manifest = GovernanceManifest(**manifest_data)
        except ValidationError as e:
            raise ValidationError(
                f"Manifest validation failed for {file_path}: {e}"
            )

        # Cache and return
        self._cache[str(file_path)] = manifest
        logger.info(
            f"Manifest loaded: {manifest.name} v{manifest.policy_version} "
            f"from {file_path}"
        )

        return manifest

    def load_from_dict(
        self,
        manifest_data: Dict,
        name: Optional[str] = None
    ) -> GovernanceManifest:
        """
        Load manifest from dictionary.

        Args:
            manifest_data: Manifest dictionary
            name: Optional name for caching

        Returns:
            Validated GovernanceManifest

        Raises:
            ValidationError: If manifest schema is invalid

        Example:
            >>> manifest_data = {
            ...     "manifest_version": 1,
            ...     "policy_version": "2b.1",
            ...     "name": "test_manifest",
            ...     ...
            ... }
            >>> manifest = loader.load_from_dict(manifest_data)
        """
        # Validate and parse
        try:
            manifest = GovernanceManifest(**manifest_data)
        except ValidationError as e:
            raise ValidationError(
                f"Manifest validation failed: {e}"
            )

        # Cache if name provided
        if name:
            self._cache[name] = manifest

        logger.info(
            f"Manifest loaded from dict: {manifest.name} v{manifest.policy_version}"
        )

        return manifest

    def get_default_manifest(self) -> GovernanceManifest:
        """
        Get default manifest.

        Loads from manifests/defaults.yaml or returns hard-coded default.

        Returns:
            Default GovernanceManifest

        Example:
            >>> manifest = loader.get_default_manifest()
        """
        # Try to load from file
        default_path = Path(__file__).parent / "defaults.yaml"

        if default_path.exists():
            try:
                return self.load_from_file(default_path)
            except Exception as e:
                logger.warning(
                    f"Failed to load default manifest from {default_path}: {e}"
                )

        # Fallback: return hard-coded default
        logger.warning("Using hard-coded default manifest")
        return self._get_hardcoded_default()

    def _get_hardcoded_default(self) -> GovernanceManifest:
        """
        Get hard-coded default manifest (fallback).

        Returns:
            Default GovernanceManifest
        """
        from backend.brain.governor.manifests.schema import (
            AppliesToSpec,
            ReductionSections,
            ReductionSpec,
            RiskOverride,
            LockSpec,
        )

        return GovernanceManifest(
            manifest_version=1,
            policy_version="2b.1",
            name="default",
            description="Default governance manifest (hard-coded fallback)",
            applies_to=AppliesToSpec(),  # Applies to all
            reductions=ReductionSections(
                on_customization=ReductionSpec(
                    max_llm_calls_per_day="-30%",
                    parallelism="-50%"
                )
            ),
            risk_overrides=RiskOverride(
                if_customizations="MEDIUM"
            ),
            locks=LockSpec()
        )

    def clear_cache(self) -> None:
        """
        Clear manifest cache.

        Example:
            >>> loader.clear_cache()
        """
        self._cache.clear()
        logger.info("Manifest cache cleared")

    def get_cached_manifests(self) -> Dict[str, GovernanceManifest]:
        """
        Get all cached manifests.

        Returns:
            Dictionary of cached manifests

        Example:
            >>> cached = loader.get_cached_manifests()
            >>> print(list(cached.keys()))
            ['manifests/defaults.yaml', 'manifests/strict.yaml']
        """
        return self._cache.copy()


# ============================================================================
# Singleton Instance
# ============================================================================

_manifest_loader: Optional[ManifestLoader] = None


def get_manifest_loader() -> ManifestLoader:
    """
    Get singleton manifest loader instance.

    Returns:
        ManifestLoader singleton

    Example:
        >>> loader = get_manifest_loader()
        >>> manifest = loader.get_default_manifest()
    """
    global _manifest_loader
    if _manifest_loader is None:
        _manifest_loader = ManifestLoader()
    return _manifest_loader
