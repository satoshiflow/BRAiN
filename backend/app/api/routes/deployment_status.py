"""
Deployment Status API Routes

Provides endpoints for checking deployment status.
"""

from fastapi import APIRouter
from loguru import logger

from app.modules.deployment import DeploymentStatus, DeploymentService
from app.core.config import get_settings

router = APIRouter(prefix="/api/deployment", tags=["deployment"])


@router.get("/status", response_model=DeploymentStatus)
async def get_deployment_status():
    """
    Get comprehensive deployment status including:
    - Git repository information (branch, commit, dirty state)
    - Docker container statuses
    - Service connectivity (API, PostgreSQL, Redis, Qdrant)
    - Environment and version information
    """
    try:
        settings = get_settings()
        service = DeploymentService(
            environment=settings.environment,
            version="0.6.1",  # TODO: Read from version file
        )

        status = await service.get_deployment_status()
        return status

    except Exception as e:
        logger.error(f"Failed to get deployment status: {e}")
        raise
