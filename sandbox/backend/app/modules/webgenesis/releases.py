"""
WebGenesis Module - Release Management (Sprint II)

Handles release snapshots for rollback capability.

Features:
- Release creation after successful deployment
- Release metadata tracking
- Retention policy enforcement
- Release listing and retrieval

Security:
- All paths validated via safe_path_join()
- Release IDs validated for safety
- Audit trail integration
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from loguru import logger

from .schemas import ReleaseMetadata
from .service import STORAGE_BASE, safe_path_join, validate_site_id


# ============================================================================
# Constants
# ============================================================================

# Default retention: keep 5 most recent releases
DEFAULT_RELEASE_KEEP = int(os.getenv("BRAIN_WEBGENESIS_RELEASE_KEEP", "5"))

# Release ID pattern validation
import re
RELEASE_ID_PATTERN = re.compile(r"^rel_\d{10}_[a-f0-9]{8}$")


# ============================================================================
# Helper Functions
# ============================================================================


def validate_release_id(release_id: str) -> bool:
    """
    Validate release ID format.

    Expected format: rel_{timestamp}_{short_hash}
    Example: rel_1703001234_a3f5c8e9

    Args:
        release_id: Release identifier to validate

    Returns:
        True if valid, False otherwise
    """
    return bool(RELEASE_ID_PATTERN.match(release_id))


def generate_release_id(artifact_hash: str) -> str:
    """
    Generate unique release ID.

    Format: rel_{timestamp}_{artifact_hash_short}

    Args:
        artifact_hash: Build artifact hash (SHA-256)

    Returns:
        Release ID string
    """
    timestamp = int(time.time())
    hash_short = artifact_hash[:8]  # First 8 characters
    return f"rel_{timestamp}_{hash_short}"


# ============================================================================
# Release Management
# ============================================================================


class ReleaseManager:
    """
    Manages release snapshots for WebGenesis sites (Sprint II).

    Features:
    - Create release snapshots after successful deployment
    - List releases for a site
    - Get release metadata
    - Prune old releases (retention policy)
    """

    def __init__(self, storage_base: Path = STORAGE_BASE):
        """
        Initialize release manager.

        Args:
            storage_base: Base storage path for WebGenesis sites
        """
        self.storage_base = Path(storage_base)
        logger.info(f"ReleaseManager initialized (storage: {self.storage_base})")

    # ========================================================================
    # Release Creation
    # ========================================================================

    async def create_release(
        self,
        site_id: str,
        artifact_hash: str,
        deployed_url: Optional[str] = None,
        health_status: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ReleaseMetadata:
        """
        Create a new release snapshot.

        Creates:
        - releases/{release_id}/ directory
        - release.json (metadata)
        - docker-compose.yml (frozen copy)
        - artifact_hash.txt (reference)

        Args:
            site_id: Site identifier
            artifact_hash: Build artifact SHA-256 hash
            deployed_url: Deployment URL
            health_status: Health check status after deployment
            metadata: Additional release metadata

        Returns:
            ReleaseMetadata for created release

        Raises:
            ValueError: If site_id invalid or site doesn't exist
            FileNotFoundError: If docker-compose.yml doesn't exist
        """
        # Validate site ID
        if not validate_site_id(site_id):
            raise ValueError(f"Invalid site ID: {site_id}")

        # Site directory
        site_dir = safe_path_join(self.storage_base, site_id)
        if not site_dir.exists():
            raise FileNotFoundError(f"Site not found: {site_id}")

        # Generate release ID
        release_id = generate_release_id(artifact_hash)

        # Create releases directory if needed
        releases_dir = safe_path_join(site_dir, "releases")
        releases_dir.mkdir(parents=True, exist_ok=True)

        # Create release directory
        release_dir = safe_path_join(releases_dir, release_id)
        if release_dir.exists():
            logger.warning(f"Release already exists: {release_id}, skipping")
            return await self.get_release(site_id, release_id)

        release_dir.mkdir(parents=True, exist_ok=True)

        # Copy docker-compose.yml
        compose_src = safe_path_join(site_dir, "docker-compose.yml")
        if not compose_src.exists():
            raise FileNotFoundError(
                f"docker-compose.yml not found for site {site_id}"
            )

        compose_dst = safe_path_join(release_dir, "docker-compose.yml")
        shutil.copy2(compose_src, compose_dst)

        # Write artifact_hash.txt
        artifact_hash_file = safe_path_join(release_dir, "artifact_hash.txt")
        artifact_hash_file.write_text(artifact_hash)

        # Create release metadata
        release_meta = ReleaseMetadata(
            release_id=release_id,
            site_id=site_id,
            artifact_hash=artifact_hash,
            created_at=datetime.utcnow(),
            deployed_url=deployed_url,
            docker_compose_path=str(compose_dst.relative_to(self.storage_base)),
            health_status=health_status,
            metadata=metadata or {},
        )

        # Write release.json
        release_json_path = safe_path_join(release_dir, "release.json")
        release_json_path.write_text(
            json.dumps(release_meta.dict(), indent=2, default=str)
        )

        logger.info(
            f"Created release {release_id} for site {site_id} "
            f"(artifact_hash={artifact_hash[:16]}...)"
        )

        return release_meta

    # ========================================================================
    # Release Retrieval
    # ========================================================================

    async def list_releases(
        self,
        site_id: str,
        sort_desc: bool = True,
    ) -> List[ReleaseMetadata]:
        """
        List all releases for a site.

        Args:
            site_id: Site identifier
            sort_desc: Sort descending (newest first) if True

        Returns:
            List of ReleaseMetadata, sorted by created_at

        Raises:
            ValueError: If site_id invalid
            FileNotFoundError: If site doesn't exist
        """
        # Validate site ID
        if not validate_site_id(site_id):
            raise ValueError(f"Invalid site ID: {site_id}")

        # Site directory
        site_dir = safe_path_join(self.storage_base, site_id)
        if not site_dir.exists():
            raise FileNotFoundError(f"Site not found: {site_id}")

        # Releases directory
        releases_dir = safe_path_join(site_dir, "releases")
        if not releases_dir.exists():
            return []  # No releases yet

        # Collect all releases
        releases = []
        for release_dir in releases_dir.iterdir():
            if not release_dir.is_dir():
                continue

            # Validate release ID
            if not validate_release_id(release_dir.name):
                logger.warning(f"Invalid release directory: {release_dir.name}")
                continue

            # Load release metadata
            release_json_path = safe_path_join(release_dir, "release.json")
            if not release_json_path.exists():
                logger.warning(f"Missing release.json for {release_dir.name}")
                continue

            try:
                with open(release_json_path) as f:
                    release_data = json.load(f)
                release_meta = ReleaseMetadata(**release_data)
                releases.append(release_meta)
            except Exception as e:
                logger.error(f"Failed to load release {release_dir.name}: {e}")
                continue

        # Sort by created_at (newest first by default)
        releases.sort(key=lambda r: r.created_at, reverse=sort_desc)

        return releases

    async def get_release(
        self,
        site_id: str,
        release_id: str,
    ) -> Optional[ReleaseMetadata]:
        """
        Get specific release metadata.

        Args:
            site_id: Site identifier
            release_id: Release identifier

        Returns:
            ReleaseMetadata if found, None otherwise

        Raises:
            ValueError: If site_id or release_id invalid
        """
        # Validate IDs
        if not validate_site_id(site_id):
            raise ValueError(f"Invalid site ID: {site_id}")

        if not validate_release_id(release_id):
            raise ValueError(f"Invalid release ID: {release_id}")

        # Release directory
        site_dir = safe_path_join(self.storage_base, site_id)
        releases_dir = safe_path_join(site_dir, "releases")
        release_dir = safe_path_join(releases_dir, release_id)

        if not release_dir.exists():
            return None

        # Load release metadata
        release_json_path = safe_path_join(release_dir, "release.json")
        if not release_json_path.exists():
            logger.warning(f"Missing release.json for {release_id}")
            return None

        try:
            with open(release_json_path) as f:
                release_data = json.load(f)
            return ReleaseMetadata(**release_data)
        except Exception as e:
            logger.error(f"Failed to load release {release_id}: {e}")
            return None

    # ========================================================================
    # Release Retention
    # ========================================================================

    async def prune_old_releases(
        self,
        site_id: str,
        keep: int = DEFAULT_RELEASE_KEEP,
    ) -> int:
        """
        Prune old releases, keeping only N most recent.

        Retention policy:
        - Keep N newest releases (sorted by created_at)
        - Delete older releases
        - Log audit events for deletions

        Args:
            site_id: Site identifier
            keep: Number of releases to keep (default from ENV)

        Returns:
            Number of releases deleted

        Raises:
            ValueError: If site_id invalid or keep < 0
        """
        # Validate inputs
        if not validate_site_id(site_id):
            raise ValueError(f"Invalid site ID: {site_id}")

        if keep < 0:
            raise ValueError(f"Invalid keep value: {keep} (must be >= 0)")

        # List all releases (newest first)
        releases = await self.list_releases(site_id, sort_desc=True)

        if len(releases) <= keep:
            logger.debug(
                f"No pruning needed for {site_id}: {len(releases)} <= {keep}"
            )
            return 0

        # Releases to delete (oldest)
        to_delete = releases[keep:]

        # Delete old releases
        deleted_count = 0
        for release in to_delete:
            try:
                # Delete release directory
                site_dir = safe_path_join(self.storage_base, site_id)
                releases_dir = safe_path_join(site_dir, "releases")
                release_dir = safe_path_join(releases_dir, release.release_id)

                if release_dir.exists():
                    shutil.rmtree(release_dir)
                    deleted_count += 1

                    logger.info(
                        f"Pruned old release {release.release_id} for site {site_id}"
                    )

                    # TODO: Audit event
                    # await audit_manager.log_event(
                    #     event_type="webgenesis.release_pruned",
                    #     action="prune_release",
                    #     status="success",
                    #     details={
                    #         "site_id": site_id,
                    #         "release_id": release.release_id,
                    #         "artifact_hash": release.artifact_hash,
                    #     }
                    # )

            except Exception as e:
                logger.error(
                    f"Failed to prune release {release.release_id}: {e}"
                )
                # Continue with other releases

        logger.info(
            f"Pruned {deleted_count} old releases for site {site_id} "
            f"(kept {keep} newest)"
        )

        return deleted_count

    async def get_previous_release(
        self,
        site_id: str,
        current_release_id: Optional[str] = None,
    ) -> Optional[ReleaseMetadata]:
        """
        Get previous release for rollback.

        If current_release_id is provided, returns the release immediately
        before it. Otherwise, returns the 2nd newest release.

        Args:
            site_id: Site identifier
            current_release_id: Current release ID (optional)

        Returns:
            Previous ReleaseMetadata if found, None otherwise

        Raises:
            ValueError: If site_id invalid
        """
        # List all releases (newest first)
        releases = await self.list_releases(site_id, sort_desc=True)

        if len(releases) == 0:
            return None

        # If no current release specified, return 2nd newest
        if current_release_id is None:
            if len(releases) < 2:
                return None
            return releases[1]

        # Find current release and return previous
        for i, release in enumerate(releases):
            if release.release_id == current_release_id:
                if i + 1 < len(releases):
                    return releases[i + 1]
                else:
                    return None  # No previous release

        # Current release not found
        logger.warning(
            f"Current release {current_release_id} not found for site {site_id}"
        )
        return None


# ============================================================================
# Singleton
# ============================================================================

_release_manager: Optional[ReleaseManager] = None


def get_release_manager() -> ReleaseManager:
    """Get singleton ReleaseManager instance."""
    global _release_manager
    if _release_manager is None:
        _release_manager = ReleaseManager()
    return _release_manager
