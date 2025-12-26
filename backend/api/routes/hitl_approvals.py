"""
HITL Approvals API Route - Auto-discovered by FastAPI

Sprint 11: Human-in-the-Loop approval interface for IR governance.
"""

from backend.app.modules.ir_governance.hitl_router import router

# This module is auto-discovered by backend/main.py
# The router is automatically included in the FastAPI app

__all__ = ["router"]
