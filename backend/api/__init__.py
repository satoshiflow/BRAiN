# backend/api/__init__.py

from fastapi import APIRouter

from .routes.agent_manager import router as agent_router
from .routes.axe import router as axe_router

# Zentraler API-Router für alle "Core"-APIs (nicht modulbasiert)
api_router = APIRouter()

# Agents (/api/agents/...)
api_router.include_router(agent_router)

# AXE (/api/axe/...)
api_router.include_router(axe_router)
