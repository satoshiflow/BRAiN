"""
NeuroRail API Routes (Phase 3 Backend).

FastAPI routers for NeuroRail SSE streams and RBAC.
"""

from backend.app.modules.neurorail.api.streams import router as streams_router
from backend.app.modules.neurorail.api.rbac import router as rbac_router

__all__ = ["streams_router", "rbac_router"]
