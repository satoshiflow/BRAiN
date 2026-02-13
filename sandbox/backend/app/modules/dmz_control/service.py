"""
DMZ Control Service

Manages DMZ gateway services lifecycle via docker compose.
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Optional
from loguru import logger

from app.modules.dmz_control.schemas import (
    DMZStatus,
    DMZContainer,
)


class DMZControlService:
    """
    Control DMZ gateway docker compose.

    Manages lifecycle of DMZ services (Telegram, future: WhatsApp, etc.)
    """

    def __init__(self, compose_file: str = "docker-compose.dmz.yml"):
        """
        Initialize DMZ control service.

        Args:
            compose_file: Path to DMZ docker-compose file
        """
        self.compose_file = compose_file
        self.project_root = Path(__file__).parent.parent.parent.parent.parent
        self.compose_path = self.project_root / compose_file

        # Check if compose file exists
        if not self.compose_path.exists():
            logger.warning(f"DMZ compose file not found: {self.compose_path}")

    async def get_status(self) -> DMZStatus:
        """
        Get DMZ gateway status.

        Returns:
            DMZStatus with current state
        """
        try:
            # Check if compose file exists
            if not self.compose_path.exists():
                return DMZStatus(
                    enabled=False,
                    running=False,
                    error=f"Compose file not found: {self.compose_file}",
                )

            # Get container status via docker compose ps
            result = subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    str(self.compose_path),
                    "ps",
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.project_root),
            )

            if result.returncode != 0:
                logger.error(f"Failed to get DMZ status: {result.stderr}")
                return DMZStatus(
                    enabled=True,
                    running=False,
                    error=result.stderr[:200],
                )

            # Parse JSON output
            containers = []
            running_count = 0

            if result.stdout.strip():
                # Docker compose ps can return multiple JSON objects (one per line)
                for line in result.stdout.strip().split("\n"):
                    if not line.strip():
                        continue

                    try:
                        data = json.loads(line)

                        container = DMZContainer(
                            name=data.get("Name", "unknown"),
                            status=self._map_status(data.get("State", "unknown")),
                            health=data.get("Health"),
                            ports=self._extract_ports(data.get("Publishers", [])),
                        )

                        containers.append(container)

                        if container.status == "running":
                            running_count += 1

                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse container JSON: {e}")
                        continue

            return DMZStatus(
                enabled=True,
                running=(running_count > 0),
                containers=containers,
            )

        except subprocess.TimeoutExpired:
            logger.error("Timeout while getting DMZ status")
            return DMZStatus(
                enabled=True, running=False, error="Command timeout"
            )

        except Exception as e:
            logger.error(f"Failed to get DMZ status: {e}")
            return DMZStatus(enabled=False, running=False, error=str(e))

    async def start_dmz(self) -> bool:
        """
        Start DMZ gateway services.

        Returns:
            True if started successfully
        """
        try:
            if not self.compose_path.exists():
                logger.error(f"DMZ compose file not found: {self.compose_path}")
                return False

            logger.info("Starting DMZ gateway services...")

            result = subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    str(self.compose_path),
                    "up",
                    "-d",
                ],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.project_root),
            )

            if result.returncode == 0:
                logger.info("DMZ gateway started successfully")
                return True
            else:
                logger.error(f"Failed to start DMZ: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Timeout while starting DMZ")
            return False

        except Exception as e:
            logger.error(f"Failed to start DMZ: {e}")
            return False

    async def stop_dmz(self) -> bool:
        """
        Stop DMZ gateway services.

        Returns:
            True if stopped successfully
        """
        try:
            if not self.compose_path.exists():
                logger.warning(f"DMZ compose file not found: {self.compose_path}")
                # If file doesn't exist, consider it "stopped"
                return True

            logger.info("Stopping DMZ gateway services...")

            result = subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    str(self.compose_path),
                    "down",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.project_root),
            )

            if result.returncode == 0:
                logger.info("DMZ gateway stopped successfully")
                return True
            else:
                logger.error(f"Failed to stop DMZ: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Timeout while stopping DMZ")
            return False

        except Exception as e:
            logger.error(f"Failed to stop DMZ: {e}")
            return False

    def _map_status(self, state: str) -> str:
        """
        Map docker compose state to simplified status.

        Args:
            state: Docker compose state (e.g., "running", "exited")

        Returns:
            Simplified status
        """
        state_lower = state.lower()

        if "running" in state_lower or "up" in state_lower:
            return "running"
        elif "stop" in state_lower or "exit" in state_lower:
            return "stopped"
        elif "restart" in state_lower:
            return "restarting"
        else:
            return "unknown"

    def _extract_ports(self, publishers: list) -> list:
        """
        Extract port mappings from docker compose publishers.

        Args:
            publishers: List of port publisher objects

        Returns:
            List of port strings (e.g., ["8001:8001"])
        """
        ports = []

        for pub in publishers:
            if isinstance(pub, dict):
                published_port = pub.get("PublishedPort")
                target_port = pub.get("TargetPort")

                if published_port and target_port:
                    ports.append(f"{published_port}:{target_port}")

        return ports


# Singleton
_dmz_control_service: Optional[DMZControlService] = None


def get_dmz_control_service() -> DMZControlService:
    """Get singleton DMZ control service instance."""
    global _dmz_control_service
    if _dmz_control_service is None:
        _dmz_control_service = DMZControlService()
    return _dmz_control_service
