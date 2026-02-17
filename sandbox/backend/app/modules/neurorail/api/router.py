"""
NeuroRail API Router Integration (Phase 3 Backend).

Combines all NeuroRail routers for easy FastAPI integration.

Usage in main.py:
    from app.modules.neurorail.api.router import neurorail_router
    app.include_router(neurorail_router)
"""

from fastapi import APIRouter

from app.modules.neurorail.api.streams import router as streams_router
from app.modules.neurorail.api.rbac import router as rbac_router

# Import existing NeuroRail routers (from Phase 1 & 2)
from app.modules.neurorail.identity.router import router as identity_router
from app.modules.neurorail.lifecycle.router import router as lifecycle_router
from app.modules.neurorail.audit.router import router as audit_router
from app.modules.neurorail.telemetry.router import router as telemetry_router
from app.modules.neurorail.execution.router import router as execution_router
from app.modules.governor.router import router as governor_router

# Combined NeuroRail router
neurorail_router = APIRouter()

# Include all sub-routers
neurorail_router.include_router(identity_router)
neurorail_router.include_router(lifecycle_router)
neurorail_router.include_router(audit_router)
neurorail_router.include_router(telemetry_router)
neurorail_router.include_router(execution_router)
neurorail_router.include_router(governor_router)

# Phase 3 routers
neurorail_router.include_router(streams_router)
neurorail_router.include_router(rbac_router)
