"""
DMZ Control API Router

Endpoints for managing DMZ gateway services.
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from backend.app.modules.dmz_control.service import get_dmz_control_service
from backend.app.modules.dmz_control.schemas import (
    DMZStatus,
    DMZControlResponse,
)

router = APIRouter(prefix="/api/dmz", tags=["dmz"])


@router.get("/status", response_model=DMZStatus)
async def get_dmz_status():
    """
    Get DMZ gateway status.

    Returns current status of all DMZ containers.

    **Security**: Admin/Owner only (TODO: implement auth check)
    """
    service = get_dmz_control_service()

    try:
        status = await service.get_status()
        return status

    except Exception as e:
        logger.error(f"Failed to get DMZ status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get DMZ status: {str(e)}"
        )


@router.post("/start", response_model=DMZControlResponse)
async def start_dmz():
    """
    Start DMZ gateway services.

    Starts all DMZ containers defined in docker-compose.dmz.yml.

    **Security**: Admin/Owner only (TODO: implement auth check)

    **Note**: DMZ cannot be started in Sovereign Mode.
    """
    service = get_dmz_control_service()

    try:
        # TODO: Check if in Sovereign Mode - if yes, reject
        # from backend.app.modules.sovereign_mode import get_sovereign_service
        # sovereign = get_sovereign_service()
        # if sovereign.config.current_mode == OperationMode.SOVEREIGN:
        #     raise HTTPException(
        #         status_code=403,
        #         detail="Cannot start DMZ while in Sovereign Mode"
        #     )

        success = await service.start_dmz()

        if success:
            status = await service.get_status()
            return DMZControlResponse(
                success=True,
                message="DMZ gateway started successfully",
                status=status,
            )
        else:
            return DMZControlResponse(
                success=False, message="Failed to start DMZ gateway"
            )

    except Exception as e:
        logger.error(f"Failed to start DMZ: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to start DMZ: {str(e)}"
        )


@router.post("/stop", response_model=DMZControlResponse)
async def stop_dmz():
    """
    Stop DMZ gateway services.

    Stops all DMZ containers.

    **Security**: Admin/Owner only (TODO: implement auth check)
    """
    service = get_dmz_control_service()

    try:
        success = await service.stop_dmz()

        if success:
            status = await service.get_status()
            return DMZControlResponse(
                success=True,
                message="DMZ gateway stopped successfully",
                status=status,
            )
        else:
            return DMZControlResponse(
                success=False, message="Failed to stop DMZ gateway"
            )

    except Exception as e:
        logger.error(f"Failed to stop DMZ: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to stop DMZ: {str(e)}"
        )
