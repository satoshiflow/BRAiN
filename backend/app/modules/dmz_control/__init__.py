"""
DMZ Control Module

Manages DMZ Docker Compose stack lifecycle.
Provides API endpoints for DMZ start/stop/status operations.

Phase: B.3 - DMZ Control Backend
Version: 1.0.0
"""

from backend.app.modules.dmz_control.schemas import (
    DMZStatus,
    DMZServiceInfo,
    DMZStatusResponse,
    DMZControlRequest,
    DMZControlResponse,
)

from backend.app.modules.dmz_control.service import (
    DMZControlService,
    get_dmz_control_service,
)

from backend.app.modules.dmz_control.router import router


__all__ = [
    # Enums
    "DMZStatus",
    # Models
    "DMZServiceInfo",
    "DMZStatusResponse",
    "DMZControlRequest",
    "DMZControlResponse",
    # Service
    "DMZControlService",
    "get_dmz_control_service",
    # Router
    "router",
]
