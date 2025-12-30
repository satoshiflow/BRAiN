"""
System Health API Routes

Auto-discovered route module for comprehensive system health monitoring.
"""

from fastapi import APIRouter

# Import the main router from the system_health module
from backend.app.modules.system_health.router import router as system_health_router

# Create wrapper router for auto-discovery
router = APIRouter()
router.include_router(system_health_router)
