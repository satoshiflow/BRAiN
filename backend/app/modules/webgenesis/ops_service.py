"""
WebGenesis Module - Operational Service (Sprint II)

Handles container lifecycle operations with file locking.

Features:
- start/stop/restart/remove operations
- Container status retrieval
- File locking for operation safety
- Docker Compose CLI integration

Security:
- File locks prevent concurrent operations
- All paths validated via safe_path_join()
- Subprocess arg arrays (no shell=True)
- Site ID validation

Operations:
- start_site() - Start stopped container
- stop_site() - Stop running container
- restart_site() - Restart container
- remove_site() - Safe remove (with data preservation option)
- get_site_status() - Extended status with container state
"""

from __future__ import annotations

import fcntl
import json
import subprocess
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from loguru import logger

from .schemas import (
    SiteLifecycleStatus,
    HealthStatus,
    SiteOperationalStatus,
    SiteStatus,
    SiteManifest,
)
from .service import STORAGE_BASE, safe_path_join, validate_site_id


# ============================================================================
# File Locking Context Manager
# ============================================================================


@contextmanager
def site_lock(site_id: str, storage_base: Path = STORAGE_BASE):
    """
    File lock context manager for site operations.

    Prevents concurrent operations on the same site.

    Args:
        site_id: Site identifier
        storage_base: Base storage path

    Yields:
        None (lock acquired)

    Raises:
        ValueError: If site_id invalid or site doesn't exist
    """
    # Validate site ID
    if not validate_site_id(site_id):
        raise ValueError(f"Invalid site ID: {site_id}")

    # Site directory
    site_dir = safe_path_join(Path(storage_base), site_id)
    if not site_dir.exists():
        raise FileNotFoundError(f"Site not found: {site_id}")

    # Lock file
    lock_file = safe_path_join(site_dir, ".lock")

    # Acquire exclusive lock
    with open(lock_file, "w") as f:
        try:
            # Exclusive lock (blocks until acquired)
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            logger.debug(f"Acquired lock for site {site_id}")

            yield

        finally:
            # Release lock
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            logger.debug(f"Released lock for site {site_id}")


# ============================================================================
# Operational Service
# ============================================================================


