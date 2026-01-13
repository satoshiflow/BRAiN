"""
Deployment Status Service

Provides methods to check deployment status including git info,
container status, and service connectivity.
"""

import asyncio
import subprocess
from typing import Dict, Optional
import time

from loguru import logger

from .schemas import (
    DeploymentStatus,
    GitInfo,
    ContainerInfo,
    ServiceInfo,
    ConnectivityResult,
)


class DeploymentService:
    """Service for checking deployment status"""

    def __init__(self, environment: str = "development", version: str = "0.6.1"):
        self.environment = environment
        self.version = version

    async def get_deployment_status(self) -> DeploymentStatus:
        """Get complete deployment status"""
        git_info = await self._get_git_info()
        containers = await self._get_container_status()
        services = await self._get_service_connectivity()

        return DeploymentStatus(
            git=git_info,
            containers=containers,
            services=services,
            environment=self.environment,
            version=self.version,
        )

    async def _get_git_info(self) -> GitInfo:
        """Get git repository information"""
        try:
            # Get current branch
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()

            # Get current commit (short)
            commit = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()

            # Check if working directory is dirty
            status_output = subprocess.check_output(
                ["git", "status", "--porcelain"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            dirty = len(status_output) > 0

            # Check commits behind remote (if remote exists)
            try:
                behind_output = subprocess.check_output(
                    ["git", "rev-list", "--count", f"HEAD..origin/{branch}"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
                behind_remote = int(behind_output)
            except (subprocess.CalledProcessError, ValueError):
                behind_remote = 0

            return GitInfo(
                branch=branch,
                commit=commit,
                dirty=dirty,
                behind_remote=behind_remote,
            )
        except Exception as e:
            logger.error(f"Failed to get git info: {e}")
            # Return fallback git info
            return GitInfo(
                branch="unknown",
                commit="unknown",
                dirty=False,
                behind_remote=0,
            )

    async def _get_container_status(self) -> Dict[str, ContainerInfo]:
        """Get Docker container statuses"""
        containers = {}
        container_names = ["backend", "postgres", "redis", "qdrant"]

        for name in container_names:
            try:
                # Check if container exists and get its status
                output = subprocess.check_output(
                    ["docker", "ps", "-a", "--filter", f"name={name}", "--format", "{{.ID}} {{.Status}}"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()

                if not output:
                    containers[name] = ContainerInfo(status="not_found", container_id=None)
                else:
                    parts = output.split(maxsplit=1)
                    container_id = parts[0] if parts else None
                    status_text = parts[1] if len(parts) > 1 else ""

                    # Determine status from Docker status text
                    if status_text.startswith("Up"):
                        status = "running"
                    else:
                        status = "stopped"

                    containers[name] = ContainerInfo(
                        status=status,
                        container_id=container_id[:12] if container_id else None,
                    )
            except subprocess.CalledProcessError:
                # Docker not available or other error
                containers[name] = ContainerInfo(status="unknown", container_id=None)
            except Exception as e:
                logger.error(f"Failed to check container {name}: {e}")
                containers[name] = ContainerInfo(status="unknown", container_id=None)

        return containers

    async def _test_postgres_connectivity(self) -> ConnectivityResult:
        """Test PostgreSQL connectivity"""
        try:
            from app.core.config import get_settings
            import asyncpg

            settings = get_settings()
            start_time = time.time()

            # Parse DATABASE_URL to extract connection parameters
            # Format: postgresql://user:pass@host:port/database
            url = str(settings.DATABASE_URL)
            conn = await asyncio.wait_for(
                asyncpg.connect(url),
                timeout=5.0,
            )
            await conn.close()

            response_time = (time.time() - start_time) * 1000

            return ConnectivityResult(
                status="reachable",
                response_time_ms=round(response_time, 2),
            )
        except asyncio.TimeoutError:
            return ConnectivityResult(
                status="unreachable",
                error="Connection timeout (5s)",
            )
        except Exception as e:
            return ConnectivityResult(
                status="error",
                error=str(e),
            )

    async def _test_redis_connectivity(self) -> ConnectivityResult:
        """Test Redis connectivity"""
        try:
            from app.core.config import get_settings
            import redis.asyncio as redis

            settings = get_settings()
            start_time = time.time()

            r = redis.from_url(str(settings.REDIS_URL), decode_responses=True)
            await asyncio.wait_for(r.ping(), timeout=5.0)
            await r.aclose()

            response_time = (time.time() - start_time) * 1000

            return ConnectivityResult(
                status="reachable",
                response_time_ms=round(response_time, 2),
            )
        except asyncio.TimeoutError:
            return ConnectivityResult(
                status="unreachable",
                error="Connection timeout (5s)",
            )
        except Exception as e:
            return ConnectivityResult(
                status="error",
                error=str(e),
            )

    async def _test_qdrant_connectivity(self) -> ConnectivityResult:
        """Test Qdrant connectivity"""
        try:
            from app.core.config import get_settings
            import httpx

            settings = get_settings()
            start_time = time.time()

            # Qdrant health check endpoint
            qdrant_url = f"{settings.QDRANT_HOST}:{settings.QDRANT_PORT}/health"

            async with httpx.AsyncClient() as client:
                response = await asyncio.wait_for(
                    client.get(qdrant_url),
                    timeout=5.0,
                )

            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return ConnectivityResult(
                    status="reachable",
                    response_time_ms=round(response_time, 2),
                )
            else:
                return ConnectivityResult(
                    status="unreachable",
                    error=f"HTTP {response.status_code}",
                )
        except asyncio.TimeoutError:
            return ConnectivityResult(
                status="unreachable",
                error="Connection timeout (5s)",
            )
        except Exception as e:
            return ConnectivityResult(
                status="error",
                error=str(e),
            )

    async def _test_api_connectivity(self) -> ConnectivityResult:
        """Test backend API connectivity (self-test)"""
        try:
            import httpx

            start_time = time.time()

            # Test own API health endpoint
            async with httpx.AsyncClient() as client:
                response = await asyncio.wait_for(
                    client.get("http://localhost:8000/api/system/health/status"),
                    timeout=5.0,
                )

            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return ConnectivityResult(
                    status="reachable",
                    response_time_ms=round(response_time, 2),
                )
            else:
                return ConnectivityResult(
                    status="unreachable",
                    error=f"HTTP {response.status_code}",
                )
        except asyncio.TimeoutError:
            return ConnectivityResult(
                status="unreachable",
                error="Connection timeout (5s)",
            )
        except Exception as e:
            return ConnectivityResult(
                status="error",
                error=str(e),
            )

    async def _get_service_connectivity(self) -> ServiceInfo:
        """Test connectivity to all services"""
        # Run all connectivity tests in parallel
        results = await asyncio.gather(
            self._test_api_connectivity(),
            self._test_postgres_connectivity(),
            self._test_redis_connectivity(),
            self._test_qdrant_connectivity(),
            return_exceptions=True,
        )

        # Handle potential exceptions from gather
        api_result = results[0] if not isinstance(results[0], Exception) else ConnectivityResult(
            status="error", error=str(results[0])
        )
        postgres_result = results[1] if not isinstance(results[1], Exception) else ConnectivityResult(
            status="error", error=str(results[1])
        )
        redis_result = results[2] if not isinstance(results[2], Exception) else ConnectivityResult(
            status="error", error=str(results[2])
        )
        qdrant_result = results[3] if not isinstance(results[3], Exception) else ConnectivityResult(
            status="error", error=str(results[3])
        )

        return ServiceInfo(
            api=api_result,
            postgres=postgres_result,
            redis=redis_result,
            qdrant=qdrant_result,
        )
