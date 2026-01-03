"""
WebGenesis Module - Rollback Service (Sprint II)

Rollback to previous releases.

Features:
- Rollback to specific or previous release
- Health check after rollback
- Fail-safe error handling
- Audit trail integration

Security:
- File locking for rollback operations
- Path safety validation
- Graceful degradation on errors

Fail-Safe Policy:
- Rollback errors logged as CRITICAL
- Errors do NOT throw exceptions (graceful)
- Site may be in degraded state (manual intervention needed)
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from loguru import logger

from .schemas import (
    ReleaseMetadata,
    RollbackResponse,
    SiteLifecycleStatus,
    HealthStatus,
)
from .service import STORAGE_BASE, safe_path_join, validate_site_id
from .releases import get_release_manager
from .health import get_health_service
from .ops_service import site_lock


# ============================================================================
# Rollback Service
# ============================================================================


class RollbackService:
    """
    Rollback service for WebGenesis sites (Sprint II).

    Features:
    - Rollback to specific release
    - Rollback to previous release (auto-select)
    - Health check after rollback
    - Fail-safe error handling
    """

    def __init__(self, storage_base: Path = STORAGE_BASE):
        """
        Initialize rollback service.

        Args:
            storage_base: Base storage path for WebGenesis sites
        """
        self.storage_base = Path(storage_base)
        self.release_manager = get_release_manager()
        self.health_service = get_health_service()
        logger.info(f"RollbackService initialized (storage: {self.storage_base})")

    async def rollback_to_release(
        self,
        site_id: str,
        release_id: Optional[str] = None,
        current_release_id: Optional[str] = None,
    ) -> RollbackResponse:
        """
        Rollback site to specific or previous release.

        If release_id is None, automatically selects previous release
        (the release immediately before current_release_id, or 2nd newest).

        Workflow:
        1. Select target release
        2. Validate release exists
        3. Stop current container (docker-compose down)
        4. Copy docker-compose.yml from release to root
        5. Start with old config (docker-compose up -d)
        6. Health check
        7. Update manifest (if available)

        Fail-Safe:
        - Errors logged as CRITICAL
        - No exceptions thrown (graceful degradation)
        - Returns RollbackResponse with success=False and error details

        Args:
            site_id: Site identifier
            release_id: Target release ID (if None: use previous)
            current_release_id: Current release ID (for finding previous)

        Returns:
            RollbackResponse with rollback result
        """
        # Validate site ID
        if not validate_site_id(site_id):
            return RollbackResponse(
                success=False,
                site_id=site_id,
                from_release=current_release_id,
                to_release="",
                lifecycle_status=SiteLifecycleStatus.UNKNOWN,
                health_status=HealthStatus.UNKNOWN,
                message="Invalid site ID",
                warnings=["Rollback aborted: invalid site ID"],
            )

        # Acquire lock
        try:
            with site_lock(site_id, self.storage_base):
                return await self._perform_rollback(
                    site_id, release_id, current_release_id
                )

        except Exception as e:
            logger.critical(f"CRITICAL: Rollback lock acquisition failed for {site_id}: {e}")
            return RollbackResponse(
                success=False,
                site_id=site_id,
                from_release=current_release_id,
                to_release=release_id or "previous",
                lifecycle_status=SiteLifecycleStatus.UNKNOWN,
                health_status=HealthStatus.UNKNOWN,
                message=f"Rollback failed: {str(e)}",
                warnings=[f"CRITICAL: Lock acquisition failed - {str(e)}"],
            )

    async def _perform_rollback(
        self,
        site_id: str,
        release_id: Optional[str],
        current_release_id: Optional[str],
    ) -> RollbackResponse:
        """
        Internal rollback implementation (called with lock held).

        Args:
            site_id: Site identifier
            release_id: Target release ID (if None: use previous)
            current_release_id: Current release ID

        Returns:
            RollbackResponse with rollback result
        """
        warnings: List[str] = []

        # Step 1: Select target release
        logger.info(
            f"Rollback started for {site_id}: "
            f"target={release_id or 'previous'}, current={current_release_id}"
        )

        if release_id is None:
            # Auto-select previous release
            try:
                previous_release = await self.release_manager.get_previous_release(
                    site_id, current_release_id
                )

                if previous_release is None:
                    logger.error(f"No previous release found for {site_id}")
                    return RollbackResponse(
                        success=False,
                        site_id=site_id,
                        from_release=current_release_id,
                        to_release="",
                        lifecycle_status=SiteLifecycleStatus.UNKNOWN,
                        health_status=HealthStatus.UNKNOWN,
                        message="No previous release available for rollback",
                        warnings=["No previous release found"],
                    )

                target_release = previous_release
                logger.info(f"Auto-selected previous release: {target_release.release_id}")

            except Exception as e:
                logger.critical(f"CRITICAL: Failed to find previous release for {site_id}: {e}")
                return RollbackResponse(
                    success=False,
                    site_id=site_id,
                    from_release=current_release_id,
                    to_release="",
                    lifecycle_status=SiteLifecycleStatus.UNKNOWN,
                    health_status=HealthStatus.UNKNOWN,
                    message=f"Failed to find previous release: {str(e)}",
                    warnings=[f"CRITICAL: Previous release selection failed - {str(e)}"],
                )

        else:
            # Use specified release
            try:
                target_release = await self.release_manager.get_release(
                    site_id, release_id
                )

                if target_release is None:
                    logger.error(f"Release not found: {release_id}")
                    return RollbackResponse(
                        success=False,
                        site_id=site_id,
                        from_release=current_release_id,
                        to_release=release_id,
                        lifecycle_status=SiteLifecycleStatus.UNKNOWN,
                        health_status=HealthStatus.UNKNOWN,
                        message=f"Release not found: {release_id}",
                        warnings=[f"Target release {release_id} does not exist"],
                    )

                logger.info(f"Using specified release: {target_release.release_id}")

            except Exception as e:
                logger.critical(f"CRITICAL: Failed to get release {release_id} for {site_id}: {e}")
                return RollbackResponse(
                    success=False,
                    site_id=site_id,
                    from_release=current_release_id,
                    to_release=release_id,
                    lifecycle_status=SiteLifecycleStatus.UNKNOWN,
                    health_status=HealthStatus.UNKNOWN,
                    message=f"Failed to get release: {str(e)}",
                    warnings=[f"CRITICAL: Release retrieval failed - {str(e)}"],
                )

        # Step 2: Validate release has docker-compose.yml
        site_dir = safe_path_join(self.storage_base, site_id)
        releases_dir = safe_path_join(site_dir, "releases")
        release_dir = safe_path_join(releases_dir, target_release.release_id)
        release_compose = safe_path_join(release_dir, "docker-compose.yml")

        if not release_compose.exists():
            logger.error(f"docker-compose.yml not found in release {target_release.release_id}")
            return RollbackResponse(
                success=False,
                site_id=site_id,
                from_release=current_release_id,
                to_release=target_release.release_id,
                lifecycle_status=SiteLifecycleStatus.UNKNOWN,
                health_status=HealthStatus.UNKNOWN,
                message=f"Release {target_release.release_id} missing docker-compose.yml",
                warnings=["Release is corrupt (missing docker-compose.yml)"],
            )

        # Step 3: Stop current container
        logger.info(f"Stopping current container for {site_id}")
        try:
            result = subprocess.run(
                ["docker-compose", "down"],
                cwd=str(site_dir),
                capture_output=True,
                timeout=60,
                check=True,
            )
            logger.info(f"Current container stopped for {site_id}")

        except subprocess.CalledProcessError as e:
            logger.warning(
                f"docker-compose down failed for {site_id}: {e.stderr.decode() if e.stderr else str(e)}"
            )
            warnings.append(f"Failed to stop current container: {str(e)}")
            # Continue anyway (container might not be running)

        except Exception as e:
            logger.critical(f"CRITICAL: Failed to stop container for {site_id}: {e}")
            warnings.append(f"CRITICAL: Container stop failed - {str(e)}")
            # Continue anyway

        # Step 4: Copy docker-compose.yml from release to root
        logger.info(f"Copying docker-compose.yml from release {target_release.release_id}")
        try:
            root_compose = safe_path_join(site_dir, "docker-compose.yml")
            shutil.copy2(release_compose, root_compose)
            logger.info(f"docker-compose.yml copied from release {target_release.release_id}")

        except Exception as e:
            logger.critical(f"CRITICAL: Failed to copy docker-compose.yml for {site_id}: {e}")
            return RollbackResponse(
                success=False,
                site_id=site_id,
                from_release=current_release_id,
                to_release=target_release.release_id,
                lifecycle_status=SiteLifecycleStatus.UNKNOWN,
                health_status=HealthStatus.UNKNOWN,
                message=f"Failed to copy docker-compose.yml: {str(e)}",
                warnings=[f"CRITICAL: File copy failed - {str(e)}"] + warnings,
            )

        # Step 5: Start with old config
        logger.info(f"Starting container with release {target_release.release_id} config")
        try:
            result = subprocess.run(
                ["docker-compose", "up", "-d"],
                cwd=str(site_dir),
                capture_output=True,
                timeout=60,
                check=True,
            )
            logger.info(f"Container started with release {target_release.release_id} config")

        except subprocess.CalledProcessError as e:
            logger.critical(
                f"CRITICAL: docker-compose up failed for {site_id}: {e.stderr.decode() if e.stderr else str(e)}"
            )
            return RollbackResponse(
                success=False,
                site_id=site_id,
                from_release=current_release_id,
                to_release=target_release.release_id,
                lifecycle_status=SiteLifecycleStatus.EXITED,
                health_status=HealthStatus.UNHEALTHY,
                message=f"Failed to start container with old config: {str(e)}",
                warnings=[f"CRITICAL: docker-compose up failed - {str(e)}"] + warnings,
            )

        except Exception as e:
            logger.critical(f"CRITICAL: Failed to start container for {site_id}: {e}")
            return RollbackResponse(
                success=False,
                site_id=site_id,
                from_release=current_release_id,
                to_release=target_release.release_id,
                lifecycle_status=SiteLifecycleStatus.UNKNOWN,
                health_status=HealthStatus.UNKNOWN,
                message=f"Failed to start container: {str(e)}",
                warnings=[f"CRITICAL: Container start failed - {str(e)}"] + warnings,
            )

        # Step 6: Health check
        logger.info(f"Running health check after rollback for {site_id}")
        health_status = HealthStatus.UNKNOWN
        if target_release.deployed_url:
            try:
                success, health_status, error_msg = await self.health_service.check_site_health(
                    target_release.deployed_url
                )

                if success:
                    logger.info(f"Health check PASSED after rollback for {site_id}")
                else:
                    logger.warning(
                        f"Health check FAILED after rollback for {site_id}: {error_msg}"
                    )
                    warnings.append(f"Health check failed after rollback: {error_msg}")

            except Exception as e:
                logger.error(f"Health check error after rollback for {site_id}: {e}")
                warnings.append(f"Health check error: {str(e)}")
                health_status = HealthStatus.UNKNOWN

        else:
            logger.warning(f"No deployed_url in release {target_release.release_id}, skipping health check")
            warnings.append("No deployed URL available for health check")

        # Step 7: Update manifest (best-effort)
        try:
            manifest_file = safe_path_join(site_dir, "manifest.json")
            if manifest_file.exists():
                import json

                with open(manifest_file) as f:
                    manifest_data = json.load(f)

                manifest_data["current_release_id"] = target_release.release_id
                manifest_data["updated_at"] = datetime.utcnow().isoformat()
                manifest_data["last_health_status"] = health_status.value

                with open(manifest_file, "w") as f:
                    json.dump(manifest_data, f, indent=2)

                logger.info(f"Manifest updated after rollback for {site_id}")

        except Exception as e:
            logger.warning(f"Failed to update manifest after rollback for {site_id}: {e}")
            warnings.append(f"Failed to update manifest: {str(e)}")

        # Success!
        logger.info(
            f"Rollback COMPLETED for {site_id}: "
            f"{current_release_id or 'unknown'} → {target_release.release_id}"
        )

        return RollbackResponse(
            success=True,
            site_id=site_id,
            from_release=current_release_id,
            to_release=target_release.release_id,
            lifecycle_status=SiteLifecycleStatus.RUNNING,
            health_status=health_status,
            message=f"Rollback completed to release {target_release.release_id}",
            warnings=warnings,
        )


# ============================================================================
# Singleton
# ============================================================================

_rollback_service: Optional[RollbackService] = None


def get_rollback_service() -> RollbackService:
    """Get singleton RollbackService instance."""
    global _rollback_service
    if _rollback_service is None:
        _rollback_service = RollbackService()
    return _rollback_service
