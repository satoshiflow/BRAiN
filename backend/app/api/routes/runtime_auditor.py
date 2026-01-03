"""
Runtime Auditor API Routes

Auto-discovered route module for runtime audit metrics.
"""

from fastapi import APIRouter

# Import the main router from the runtime_auditor module
from app.modules.runtime_auditor.router import router as auditor_router

# Create wrapper router for auto-discovery
router = APIRouter()
router.include_router(auditor_router)