class WebGenesisOpsService:
    """
    Operational service for WebGenesis site lifecycle management (Sprint II).

    Features:
    - Start/stop/restart/remove operations
    - Container status queries
    - File locking for operation safety
    - Docker Compose integration
    """

    def __init__(self, storage_base: Path = STORAGE_BASE):
        """
        Initialize operational service.

        Args:
            storage_base: Base storage path for WebGenesis sites
        """
        self.storage_base = Path(storage_base)
        logger.info(f"WebGenesisOpsService initialized (storage: {self.storage_base})")

    # ========================================================================
    # Lifecycle Operations
    # ========================================================================

    async def start_site(self, site_id: str) -> Dict[str, Any]:
        """
        Start a stopped site.

        Args:
            site_id: Site identifier

        Returns:
            Operation result with lifecycle status

        Raises:
            ValueError: If site_id invalid
            FileNotFoundError: If site doesn't exist
            subprocess.CalledProcessError: If docker-compose fails
        """
        # Validate site ID
        if not validate_site_id(site_id):
            raise ValueError(f"Invalid site ID: {site_id}")

        # Acquire lock
        with site_lock(site_id, self.storage_base):
            site_dir = safe_path_join(self.storage_base, site_id)

            # Check if docker-compose.yml exists
            compose_file = safe_path_join(site_dir, "docker-compose.yml")
            if not compose_file.exists():
                raise FileNotFoundError(
                    f"docker-compose.yml not found for site {site_id}"
                )

            # Run docker-compose start
            try:
                result = subprocess.run(
                    ["docker-compose", "start"],
                    cwd=str(site_dir),
                    capture_output=True,
                    timeout=60,
                    check=True,
                )

                logger.info(f"Started site {site_id}")

                # Get new status
                status = await self.get_site_status(site_id)

                return {
                    "success": True,
                    "site_id": site_id,
                    "operation": "start",
                    "lifecycle_status": status.lifecycle_status,
                    "message": "Site started successfully",
                }

            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Failed to start site {site_id}: {e.stderr.decode() if e.stderr else str(e)}"
                )
                raise

    async def stop_site(self, site_id: str) -> Dict[str, Any]:
        """
        Stop a running site.

        Args:
            site_id: Site identifier

        Returns:
            Operation result with lifecycle status

        Raises:
            ValueError: If site_id invalid
            FileNotFoundError: If site doesn't exist
            subprocess.CalledProcessError: If docker-compose fails
        """
        # Validate site ID
        if not validate_site_id(site_id):
            raise ValueError(f"Invalid site ID: {site_id}")

        # Acquire lock
        with site_lock(site_id, self.storage_base):
            site_dir = safe_path_join(self.storage_base, site_id)

            # Check if docker-compose.yml exists
            compose_file = safe_path_join(site_dir, "docker-compose.yml")
            if not compose_file.exists():
                raise FileNotFoundError(
                    f"docker-compose.yml not found for site {site_id}"
                )

            # Run docker-compose stop
            try:
                result = subprocess.run(
                    ["docker-compose", "stop"],
                    cwd=str(site_dir),
                    capture_output=True,
                    timeout=60,
                    check=True,
                )

                logger.info(f"Stopped site {site_id}")

                # Get new status
                status = await self.get_site_status(site_id)

                return {
                    "success": True,
                    "site_id": site_id,
                    "operation": "stop",
                    "lifecycle_status": status.lifecycle_status,
                    "message": "Site stopped successfully",
                }

            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Failed to stop site {site_id}: {e.stderr.decode() if e.stderr else str(e)}"
                )
                raise

    async def restart_site(self, site_id: str) -> Dict[str, Any]:
        """
        Restart a site.

        Args:
            site_id: Site identifier

        Returns:
            Operation result with lifecycle status

        Raises:
            ValueError: If site_id invalid
            FileNotFoundError: If site doesn't exist
            subprocess.CalledProcessError: If docker-compose fails
        """
        # Validate site ID
        if not validate_site_id(site_id):
            raise ValueError(f"Invalid site ID: {site_id}")

        # Acquire lock
        with site_lock(site_id, self.storage_base):
            site_dir = safe_path_join(self.storage_base, site_id)

            # Check if docker-compose.yml exists
            compose_file = safe_path_join(site_dir, "docker-compose.yml")
            if not compose_file.exists():
                raise FileNotFoundError(
                    f"docker-compose.yml not found for site {site_id}"
                )

            # Run docker-compose restart
            try:
                result = subprocess.run(
                    ["docker-compose", "restart"],
                    cwd=str(site_dir),
                    capture_output=True,
                    timeout=60,
                    check=True,
                )

                logger.info(f"Restarted site {site_id}")

                # Get new status
                status = await self.get_site_status(site_id)

                return {
                    "success": True,
                    "site_id": site_id,
                    "operation": "restart",
                    "lifecycle_status": status.lifecycle_status,
                    "message": "Site restarted successfully",
                }

            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Failed to restart site {site_id}: {e.stderr.decode() if e.stderr else str(e)}"
                )
                raise

    async def remove_site(
        self,
        site_id: str,
        keep_data: bool = True,
    ) -> Dict[str, Any]:
        """
        Remove a site (stop container and optionally delete data).

        Args:
            site_id: Site identifier
            keep_data: If True, keep site data (source/build/releases)

        Returns:
            Operation result with data_removed flag

        Raises:
            ValueError: If site_id invalid
            FileNotFoundError: If site doesn't exist
            subprocess.CalledProcessError: If docker-compose fails
        """
        # Validate site ID
        if not validate_site_id(site_id):
            raise ValueError(f"Invalid site ID: {site_id}")

        # Acquire lock
        with site_lock(site_id, self.storage_base):
            site_dir = safe_path_join(self.storage_base, site_id)

            # Check if docker-compose.yml exists
            compose_file = safe_path_join(site_dir, "docker-compose.yml")
            if not compose_file.exists():
                logger.warning(
                    f"docker-compose.yml not found for site {site_id}, skipping container removal"
                )
            else:
                # Run docker-compose down (removes containers)
                try:
                    result = subprocess.run(
                        ["docker-compose", "down"],
                        cwd=str(site_dir),
                        capture_output=True,
                        timeout=60,
                        check=True,
                    )

                    logger.info(f"Removed container for site {site_id}")

                except subprocess.CalledProcessError as e:
                    logger.error(
                        f"Failed to remove container for site {site_id}: {e.stderr.decode() if e.stderr else str(e)}"
                    )
                    raise

            # Delete data if requested
            data_removed = False
            if not keep_data:
                try:
                    import shutil

                    shutil.rmtree(site_dir)
                    data_removed = True
                    logger.info(f"Deleted all data for site {site_id}")

                except Exception as e:
                    logger.error(f"Failed to delete data for site {site_id}: {e}")
                    raise

            return {
                "success": True,
                "site_id": site_id,
                "data_removed": data_removed,
                "message": (
                    f"Site removed, data {'deleted' if data_removed else 'preserved'}"
                ),
            }

    # ========================================================================
    # Status Retrieval
    # ========================================================================

    async def get_site_status(self, site_id: str) -> SiteOperationalStatus:
        """
        Get extended site status with container lifecycle and health.

        Args:
            site_id: Site identifier

        Returns:
            SiteOperationalStatus with complete status information

        Raises:
            ValueError: If site_id invalid
            FileNotFoundError: If site doesn't exist
        """
        # Validate site ID
        if not validate_site_id(site_id):
            raise ValueError(f"Invalid site ID: {site_id}")

        site_dir = safe_path_join(self.storage_base, site_id)
        if not site_dir.exists():
            raise FileNotFoundError(f"Site not found: {site_id}")

        # Load manifest
        manifest_file = safe_path_join(site_dir, "manifest.json")
        if not manifest_file.exists():
            raise FileNotFoundError(f"Manifest not found for site {site_id}")

        with open(manifest_file) as f:
            manifest_data = json.load(f)
        manifest = SiteManifest(**manifest_data)

        # Get container lifecycle status
        lifecycle_status = await self._get_container_status(site_id)

        # Get health status (default to unknown)
        health_status = HealthStatus.UNKNOWN
        if hasattr(manifest, "last_health_status") and manifest.last_health_status:
            try:
                health_status = HealthStatus(manifest.last_health_status)
            except ValueError:
                health_status = HealthStatus.UNKNOWN

        # Get container details
        container_id = manifest.docker_container_id
        container_name = None
        if container_id:
            try:
                # Get container name from docker inspect
                result = subprocess.run(
                    ["docker", "inspect", "--format", "{{.Name}}", container_id],
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    container_name = result.stdout.decode().strip().lstrip("/")
            except Exception as e:
                logger.warning(f"Failed to get container name for {container_id}: {e}")

        # Calculate uptime (if container is running)
        uptime_seconds = None
        if lifecycle_status == SiteLifecycleStatus.RUNNING and container_id:
            try:
                result = subprocess.run(
                    [
                        "docker",
                        "inspect",
                        "--format",
                        "{{.State.StartedAt}}",
                        container_id,
                    ],
                    capture_output=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    started_at_str = result.stdout.decode().strip()
                    # Parse started_at and calculate uptime
                    # Format: 2025-01-01T12:00:00.123456789Z
                    from datetime import datetime, timezone

                    started_at = datetime.fromisoformat(
                        started_at_str.replace("Z", "+00:00")
                    )
                    uptime_seconds = int((datetime.now(timezone.utc) - started_at).total_seconds())
            except Exception as e:
                logger.warning(f"Failed to calculate uptime for {container_id}: {e}")

        # Last release ID (from manifest if available)
        last_release_id = None
        if hasattr(manifest, "current_release_id"):
            last_release_id = manifest.current_release_id

        # Build operational status
        return SiteOperationalStatus(
            site_id=site_id,
            manifest_status=manifest.status,
            lifecycle_status=lifecycle_status,
            health_status=health_status,
            container_id=container_id,
            container_name=container_name,
            deployed_url=manifest.deployed_url,
            last_deployed_at=manifest.deployed_at,
            last_release_id=last_release_id,
            uptime_seconds=uptime_seconds,
        )

    async def _get_container_status(self, site_id: str) -> SiteLifecycleStatus:
        """
        Get container lifecycle status from Docker Compose.

        Args:
            site_id: Site identifier

        Returns:
            SiteLifecycleStatus enum value

        Raises:
            FileNotFoundError: If site doesn't exist
        """
        site_dir = safe_path_join(self.storage_base, site_id)

        # Check if docker-compose.yml exists
        compose_file = safe_path_join(site_dir, "docker-compose.yml")
        if not compose_file.exists():
            return SiteLifecycleStatus.UNKNOWN

        try:
            # Run docker-compose ps to get container status
            result = subprocess.run(
                ["docker-compose", "ps", "--format", "json"],
                cwd=str(site_dir),
                capture_output=True,
                timeout=10,
            )

            if result.returncode != 0:
                logger.warning(
                    f"docker-compose ps failed for {site_id}: {result.stderr.decode() if result.stderr else 'unknown error'}"
                )
                return SiteLifecycleStatus.UNKNOWN

            # Parse JSON output
            output = result.stdout.decode().strip()
            if not output:
                return SiteLifecycleStatus.STOPPED

            # docker-compose ps --format json returns one JSON object per line
            import json

            containers = []
            for line in output.splitlines():
                if line.strip():
                    containers.append(json.loads(line))

            if not containers:
                return SiteLifecycleStatus.STOPPED

            # Get status of first container (should only be one)
            container = containers[0]
            state = container.get("State", "").lower()

            # Map docker state to SiteLifecycleStatus
            status_map = {
                "running": SiteLifecycleStatus.RUNNING,
                "exited": SiteLifecycleStatus.EXITED,
                "stopped": SiteLifecycleStatus.STOPPED,
                "restarting": SiteLifecycleStatus.RESTARTING,
                "paused": SiteLifecycleStatus.PAUSED,
                "dead": SiteLifecycleStatus.DEAD,
                "created": SiteLifecycleStatus.CREATED,
            }

            return status_map.get(state, SiteLifecycleStatus.UNKNOWN)

        except Exception as e:
            logger.error(f"Failed to get container status for {site_id}: {e}")
            return SiteLifecycleStatus.UNKNOWN


# ============================================================================
# Singleton
# ============================================================================

_ops_service: Optional[WebGenesisOpsService] = None


def get_ops_service() -> WebGenesisOpsService:
    """Get singleton WebGenesisOpsService instance."""
    global _ops_service
    if _ops_service is None:
        _ops_service = WebGenesisOpsService()
    return _ops_service
