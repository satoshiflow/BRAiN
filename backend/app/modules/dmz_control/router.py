"""
DMZ Control API Router

REST API endpoints for DMZ management.

Endpoints:
- GET  /api/dmz/status - Get DMZ status
- POST /api/dmz/start  - Start DMZ services
- POST /api/dmz/stop   - Stop DMZ services

Security:
- Admin/Owner access only (TODO: Add auth middleware)
- All operations audited
- Fail-closed design

Version: 1.0.0
Phase: B.3 - DMZ Control Backend
"""

from fastapi import APIRouter, HTTPException, status, Depends
from loguru import logger

from backend.app.modules.dmz_control.schemas import (
    DMZStatusResponse,
    DMZControlRequest,
    DMZControlResponse,
)
from backend.app.modules.dmz_control.service import (
    DMZControlService,
    get_dmz_control_service,
)


# ============================================================================
# Router Setup
# ============================================================================

router = APIRouter(
    prefix="/api/dmz",
    tags=["DMZ Control"],
)


# ============================================================================
# Endpoints
# ============================================================================

@router.get(
    "/status",
    response_model=DMZStatusResponse,
    summary="Get DMZ Status",
    description="Get current status of DMZ gateway services",
)
async def get_dmz_status(
    service: DMZControlService = Depends(get_dmz_control_service),
) -> DMZStatusResponse:
    """
    Get DMZ status.

    Returns:
        Current status of all DMZ services

    Example Response:
        ```json
        {
          "status": "running",
          "services": [
            {
              "name": "brain-dmz-telegram",
              "status": "running",
              "ports": ["8001:8000"]
            }
          ],
          "service_count": 1,
          "running_count": 1,
          "message": "All 1 DMZ service(s) running"
        }
        ```
    """
    try:
        return await service.get_status()
    except Exception as e:
        logger.error(f"Failed to get DMZ status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DMZ status: {str(e)}",
        )


@router.post(
    "/start",
    response_model=DMZControlResponse,
    summary="Start DMZ Services",
    description="Start all DMZ gateway services",
)
async def start_dmz(
    request: DMZControlRequest = DMZControlRequest(action="start"),
    service: DMZControlService = Depends(get_dmz_control_service),
) -> DMZControlResponse:
    """
    Start DMZ services.

    Args:
        request: Control request with options (force, timeout)

    Returns:
        Operation result with status changes

    Raises:
        HTTPException: If operation fails

    Example Request:
        ```json
        {
          "action": "start",
          "force": false,
          "timeout": 30
        }
        ```

    Example Response:
        ```json
        {
          "success": true,
          "action": "start",
          "previous_status": "stopped",
          "current_status": "running",
          "services_affected": ["brain-dmz-telegram"],
          "message": "DMZ started successfully (1 services)"
        }
        ```
    """
    try:
        result = await service.start(request)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message,
            )

        logger.info(f"DMZ started: {result.message}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start DMZ: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start DMZ: {str(e)}",
        )


@router.post(
    "/stop",
    response_model=DMZControlResponse,
    summary="Stop DMZ Services",
    description="Stop all DMZ gateway services",
)
async def stop_dmz(
    request: DMZControlRequest = DMZControlRequest(action="stop"),
    service: DMZControlService = Depends(get_dmz_control_service),
) -> DMZControlResponse:
    """
    Stop DMZ services.

    Args:
        request: Control request with options (force, timeout)

    Returns:
        Operation result with status changes

    Raises:
        HTTPException: If operation fails

    Example Request:
        ```json
        {
          "action": "stop",
          "force": false,
          "timeout": 30
        }
        ```

    Example Response:
        ```json
        {
          "success": true,
          "action": "stop",
          "previous_status": "running",
          "current_status": "stopped",
          "services_affected": ["brain-dmz-telegram"],
          "message": "DMZ stopped successfully"
        }
        ```

    Security Note:
        This endpoint is called automatically when Sovereign Mode is activated.
        All stop operations are audited.
    """
    try:
        result = await service.stop(request)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message,
            )

        logger.info(f"DMZ stopped: {result.message}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop DMZ: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop DMZ: {str(e)}",
        )
