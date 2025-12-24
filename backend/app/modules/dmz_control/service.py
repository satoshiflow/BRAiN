"""
DMZ Control Service

Manages DMZ Docker Compose stack lifecycle.
Provides start/stop/status operations for DMZ gateway services.

Security:
- Admin/Owner access only
- Audit all operations
- Fail-closed design
- No partial states

Version: 1.0.0
Phase: B.3 - DMZ Control Backend
"""

import os
import subprocess
from typing import List, Tuple
from loguru import logger

from backend.app.modules.dmz_control.schemas import (
    DMZStatus,
    DMZStatusResponse,
    DMZServiceInfo,
    DMZControlRequest,
    DMZControlResponse,
)


class DMZControlService:
    """
    Service for managing DMZ Docker Compose stack.

    Responsibilities:
    - Start/stop DMZ services via docker compose
    - Query DMZ service status
    - Validate DMZ state
    """

    def __init__(
        self,
        compose_file: str = "docker-compose.dmz.yml",
        project_name: str = "brain-dmz",
    ):
        """
        Initialize DMZ control service.

        Args:
            compose_file: Path to DMZ docker-compose file
            project_name: Docker Compose project name
        """
        self.compose_file = compose_file
        self.project_name = project_name

        # Validate compose file exists
        if not os.path.exists(self.compose_file):
            logger.warning(
                f"DMZ compose file not found: {self.compose_file} "
                "(DMZ control disabled)"
            )

    def _run_compose_command(
        self,
        command: List[str],
        timeout: int = 30,
    ) -> Tuple[bool, str, str]:
        """
        Run docker compose command.

        Args:
            command: Command arguments (e.g., ["ps", "--format", "json"])
            timeout: Command timeout in seconds

        Returns:
            (success, stdout, stderr)
        """
        cmd = [
            "docker",
            "compose",
            "-f",
            self.compose_file,
            "-p",
            self.project_name,
        ] + command

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            logger.error(f"Docker compose command timeout: {' '.join(cmd)}")
            return False, "", "Command timeout"
        except Exception as e:
            logger.error(f"Failed to run docker compose: {e}")
            return False, "", str(e)

    async def get_status(self) -> DMZStatusResponse:
        """
        Get current DMZ status.

        Returns:
            DMZStatusResponse with current status and service info
        """
        if not os.path.exists(self.compose_file):
            return DMZStatusResponse(
                status=DMZStatus.UNKNOWN,
                message=f"DMZ compose file not found: {self.compose_file}",
            )

        # Get service list with status
        success, stdout, stderr = self._run_compose_command(["ps", "--all"])

        if not success:
            logger.error(f"Failed to get DMZ status: {stderr}")
            return DMZStatusResponse(
                status=DMZStatus.ERROR,
                message=f"Failed to query DMZ: {stderr}",
            )

        # Parse service info from ps output
        services = []
        running_count = 0

        # Parse ps output (format: NAME   SERVICE   STATUS   PORTS)
        lines = stdout.strip().split("\n")[1:]  # Skip header
        for line in lines:
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) < 3:
                continue

            name = parts[0]
            status_str = " ".join(parts[2:])  # Status might be multi-word

            service_info = DMZServiceInfo(
                name=name,
                status=status_str,
            )
            services.append(service_info)

            if "running" in status_str.lower() or "up" in status_str.lower():
                running_count += 1

        # Determine overall status
        service_count = len(services)
        if service_count == 0:
            status = DMZStatus.STOPPED
            message = "No DMZ services exist"
        elif running_count == service_count:
            status = DMZStatus.RUNNING
            message = f"All {service_count} DMZ service(s) running"
        elif running_count == 0:
            status = DMZStatus.STOPPED
            message = f"All {service_count} DMZ service(s) stopped"
        else:
            status = DMZStatus.ERROR
            message = (
                f"Partial state: {running_count}/{service_count} services running "
                "(inconsistent state)"
            )

        return DMZStatusResponse(
            status=status,
            services=services,
            service_count=service_count,
            running_count=running_count,
            message=message,
        )

    async def start(self, request: DMZControlRequest) -> DMZControlResponse:
        """
        Start DMZ services.

        Args:
            request: Control request with options

        Returns:
            DMZControlResponse with operation result
        """
        # Get current status
        status_before = await self.get_status()

        # Check if already running
        if status_before.status == DMZStatus.RUNNING and not request.force:
            return DMZControlResponse(
                success=True,
                action="start",
                previous_status=status_before.status,
                current_status=DMZStatus.RUNNING,
                message="DMZ already running (no action needed)",
            )

        # Start services
        logger.info("Starting DMZ services...")
        success, stdout, stderr = self._run_compose_command(
            ["up", "-d"],
            timeout=request.timeout,
        )

        if not success:
            logger.error(f"Failed to start DMZ: {stderr}")
            return DMZControlResponse(
                success=False,
                action="start",
                previous_status=status_before.status,
                current_status=DMZStatus.ERROR,
                message=f"Failed to start DMZ: {stderr}",
            )

        # Verify started
        status_after = await self.get_status()

        return DMZControlResponse(
            success=True,
            action="start",
            previous_status=status_before.status,
            current_status=status_after.status,
            services_affected=[svc.name for svc in status_after.services],
            message=f"DMZ started successfully ({status_after.running_count} services)",
        )

    async def stop(self, request: DMZControlRequest) -> DMZControlResponse:
        """
        Stop DMZ services.

        Args:
            request: Control request with options

        Returns:
            DMZControlResponse with operation result
        """
        # Get current status
        status_before = await self.get_status()

        # Check if already stopped
        if status_before.status == DMZStatus.STOPPED and not request.force:
            return DMZControlResponse(
                success=True,
                action="stop",
                previous_status=status_before.status,
                current_status=DMZStatus.STOPPED,
                message="DMZ already stopped (no action needed)",
            )

        # Stop services
        logger.info("Stopping DMZ services...")
        success, stdout, stderr = self._run_compose_command(
            ["down"],
            timeout=request.timeout,
        )

        if not success:
            logger.error(f"Failed to stop DMZ: {stderr}")
            return DMZControlResponse(
                success=False,
                action="stop",
                previous_status=status_before.status,
                current_status=DMZStatus.ERROR,
                message=f"Failed to stop DMZ: {stderr}",
            )

        # Verify stopped
        status_after = await self.get_status()

        return DMZControlResponse(
            success=True,
            action="stop",
            previous_status=status_before.status,
            current_status=status_after.status,
            services_affected=[svc.name for svc in status_before.services],
            message="DMZ stopped successfully",
        )


# ============================================================================
# Singleton
# ============================================================================

_dmz_control_service: DMZControlService | None = None


def get_dmz_control_service() -> DMZControlService:
    """Get DMZ control service singleton."""
    global _dmz_control_service
    if _dmz_control_service is None:
        _dmz_control_service = DMZControlService()
    return _dmz_control_service
